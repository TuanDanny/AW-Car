# Xiaozhi source provenance

Baseline: https://github.com/78/xiaozhi-esp32
Tag v2.5.2, commit `49b4380b3faa0ceadd28a3e78aaf0f311c46c57e`, MIT (LICENSE retained).
Imported selectively from the already verified AW-Car Xiaozhi snapshot, not decompiled
from a binary. One board only: INMP441, MAX98357A, SSD1306. Keep Chinese sounds,
audio engines/codecs, cloud protocols/MCP, fonts/assets needed by that profile.

Changes: STA-only board/network, UART car tools and captured session-generation
context, observer LED. Removed Brain HTTP/dashboard, ARM/Gate/Web chat coupling,
RGB tools, unrelated board profiles and their dependencies. Automatic cloud firmware
installation is disabled for this custom profile; activation/service configuration
continues using upstream OTA discovery and existing NVS identity.

Local `components/ssid_store` and `components/xiaozhi_network` retain required upstream
manager/network implementation with their LICENSE files. `dependencies.lock` pins
managed components and hashes. This is a rebuilt derivative, not a byte-identical
reconstruction of the original firmware.
