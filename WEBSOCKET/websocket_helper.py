import network
import uasyncio as asyncio
from machine import Pin
import websocket_helper as ws_helper
import usocket as socket

led = Pin(2, Pin.OUT)
led_state = False
clients = []

html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>ESP32 WS LED</title></head>
<body>
<h1>ESP32 WebSocket LED</h1>
<p>LED state: <span id="state">%STATE%</span></p>
<button onclick="toggle()">Toggle LED</button>
<script>
var ws = new WebSocket('ws://' + location.host + '/ws');
ws.onmessage = function(evt){ document.getElementById('state').innerText = evt.data=="1"?"ON":"OFF"; };
function toggle(){ ws.send('toggle'); }
</script>
</body>
</html>
"""

# --- Lancer AP ---
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="ESP32_AP", password="12345678")
print("AP active, IP:", ap.ifconfig()[0])

async def serve_client(reader, writer):
    global led_state
    try:
        request = await reader.readline()
        while await reader.readline() != b"\r\n":
            pass
        if b"GET /ws" in request:
            sock = writer.get_extra_info('socket')
            if ws_helper.handshake(sock):
                clients.append(sock)
                while True:
                    msg = ws_helper.recv(sock)
                    if not msg: break
                    if msg == "toggle":
                        led_state = not led_state
                        led.value(led_state)
                        # notifier tous les clients
                        for c in clients[:]:
                            try:
                                ws_helper.send(c, "1" if led_state else "0")
                            except:
                                clients.remove(c)
        else:
            writer.write(b"HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n")
            writer.write(html.replace("%STATE%", "ON" if led_state else "OFF").encode())
            await writer.drain()
            await writer.aclose()
    except:
        await writer.aclose()

async def main():
    server = await asyncio.start_server(serve_client, "0.0.0.0", 80)
    print("Server running on 192.168.4.1:80")
    while True:
        await asyncio.sleep(1)

asyncio.run(main())
