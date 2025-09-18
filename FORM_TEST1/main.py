import network
import socket
from machine import Pin
import time

# --- LED et bouton BOOT ---
led = Pin(2, Pin.OUT)
boot_btn = Pin(0, Pin.IN, Pin.PULL_UP)
last_btn_state = 1
badge_present = False
badge_start_time = None
BADGE_TIMEOUT = 10  # secondes

# --- Badge valide ---
valid_rfid = ["123456789"]
badge_status = "En attente"

# --- HTML front ---
html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>ESP32 RFID Login</title></head>
<body>
<h1>Connexion RFID</h1>
<button onclick="startLogin()">Se connecter</button>
<p id="status">En attente</p>
<script>
function startLogin(){
    fetch('/start');
    document.getElementById('status').innerText = 'Lecture du badge...';
    var interval = setInterval(function(){
        fetch('/status').then(r => r.text()).then(s => {
            document.getElementById('status').innerText = s;
            if(s.includes('OK') || s.includes('TIMEOUT')) clearInterval(interval);
        });
    }, 500);
}
</script>
</body>
</html>
"""

# --- AP Wi-Fi ---
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="ESP32_AP", password="12345678")
print("AP active, IP:", ap.ifconfig()[0])

# --- Serveur HTTP ---
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('0.0.0.0', 80))
s.listen(5)
print("Server listening...")

while True:
    # --- Vérifier bouton BOOT ---
    current = boot_btn.value()
    if last_btn_state == 1 and current == 0:
        badge_present = True
        print("BOOT pressed → badge simulé")
        time.sleep(0.2)
    last_btn_state = current

    # --- Accepter connexions HTTP ---
    conn, addr = s.accept()
    try:
        req = conn.recv(1024).decode()
        path = req.split(' ')[1]
        print("Request path:", path)

        if path == "/":
            # reset état front
            badge_status = "En attente"
            badge_start_time = None
            conn.send(b"HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n")
            conn.send(html.encode())

        elif path == "/start":
            badge_status = "Lecture du badge..."
            badge_start_time = time.time()
            badge_present = False
            conn.send(b"HTTP/1.0 200 OK\r\nContent-type: text/plain\r\n\r\nOK")

        elif path == "/status":
            now = time.time()
            if badge_present:
                if "123456789" in valid_rfid:
                    led.value(1)
                    badge_status = "Badge OK! LED allumée"
                else:
                    led.value(0)
                    badge_status = "Badge refusé"
                badge_present = False
                badge_start_time = None
            elif badge_start_time and (now - badge_start_time) > BADGE_TIMEOUT:
                badge_status = "TIMEOUT"
                badge_start_time = None
            conn.send(b"HTTP/1.0 200 OK\r\nContent-type: text/plain\r\n\r\n")
            conn.send(badge_status.encode())
        else:
            conn.send(b"HTTP/1.0 404 Not Found\r\n\r\n")
        conn.close()
    except Exception as e:
        print("Error:", e)
        conn.close()
