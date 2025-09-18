import network
import socket
from machine import Pin
import time

# LED et bouton BOOT
led = Pin(2, Pin.OUT)
boot_btn = Pin(0, Pin.IN, Pin.PULL_UP)
led_state = False
last_btn_state = 1

# HTML
html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>ESP32 LED</title></head>
<body>
<h1>ESP32 LED Control</h1>
<p>LED state: <span id="state">UNKNOWN</span></p>
<button onclick="toggle()">Toggle LED</button>
<script>
function updateState() {
    fetch('/status').then(r => r.text()).then(s => document.getElementById('state').innerText = s=="1"?"ON":"OFF");
}
setInterval(updateState, 500);
function toggle() { fetch('/toggle'); }
</script>
</body>
</html>
"""

# Lancer AP
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="ESP32_AP", password="12345678")
print("AP active, IP:", ap.ifconfig()[0])

# Serveur HTTP
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('0.0.0.0', 80))
s.listen(5)
print("Server listening...")

while True:
    # Vérifier bouton BOOT
    current = boot_btn.value()
    if last_btn_state == 1 and current == 0:
        led_state = not led_state
        led.value(led_state)
        print("BOOT pressed, LED:", "ON" if led_state else "OFF")
        time.sleep(0.2)
    last_btn_state = current

    # Accepter connexions HTTP
    conn, addr = s.accept()
    try:
        req = conn.recv(1024).decode()
        first_line = req.split('\r\n')[0]
        if 'GET /toggle' in first_line:
            led_state = not led_state
            led.value(led_state)
        elif 'GET /led=on' in first_line:
            led_state = True
            led.value(1)
        elif 'GET /led=off' in first_line:
            led_state = False
            led.value(0)
        elif 'GET /status' in first_line:
            conn.send(b"HTTP/1.0 200 OK\r\nContent-type: text/plain\r\n\r\n")
            conn.send(b"1" if led.value() else b"0")
            conn.close()
            continue

        conn.send(b"HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n")
        conn.send(html.encode())
    except Exception as e:
        print("Error:", e)
    finally:
        conn.close()
