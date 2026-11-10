#include "runtime.hpp"
#include <algorithm>
#include <cstring>
#include <inttypes.h>
#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_log.h"
#include "esp_random.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "led_strip.h"

namespace motion {
namespace {
constexpr auto kUart=UART_NUM_1;
constexpr auto kDriver=GPIO_NUM_10;
constexpr bool kPidEnabled=false; // Enable only after two encoders + physical calibration.
static_assert(!kPidEnabled,"PID requires calibrated two-wheel measurements");
uint64_t us() { return uint64_t(esp_timer_get_time()); }
}
Runtime& Runtime::get() { static Runtime runtime;return runtime; }
void Runtime::wake() { if(control_task_) xTaskNotifyGive(control_task_); }
void Runtime::start() {
    core_=simple::Control(esp_random());
    gpio_config_t pin{};pin.pin_bit_mask=1ULL<<kDriver;pin.mode=GPIO_MODE_OUTPUT;pin.pull_down_en=GPIO_PULLDOWN_ENABLE;
    ESP_ERROR_CHECK(gpio_config(&pin));ESP_ERROR_CHECK(gpio_set_level(kDriver,0));
    // CS is inactive before ownership moves to SPI2. No old permit/handshake outputs.
    ESP_ERROR_CHECK(gpio_set_direction(GPIO_NUM_5,GPIO_MODE_OUTPUT));ESP_ERROR_CHECK(gpio_set_level(GPIO_NUM_5,1));
    spi_bus_config_t bus{};bus.mosi_io_num=15;bus.miso_io_num=16;bus.sclk_io_num=4;
    bus.quadwp_io_num=-1;bus.quadhd_io_num=-1;bus.max_transfer_sz=32;
    ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST,&bus,SPI_DMA_DISABLED));
    spi_device_interface_config_t device{};device.clock_speed_hz=1000000;device.mode=0;device.spics_io_num=5;
    device.queue_size=1;device.cs_ena_pretrans=2;device.cs_ena_posttrans=2;
    ESP_ERROR_CHECK(spi_bus_add_device(SPI2_HOST,&device,&spi_));
    uart_config_t uart{};uart.baud_rate=460800;uart.data_bits=UART_DATA_8_BITS;uart.parity=UART_PARITY_DISABLE;
    uart.stop_bits=UART_STOP_BITS_1;uart.flow_ctrl=UART_HW_FLOWCTRL_DISABLE;uart.source_clk=UART_SCLK_DEFAULT;
    ESP_ERROR_CHECK(uart_param_config(kUart,&uart));
    ESP_ERROR_CHECK(uart_set_pin(kUart,13,14,UART_PIN_NO_CHANGE,UART_PIN_NO_CHANGE));
    ESP_ERROR_CHECK(uart_driver_install(kUart,2048,0,16,&uart_events_,0));
    uart_out_=xQueueCreate(4,sizeof(simple::Frame));configASSERT(uart_out_);
    configASSERT(xTaskCreatePinnedToCore(control_entry,"car_control",6144,this,12,&control_task_,1)==pdPASS);
    configASSERT(xTaskCreatePinnedToCore(uart_entry,"brain_uart",4096,this,11,nullptr,1)==pdPASS);
    configASSERT(xTaskCreatePinnedToCore(log_entry,"car_log",6144,this,2,nullptr,0)==pdPASS);
}
void Runtime::stop(simple::Reason reason) {
    portENTER_CRITICAL(&mux_);pending_.stop=true;pending_.stop_reason=reason;pending_.stop_us=us();portEXIT_CRITICAL(&mux_);wake();
}
void Runtime::mode(simple::Mode mode) {
    portENTER_CRITICAL(&mux_);pending_.mode=true;pending_.new_mode=mode;pending_.source=Source::None;pending_.command_us=us();portEXIT_CRITICAL(&mux_);wake();
}
void Runtime::disconnect() {
    portENTER_CRITICAL(&mux_);pending_.disconnected=true;portEXIT_CRITICAL(&mux_);wake();
}
void Runtime::drive(simple::Action action,uint8_t speed) {
    portENTER_CRITICAL(&mux_);pending_.source=Source::Manual;pending_.action=action;pending_.speed=speed;pending_.command_us=us();portEXIT_CRITICAL(&mux_);wake();
}
bool Runtime::listen(bool enabled) {
    simple::Frame f{simple::Type::Listen,0,1,{}};f.payload[0]=enabled?1:0;return xQueueSend(uart_out_,&f,0)==pdTRUE;
}
bool Runtime::wifi(const char* ssid,size_t n,const char* password,size_t p) {
    if(!n || n>32 || p>64) return false;
    simple::Frame f{simple::Type::WifiConfig,0,uint8_t(2+n+p),{}};
    f.payload[0]=uint8_t(n);f.payload[1]=uint8_t(p);
    std::memcpy(f.payload.data()+2,ssid,n);std::memcpy(f.payload.data()+2+n,password,p);
    // STOP is signaled before credentials can leave for the lower priority UART task.
    stop();return xQueueSend(uart_out_,&f,0)==pdTRUE;
}
Snapshot Runtime::snapshot() {
    portENTER_CRITICAL(&mux_);const auto copy=snapshot_;portEXIT_CRITICAL(&mux_);return copy;
}
bool Runtime::network_busy() {
    portENTER_CRITICAL(&mux_);
    const bool busy=snapshot_.car.left || snapshot_.car.right || pending_.source!=Source::None;
    portEXIT_CRITICAL(&mux_);return busy;
}
void Runtime::accept(const simple::Frame& f) {
    simple::BrainState brain;simple::AiMove ai;
    portENTER_CRITICAL(&mux_);++snapshot_.uart_rx;portEXIT_CRITICAL(&mux_);
    if(simple::parse_brain_state(f,brain)) {
        portENTER_CRITICAL(&mux_);pending_.brain=true;pending_.brain_state=brain;pending_.brain_at=us()/1000;portEXIT_CRITICAL(&mux_);wake();
    } else if(simple::parse_ai_move(f,ai)) {
        portENTER_CRITICAL(&mux_);pending_.source=Source::Ai;pending_.ai=ai;pending_.command_us=us();portEXIT_CRITICAL(&mux_);wake();
    } else if(f.type==simple::Type::Stop && f.size==0) stop();
    else { portENTER_CRITICAL(&mux_);++snapshot_.uart_errors;portEXIT_CRITICAL(&mux_); }
}
void Runtime::control_loop() {
    uint16_t seq=0,last_tx=0;bool have_tx=false;simple::SpiStatus fpga{};
    for(;;) {
        ulTaskNotifyTake(pdTRUE,pdMS_TO_TICKS(5));
        const uint64_t now=us()/1000;
        portENTER_CRITICAL(&mux_);const auto inputs=pending_;pending_=Pending{};portEXIT_CRITICAL(&mux_);
        if(inputs.brain) core_.brain(inputs.brain_state,inputs.brain_at);
        bool rejected=false;
        if(inputs.stop) core_.stop(inputs.stop_reason);
        else {
            if(inputs.disconnected) core_.disconnect();
            if(inputs.mode) core_.set_mode(inputs.new_mode);
            if(inputs.source==Source::Manual) rejected=!core_.manual(inputs.action,inputs.speed,now);
            else if(inputs.source==Source::Ai) rejected=!core_.ai(inputs.ai,now);
        }
        core_.tick(now);
        const auto state=core_.state();
        const bool enable=core_.driver_enabled();
        ESP_ERROR_CHECK(gpio_set_level(kDriver,enable?1:0));
        const auto tx=simple::encode_spi_command({++seq,state.left,state.right});simple::SpiBytes rx{};
        spi_transaction_t transaction{};transaction.length=256;transaction.rxlength=256;
        transaction.tx_buffer=tx.data();transaction.rx_buffer=rx.data();
        const uint64_t started=us();
        const esp_err_t result=spi_device_polling_transmit(spi_,&transaction);
        simple::SpiStatus received{};
        const bool frame_valid=result==ESP_OK && simple::decode_spi_status(rx,received);
        const bool valid=frame_valid && have_tx && received.applied_seq==last_tx;
        if(valid) { fpga=received;core_.fpga(received,us()/1000); }
        // Publish one bounded snapshot; no formatting, socket write, flash or heap here.
        portENTER_CRITICAL(&mux_);
        snapshot_.car=core_.state();snapshot_.brain=core_.brain_state();snapshot_.fpga=fpga;
        snapshot_.brain_connected=core_.brain_connected(now);
        if(!have_tx) ++snapshot_.spi_startup;
        else if(valid) ++snapshot_.spi_ok;
        else {
            ++snapshot_.spi_errors;
            if(result!=ESP_OK) ++snapshot_.spi_io_errors;
            else if(!frame_valid) ++snapshot_.spi_frame_errors;
            else ++snapshot_.spi_ack_errors;
        }
        if(rejected) ++snapshot_.rejected;
        const auto input_time=inputs.stop?inputs.stop_us:inputs.command_us;
        if(input_time && !rejected && started>=input_time) {
            const auto delay=uint32_t(std::min<uint64_t>(started-input_time,UINT32_MAX));
            snapshot_.latency_us[snapshot_.latency_count%snapshot_.latency_us.size()]=delay;++snapshot_.latency_count;
            snapshot_.latency_max_us=std::max(snapshot_.latency_max_us,delay);
        }
        portEXIT_CRITICAL(&mux_);
        last_tx=seq;have_tx=true;
    }
}
void Runtime::uart_loop() {
    simple::UartParser parser;simple::Frame incoming,outgoing;uint16_t seq=0;uint64_t next=0;uint32_t published_generation=0;
    std::array<uint8_t,256> input{};std::array<uint8_t,simple::kMaxFrame> output{};
    for(;;) {
        uart_event_t event{};
        if(xQueueReceive(uart_events_,&event,pdMS_TO_TICKS(5))==pdTRUE && event.type!=UART_DATA) {
            portENTER_CRITICAL(&mux_);++snapshot_.uart_errors;portEXIT_CRITICAL(&mux_);
            if(event.type==UART_FIFO_OVF || event.type==UART_BUFFER_FULL) { uart_flush_input(kUart);parser.reset(); }
        }
        int got=0;const uint32_t parse_errors_before=parser.errors();
        do {
            got=uart_read_bytes(kUart,input.data(),input.size(),0);
            for(int i=0;i<got;++i) if(parser.push(input[size_t(i)],incoming)) accept(incoming);
        } while(got>0);
        const auto s=snapshot();
        if(us()/1000>=next || s.car.generation!=published_generation) {
            outgoing=simple::make_motion_state(++seq,s.car);
            const auto length=simple::encode_uart(outgoing,output.data(),output.size());
            if(uart_write_bytes(kUart,output.data(),length)!=int(length)) { portENTER_CRITICAL(&mux_);++snapshot_.uart_tx_errors;portEXIT_CRITICAL(&mux_); }
            next=us()/1000+200;
            published_generation=s.car.generation;
        }
        if(xQueueReceive(uart_out_,&outgoing,0)==pdTRUE) {
            outgoing.seq=++seq;const auto length=simple::encode_uart(outgoing,output.data(),output.size());
            const int sent=uart_write_bytes(kUart,output.data(),length);
            if(sent!=int(length)) { portENTER_CRITICAL(&mux_);++snapshot_.uart_tx_errors;portEXIT_CRITICAL(&mux_); }
            std::fill(outgoing.payload.begin(),outgoing.payload.end(),0); // credentials never printed
            std::fill(output.begin(),output.end(),0);
        }
        portENTER_CRITICAL(&mux_);snapshot_.uart_errors+=parser.errors()-parse_errors_before;portEXIT_CRITICAL(&mux_);
    }
}
void Runtime::log_loop() {
    uint32_t generation=0,period=0;int16_t left=0,right=0;bool linked=false;
    led_strip_handle_t observer{};
    led_strip_config_t led{};led.strip_gpio_num=48;led.max_leds=1;
    led.led_model=LED_MODEL_WS2812;led.color_component_format=LED_STRIP_COLOR_COMPONENT_FMT_GRB;
    led_strip_rmt_config_t rmt{};rmt.clk_src=RMT_CLK_SRC_DEFAULT;rmt.resolution_hz=10000000;
    if(led_strip_new_rmt_device(&led,&rmt,&observer)!=ESP_OK) observer=nullptr;
    int observed=-1;
    for(;;) {
        vTaskDelay(pdMS_TO_TICKS(500));const auto s=snapshot();
        const int color=s.car.fpga_link?1:0;
        if(observer && color!=observed) {
            auto err=led_strip_set_pixel(observer,0,0,color?8:0,color?0:8);
            if(err==ESP_OK) err=led_strip_refresh(observer);
            if(err==ESP_OK) observed=color;
        }
        if(s.car.generation!=generation || s.car.left!=left || s.car.right!=right || linked!=s.car.fpga_link || ++period>=10) {
            ESP_LOGI("simple_motion","mode=%s gen=%" PRIu32 " action=%s duty=%d/%d spi=%d ack=%u reason=%s rx=%" PRIu32 " uart_err=%" PRIu32 " spi_err=%" PRIu32,
                s.car.mode==simple::Mode::Manual?"Manual":"AI",s.car.generation,simple::action_name(s.car.action),s.car.left,s.car.right,s.car.fpga_link,s.car.applied_seq,
                simple::reason_name(s.car.reason),s.uart_rx,s.uart_errors,s.spi_errors);
            // All sorting/formatting stays in this background observer, never in control_loop.
            auto samples=s.latency_us;const size_t count=std::min<size_t>(s.latency_count,samples.size());
            std::sort(samples.begin(),samples.begin()+count);
            const auto percentile=[&](unsigned p){return count?samples[(count*p+99)/100-1]:0;};
            ESP_LOGI("simple_diag","samples=%" PRIu32 " window=%u submit_us_p50=%" PRIu32 " p95=%" PRIu32 " p99=%" PRIu32 " max=%" PRIu32 " heap=%" PRIu32 " spi_io=%" PRIu32 " frame=%" PRIu32 " ack=%" PRIu32 " startup=%" PRIu32,
                s.latency_count,unsigned(count),percentile(50),percentile(95),percentile(99),s.latency_max_us,esp_get_free_heap_size(),
                s.spi_io_errors,s.spi_frame_errors,s.spi_ack_errors,s.spi_startup);
            generation=s.car.generation;left=s.car.left;right=s.car.right;linked=s.car.fpga_link;period=0;
        }
    }
}
} // namespace motion
