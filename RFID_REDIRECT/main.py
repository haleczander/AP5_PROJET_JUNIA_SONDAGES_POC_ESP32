import network
import socket
from machine import Pin
import time
import gc
import ujson
import urequests
import urandom
from mfrc522 import MFRC522

# --- LED ---
led = Pin(2, Pin.OUT)

# --- RFID ---
rdr = MFRC522(18, 23, 19, 22, 5)
print("Lecteur MFRC522 initialisé")

BADGE_TIMEOUT = 10
sessions = {}  # token -> uid


# --- Utils ---
def uid_to_str(uid):
    return "".join("{:02X}".format(x) for x in uid)


def generate_token(uid_str):
    token = "".join([hex(urandom.getrandbits(8))[2:] for _ in range(8)])
    sessions[token] = uid_str
    return token


def read_rfid(timeout=10):
    t0 = time.time()
    while True:
        if (time.time() - t0) > timeout:
            return None
        stat, tag_type = rdr.request(rdr.REQIDL)
        if stat == rdr.OK:
            stat, raw_uid = rdr.anticoll()
            if stat == rdr.OK and len(raw_uid) >= 4:
                return uid_to_str(raw_uid)
        time.sleep(0.05)


def check_authorization(rfid_str):
    url = "http://20.56.20.65/authorize"
    headers = {"Content-Type": "application/json"}
    data = ujson.dumps({"rfid": rfid_str})
    try:
        r = urequests.post(url, headers=headers, data=data)
        print("Backend response:", r.status_code, r.text)
        if r.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        print("HTTP error:", e)
        return False


# --- HTML ---
index_html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Accueil</title></head>
<body>
<h1>Bienvenue sur l'ESP32</h1>
<button onclick="login()">Se connecter</button>
<p id="status"></p>
<script>
function login(){
    document.getElementById('status').innerText = "Présentez votre badge...";
    fetch('/auth').then(r=>r.text()).then(s=>{
        if(s.startsWith("OK:")){
            let token = s.split(":")[1];
            window.location = "/success?token=" + token;
        } else {
            document.getElementById('status').innerText = "Accès refusé ou timeout.";
        }
    });
}
</script>
</body>
</html>
"""

success_html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Résultat</title></head>
<body>
<h1>{msg}</h1>
<a href="/">Retour</a>
</body>
</html>
"""

# --- Config AP + STA ---
STA_SSID = "Livebox-EF96"
STA_PASSWORD = "Onalafibreyoupi"

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
ap.config(essid="ESP32_AP", password="12345678")
print("AP active, IP:", ap.ifconfig()[0])

# --- Serveur HTTP ---
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('0.0.0.0', 80))
s.listen(5)
print("Server listening...")

while True:
    conn, addr = s.accept()
    try:
        req = conn.recv(1024).decode()
        path = req.split(' ')[1]
        print("Request path:", path)

        if path == "/":
            conn.send(b"HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n")
            conn.send(index_html.encode())

        elif path == "/auth":
            uid_str = read_rfid(BADGE_TIMEOUT)
            if uid_str:
                if check_authorization(uid_str):
                    led.value(1)
                    token = generate_token(uid_str)
                    response = "OK:" + token
                else:
                    led.value(0)
                    response = "REFUSE"
            else:
                response = "TIMEOUT"

            conn.send(b"HTTP/1.0 200 OK\r\nContent-type: text/plain\r\n\r\n")
            conn.send(response.encode())

        elif path.startswith("/success"):
            token = ""
            if "token=" in path:
                token = path.split("token=")[1]
            if token in sessions:
                msg = "Badge validé ! Accès autorisé."
            else:
                msg = "Accès refusé."
            html = success_html.format(msg=msg)
            conn.send(b"HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n")
            conn.send(html.encode())

        else:
            conn.send(b"HTTP/1.0 404 Not Found\r\n\r\n")

        conn.close()
    except Exception as e:
        print("Error:", e)
        conn.close()
    finally:
        gc.collect()
