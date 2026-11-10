#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>

namespace simple {
template<size_t Capacity=32> class LogRing {
public:
    struct Record { uint64_t seq{},ms{};char text[256]{}; };
    struct Read { size_t count{};uint64_t next{},dropped{}; };
    // Caller owns synchronization. No allocation, sockets or flash.
    void append(uint64_t ms,const char* text) {
        auto& r=records_[sequence_%Capacity];r.seq=++sequence_;r.ms=ms;
        std::snprintf(r.text,sizeof(r.text),"%s",text);
    }
    Read read(uint64_t after,Record* output,size_t capacity) const {
        Read result{};result.next=sequence_;
        if(after>=sequence_) return result;
        const auto oldest=sequence_>Capacity?sequence_-Capacity+1:1;
        auto start=after+1;
        if(start<oldest) { result.dropped=oldest-start;start=oldest; }
        for(auto seq=start;seq<=sequence_ && result.count<capacity;++seq)
            output[result.count++]=records_[(seq-1)%Capacity];
        if(result.count) result.next=output[result.count-1].seq;
        return result;
    }
private:
    static_assert(Capacity>0);
    std::array<Record,Capacity> records_{};
    uint64_t sequence_{};
};
}
