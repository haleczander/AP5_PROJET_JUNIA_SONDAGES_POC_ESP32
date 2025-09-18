import network
import time
from machine import Pin
try:
  import usocket as socket
except:
  import socket
  
led = Pin(2, Pin.OUT)

def connect_to_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    if not wlan.active():
        wlan.active(True)

    if not wlan.isconnected():
        print(f"Try connect to SSID : {ssid}")
        wlan.connect(ssid, password)

        while not wlan.isconnected():
            print('.', end = " ")
            led.value(1)
            time.sleep_ms(250)
            led.value(0)
            time.sleep_ms(250)
            
    led.value(1)
    return wlan

def display_wifi_info(wlan):
    print("\nLocal IP: {}\nSubnet mask: {}\nIP Gateway: {}\nDNS:{}".format(*wlan.ifconfig()))
    print("BSSID: {:02x}:{:02x}:{:02x}:{:02x}:{:02x}:{:02x}".format(*wlan.config("mac")))
    print(f"RSSI: {wlan.status('rssi')} dB")

def accept_captive(url):
    try:
        print("Calling captive portal URL:", url)
        resp = urequests.get(url)
        print("Status:", resp.status_code)
        print("Response:", resp.text[:200])  # afficher un bout pour debug
        resp.close()
        return True
    except Exception as e:
        print("Error:", e)
        return False

def web_page():
  if led.value() == 1:
    gpio_state="ON"
  else:
    gpio_state="OFF"
  
  html = """<html><head> <title>ESP Web Server</title> <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,"> <style>html{font-family: Helvetica; display:inline-block; margin: 0px auto; text-align: center;}
  h1{color: #0F3376; padding: 2vh;}p{font-size: 1.5rem;}.button{display: inline-block; background-color: #e7bd3b; border: none; 
  border-radius: 4px; color: white; padding: 16px 40px; text-decoration: none; font-size: 30px; margin: 2px; cursor: pointer;}
  .button2{background-color: #4286f4;}</style></head><body> <h1>ESP Web Server</h1> 
  <p>GPIO state: <strong>""" + gpio_state + """</strong></p><p><a href="/?led=on"><button class="button">ON</button></a></p>
  <p><a href="/?led=off"><button class="button button2">OFF</button></a></p></body></html>"""
  return html

def start_ap(essid="ESP32_AP", password="12345678"):
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=essid, password=password, authmode=network.AUTH_WPA_WPA2_PSK)
    while not ap.active():
        print('.', end=' ')
        time.sleep(0.5)
    print(f"\n✅ AP actif {ap.active()}: {essid} | IP: {ap.ifconfig()[0]}")
    return ap

def start_server(ip):
    ip='0.0.0.0'
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((ip, 80))
    s.listen(1)#5)
    print(f"🌐 Serveur web actif sur http://{ip}")

    while True:
        conn, addr = s.accept()
        print('Connexion de %s' % str(addr))
        request = conn.recv(1024).decode()
        print('Requête:', request)
        if '/?led=on' in request:
            led.value(1)
        if '/?led=off' in request:
            led.value(0)
        response = web_page()
        conn.send('HTTP/1.1 200 OK\n')
        conn.send('Content-Type: text/html\n')
        conn.send('Connection: close\n\n')
        conn.sendall(response.encode())
        conn.close()

if __name__=="__main__":
    # my_wlan = connect_to_wifi(ssid="JUNIA_GUEST", password="813nV3nue@2024")

    # # my_wlan = connect_to_wifi(ssid="JUNIA_STUDENTS", password="813nV3nue@Jun1a")
    # # portal_url = "https://eu.network-auth.com/splash/0GMJlad.6.3/grant?continue_url=https://www.junia.com/fr/"
    # # my_wlan = connect_to_wifi(ssid="JUNIA_LAB", password="")
    # # my_wlan = connect_to_wifi(ssid="Alex", password="")

    # display_wifi_info(my_wlan)
    
    # s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # s.bind(('', 80))
    # s.listen(5)
    # print("Serveur web actif sur http://{}".format(my_wlan.ifconfig()[0]))
    
    # while True:
    #     conn, addr = s.accept()
    #     print('Got a connection from %s' % str(addr))
    #     request = conn.recv(1024)
    #     request = str(request)
    #     print('Content = %s' % request)
    #     led_on = request.find('/?led=on')
    #     led_off = request.find('/?led=off')
    #     if led_on == 6:
    #         print('LED ON')
    #         led.value(1)
    #     if led_off == 6:
    #         print('LED OFF')
    #         led.value(0)
    #     response = web_page()
    #     conn.send('HTTP/1.1 200 OK\n')
    #     conn.send('Content-Type: text/html\n')
    #     conn.send('Connection: close\n\n')
    #     conn.sendall(response)
    #     conn.close()
    
    led.value(0)
    ap = start_ap("ESP32_AP", "12345678")
    start_server(ap.ifconfig()[0])