from machine import Pin
import time
led = Pin(2, Pin.OUT)  # GPIO2 = LED embarquée sur beaucoup d’ESP32

while True:
    led.value(1)  # LED on
    time.sleep(1)
    led.value(0)  # LED off
    time.sleep(1)
