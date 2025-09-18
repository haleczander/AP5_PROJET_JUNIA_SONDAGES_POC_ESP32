from machine import Pin
import network, socket

led = Pin(2, Pin.OUT)
button = Pin(0, Pin.IN, Pin.PULL_UP)  # BOOT = GPIO0, actif à 0 quand appuyé

ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="ESP32_AP", password="12345678")
print("AP IP:", ap.ifconfig()[0])

def web_page():
    led_state = "ON" if led.value() else "OFF"
    btn_state = "PRESSED" if button.value() == 0 else "RELEASED"
    html = """<!DOCTYPE html>
<html>
<head><title>ESP32 Web Server</title></head>
<body style="text-align:center;font-family:Helvetica;">
  <h1>ESP32 Web Server</h1>
  <p>LED: <strong>{}</strong></p>
  <p>Button: <strong>{}</strong></p>
  <p><a href="/?led=on"><button>ON</button></a>
     <a href="/?led=off"><button>OFF</button></a></p>
</body>
</html>""".format(led_state, btn_state)
    return html

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)

while True:
    conn, addr = s.accept()
    request = conn.recv(1024).decode()
    print("Reçu:", request)

    if "/?led=on" in request:
        led.value(1)
    if "/?led=off" in request:
        led.value(0)

    response = web_page()
    conn.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n")
    conn.sendall(response)
    conn.close()
