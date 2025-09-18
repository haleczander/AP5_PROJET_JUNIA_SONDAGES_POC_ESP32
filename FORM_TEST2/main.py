import network
import socket
from machine import Pin
import time
import gc
import ujson

# --- LED et bouton BOOT ---
led = Pin(2, Pin.OUT)
boot_btn = Pin(0, Pin.IN, Pin.PULL_UP)
last_btn_state = 1
badge_present = False
badge_start_time = None
BADGE_TIMEOUT = 10  # secondes

# --- Badge valide ---
valid_rfid = ["123456789"]
badge_status = "idle"

# --- Données du formulaire ---
form_data = {
    "title": "Répartissez vos étoiles",
    "stars_total": 10,  # nombre max d'étoiles
    "projects": [
        {"id": 1, "name": "Projet Alpha"},
        {"id": 2, "name": "Projet Beta"},
        {"id": 3, "name": "Projet Gamma"},
    ]
}

# --- Stats votes (RAM uniquement) ---
vote_stats = {
    "total_votes": 0,
    "projects": {p["id"]: {"name": p["name"], "stars": 0} for p in form_data["projects"]}
}

# --- HTML embarqué ---
index_html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Accueil ESP32</title></head>
<body>
<h1>Bienvenue sur l'ESP32</h1>
<div id="stats">Chargement des stats...</div>
<button id="loginBtn">S'authentifier</button>
<script>
function loadStats(){
  fetch('/vote/stats').then(r=>r.json()).then(data=>{
    let html = `<h2>Stats actuelles</h2><p>Total votes: ${data.total_votes}</p><ul>`;
    for (let pid in data.projects) {
      let p = data.projects[pid];
      html += `<li>${p.name}: ${p.stars} étoiles</li>`;
    }
    html += "</ul>";
    document.getElementById("stats").innerHTML = html;
  });
}
document.getElementById("loginBtn").onclick=()=>{window.location='/login';};
loadStats();
setInterval(loadStats,5000);
</script>
</body>
</html>
"""

login_html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>RFID Login</title></head>
<body>
<h1>Connexion RFID</h1>
<p id="status">Lecture du badge...</p>
<script>
var interval = setInterval(function(){
    fetch('/status').then(r => r.text()).then(s => {
        document.getElementById('status').innerText = s;
        if(s.includes('OK')) window.location='/form';
        if(s.includes('TIMEOUT')) clearInterval(interval);
    });
}, 500);
</script>
</body>
</html>
"""

form_html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Formulaire de vote</title></head>
<body>
<h1 id="title">Vote</h1>
<form id="voteForm"></form>
<p><button type="button" id="sendBtn">Envoyer</button></p>
<p id="result"></p>
<script>
let starsTotal = 0;
fetch('/form_data').then(r=>r.json()).then(data=>{
  document.getElementById("title").innerText=data.title+` (max ${data.stars_total} étoiles)`;
  starsTotal=data.stars_total;
  let html="";
  data.projects.forEach(p=>{
    html+=`<label>${p.name}: <input type='number' min='0' max='${starsTotal}' value='0' data-id='${p.id}'></label><br>`;
  });
  document.getElementById("voteForm").innerHTML=html;
});
document.getElementById("sendBtn").onclick=()=>{
  const inputs=document.querySelectorAll("#voteForm input");
  let votes={}, sum=0;
  inputs.forEach(i=>{
    let val=parseInt(i.value)||0;
    votes[i.dataset.id]=val; sum+=val;
  });
  if(sum > starsTotal){
    document.getElementById("result").innerText=`Erreur : maximum ${starsTotal} étoiles, vous avez mis ${sum}.`;
    return;
  }
  fetch("/vote",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({votes})})
  .then(r=>r.json()).then(res=>{
    if(res.result==="ok"){
      document.getElementById("result").innerText="Vote enregistré !";
    } else {
      document.getElementById("result").innerText="Erreur: "+JSON.stringify(res);
    }
  });
};
</script>
</body>
</html>
"""

# --- Helpers ---
def send_json(conn, data):
    conn.send(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
    conn.send(ujson.dumps(data).encode())

def send_html(conn, html):
    conn.send(b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n")
    conn.send(html.encode())

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
    current = boot_btn.value()
    if last_btn_state == 1 and current == 0:
        badge_present = True
        print("BOOT pressed → badge simulé")
        time.sleep(0.2)
    last_btn_state = current

    conn, addr = s.accept()
    try:
        req = conn.recv(1024).decode()
        if not req:
            conn.close()
            continue
        method, path, _ = req.split(" ", 2)
        now = time.time()
        # --- Pages HTML ---
        if path == "/" or path == "/index.html":
            send_html(conn, index_html)
        elif path == "/login":
            badge_status = "Lecture du badge..."
            badge_start_time = time.time()
            badge_present = False
            send_html(conn, login_html)
        elif path == "/form":
            send_html(conn, form_html)
        # --- API JSON ---
        elif path == "/form_data":
            send_json(conn, form_data)
        elif path == "/vote/stats":
            send_json(conn, vote_stats)
        elif path == "/status":
            if badge_status == "Lecture du badge..." or badge_status == "idle":
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
            conn.send(b"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\n")
            conn.send(badge_status.encode())
        elif path == "/vote" and method == "POST":
            try:
                body = req.split("\r\n\r\n", 1)[1]
                data = ujson.loads(body)
                if "votes" in data:
                    total = sum(data["votes"].values())
                    if total <= form_data["stars_total"]:
                        vote_stats["total_votes"] += 1
                        for pid, stars in data["votes"].items():
                            pid = int(pid)
                            if pid in vote_stats["projects"]:
                                vote_stats["projects"][pid]["stars"] += stars
                        send_json(conn, {"result": "ok"})
                    else:
                        send_json(conn, {"error": f"Maximum {form_data['stars_total']} étoiles"})
                else:
                    send_json(conn, {"error": "Format invalide"})
            except Exception as e:
                send_json(conn, {"error": str(e)})
        else:
            conn.send(b"HTTP/1.0 404 Not Found\r\n\r\n")
        conn.close()
    except Exception as e:
        print("Error:", e)
        try: conn.close()
        except: pass
    finally:
        gc.collect()
