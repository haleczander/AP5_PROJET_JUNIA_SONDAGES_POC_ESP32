# ESP32 POC

(Tuto flash)[https://randomnerdtutorials.com/flashing-micropython-firmware-esptool-py-esp32-esp8266/]

Erase: 
Presser "BOOT"
```cmd
python -m esptool --chip esp32 erase_flash
```

Flasher Micropython:
```cmd
python -m esptool --chip esp32 --port COM3 write_flash -z 0x1000 .\ESP32_GENERIC-20250911-v1.26.1.bin
```