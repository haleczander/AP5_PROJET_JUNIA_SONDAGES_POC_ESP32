import network
import usocket as socket
import ure
import gc

# --- Config AP + STA ---
STA_SSID = "JUNIA_LAB"
STA_PASSWORD = "813nV3nue@2025!"
AP_SSID = "ESP32_AP"
AP_PASSWORD = "12345678"

from machine import Pin
import time

# --- LED et bouton BOOT ---
led = Pin(2, Pin.OUT)
boot_btn = Pin(0, Pin.IN, Pin.PULL_UP)
led_state = False
last_btn_state = 1

# --- STA Wi-Fi ---
sta = network.WLAN(network.STA_IF)
sta.active(True)
if not sta.isconnected():
    print("Connecting to STA Wi-Fi...")
    sta.connect(STA_SSID, STA_PASSWORD)
    while not sta.isconnected():
        time.sleep(1)
print("STA connected, IP:", sta.ifconfig()[0])

# --- AP Wi-Fi ---
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid=AP_SSID, password=AP_PASSWORD)
print("AP active, IP:", ap.ifconfig()[0])

# --- Proxy HTTP chunké ---
def proxy_http(url, conn, chunk_size=512):
    try:
        m = ure.match(r"https?://([^/]+)(/.*)?", url)
        host, path = m.group(1), m.group(2) or "/"
        addr = socket.getaddrinfo(host, 80)[0][-1]
        s = socket.socket()
        s.connect(addr)
        s.send(b"GET %s HTTP/1.0\r\nHost: %s\r\n\r\n" % (path.encode(), host.encode()))
        
        conn.send(b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n")
        while True:
            data = s.recv(chunk_size)
            if not data:
                break
            conn.send(data)
        s.close()
    except Exception as e:
        print("Proxy error:", e)
        conn.send(b"<h1>Error fetching URL</h1>")
    finally:
        conn.close()
        gc.collect()

# --- Serveur HTTP AP ---
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('0.0.0.0', 80))
s.listen(5)
print("Server listening...")

while True:
    # --- Vérifier bouton BOOT ---
    current = boot_btn.value()
    if last_btn_state == 1 and current == 0:
        led_state = not led_state
        led.value(led_state)
        print("BOOT pressed, LED:", "ON" if led_state else "OFF")
        time.sleep(0.2)
    last_btn_state = current

    # --- Accepter connexion ---
    conn, addr = s.accept()
    try:
        req = conn.recv(512).decode()
        path = req.split(' ')[1]
        print("Request path:", path)

        if path == "/":
            # pipeline direct de Google
            proxy_http("https://example.net/", conn)
        elif path == "/toggle":
            led_state = not led_state
            led.value(led_state)
            conn.send(b"HTTP/1.0 200 OK\r\nContent-type: text/plain\r\n\r\nOK")
            conn.close()
        else:
            conn.send(b"HTTP/1.0 404 Not Found\r\n\r\n")
            conn.close()
    except Exception as e:
        print("Error:", e)
        conn.close()
    finally:
        gc.collect()

