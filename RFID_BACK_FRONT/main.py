from machine import Pin
import network
import time
import socket
import gc
import ujson
import urequests

from mfrc522 import MFRC522
from AP import AP_PASSWD, AP_SSID
from STA import STA_SSID, STA_PASSWD
from http_utils import response, parse_request, pass_through

RFC_TIMEOUT_S=10

ESP32_LED=Pin(2, Pin.OUT)
RFC522=MFRC522(18,23,19,22,5)

def get_html_content(html_file):
    with open(html_file, 'r') as f:
        html_content = f.read()
    return html_content

def blink_led(period):
    ESP32_LED.value(1)
    time.sleep(period/2)
    ESP32_LED.value(0)
    time.sleep(period/2)

def connect_sta(ssid=STA_SSID, passwd=STA_PASSWD):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if not sta.isconnected():
        print(f"Connecting to STA Wi-Fi ({ssid})...")
        sta.connect(ssid, passwd)
        while not sta.isconnected():
            blink_led(.25)
    print("STA connected, IP:", sta.ifconfig()[0])
    return sta
    
def start_ap(ssid=AP_SSID, passwd=AP_PASSWD):
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="ESP32_AP", password="12345678")
    print("AP active, IP:", ap.ifconfig()[0])
    return ap

def start_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 80))
    s.listen(5)
    print("Server listening...")
    return s
    
def read_rfid(timeout=10):
    def uid_to_str(uid):
        return "".join("{:02X}".format(x) for x in uid)
    
    t0 = time.time()
    while (time.time() - t0) <= timeout:
        stat, tag_type = RFC522.request(RFC522.REQIDL)
        if stat == RFC522.OK:
            stat, raw_uid = RFC522.anticoll()
            if stat == RFC522.OK and len(raw_uid) >= 4:
                return uid_to_str(raw_uid)
        # time.sleep(.05)
        blink_led(0.05)

def _handle_lobby(connection, body):
    pass_through(
        connection, 
        urequests.get,
        f"{FRONTEND_URL}/index.html"
    )


def _handle_auth(connection, body):
    uid_str = read_rfid(RFC_TIMEOUT_S)
    
    if uid_str is None:
        response_text = "TIMEOUT"
        status_code = 400
        response(connection, 408, "Délai d'authentification expiré")
    
    pass_through( 
        connection, 
        urequests.post, 
        f"{BACKEND_URL}/authorize", 
        headers={"Content-Type": "application/json"}, 
        data=ujson.dumps({"rfid": uid_str})
    )

    
def _handle_submit(connection, body):
    pass_through(
        connection, 
        urequests.post, 
        f"{BACKEND_URL}/vote", 
        headers={"Content-Type": "application/json"}, 
        data=body
    )
    
def _handle_stats(connection, body):
    pass_through(
        connection, 
        urequests.get,
        f"{BACKEND_URL}/projects"
    )

def _handle_404(connection, body):
    response(connection, 404)
        
REQUESTS_CALLBACKS = {
    "/": _handle_lobby,
    "/auth": _handle_auth,
    "/submit": _handle_submit,
    "/stats": _handle_stats,
}
        

def handle_requests(socket):
    conn, addr = socket.accept()
    try:
        method, path, body = parse_request(conn)
        print("Request path:", path)
        REQUESTS_CALLBACKS.get(path, _handle_404)(conn, body)
        conn.close()
    except Exception as e:
        print("Error:", e)
        conn.close()
    finally:
        gc.collect()
        
        

BASE_URL="http://20.56.20.65"   
BACKEND_URL = f"{BASE_URL}/backend"
FRONTEND_URL = f"{BASE_URL}/frontend"
        
def main():
    sta = connect_sta()
    ap = start_ap()
    socket = start_socket()
    while True: 
        print("RAM libre:", gc.mem_free())
        print("STA active:", sta.active(), "Connected:", sta.isconnected())
        print("AP active:", ap.active())
        try:
            socket.fileno()  
            print("Socket actif")
        except Exception:
            print("Socket fermé ou invalide")
        handle_requests(socket)
    
if __name__ == "__main__":
    main()