import network
import time
from machine import Pin
import gc

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
        print(f"Connexion à SSID : {ssid}")
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

def web_page():
    if led.value() == 1:
        gpio_state = "ON"
    else:
        gpio_state = "OFF"
 
    html = """<!DOCTYPE html>
<html>
<head>
    <title>ESP Web Server</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        html{font-family: Helvetica; display:inline-block; margin: 0px auto; text-align: center;}
        h1{color: #0F3376; padding: 2vh;}
        p{font-size: 1.5rem;}
        .button{display: inline-block; background-color: #e7bd3b; border: none;
        border-radius: 4px; color: white; padding: 16px 40px; text-decoration: none; 
        font-size: 30px; margin: 2px; cursor: pointer;}
        .button2{background-color: #4286f4;}
    </style>
</head>
<body>
    <h1>ESP Web Server</h1>
    <p>GPIO state: <strong>""" + gpio_state + """</strong></p>
    <p><a href="/?led=on"><button class="button">ON</button></a></p>
    <p><a href="/?led=off"><button class="button button2">OFF</button></a></p>
</body>
</html>"""
    return html

def handle_request(conn):
    """Traite une requête HTTP avec gestion optimisée des timeouts"""
    try:
        # Timeout court pour recevoir la requête
        conn.settimeout(5.0)
        
        # Lire la requête par petits blocs
        request_data = b""
        try:
            while True:
                chunk = conn.recv(512)  # Blocs plus petits
                if not chunk or b'\r\n\r\n' in request_data:
                    break
                request_data += chunk
                if len(request_data) > 2048:  # Limiter la taille
                    break
        except Exception as e:
            print(f"Erreur lecture requête: {e}")
            return False
        
        request = request_data.decode('utf-8', 'ignore')
        print(f'Requête reçue: {request.split()[0:2] if request.split() else "vide"}')
        
        # Parser la requête
        led_on = request.find('GET /?led=on')
        led_off = request.find('GET /?led=off')
        
        if led_on >= 0:
            print('LED ON')
            led.value(1)
        elif led_off >= 0:
            print('LED OFF')
            led.value(0)
        
        # Générer la réponse
        response_body = web_page()
        response_headers = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            "Content-Length: {}\r\n"
            "Connection: close\r\n"
            "Cache-Control: no-cache\r\n"
            "\r\n"
        ).format(len(response_body.encode('utf-8')))
        
        # Envoyer la réponse en une fois
        full_response = response_headers + response_body
        
        # Timeout plus long pour l'envoi
        conn.settimeout(10.0)
        conn.sendall(full_response.encode('utf-8'))
        
        print("Réponse envoyée avec succès")
        return True
        
    except OSError as e:
        if e.args[0] == 110:  # ETIMEDOUT
            print("Timeout lors de l'envoi de la réponse")
        else:
            print(f"Erreur OSError: {e}")
        return False
    except Exception as e:
        print(f"Erreur traitement requête: {e}")
        return False

def start_server(wlan):
    """Serveur web optimisé contre les timeouts"""
    server_socket = None
    
    try:
        # Créer le socket serveur
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind et listen
        server_socket.bind(('', 80))
        server_socket.listen(3)  # Queue plus petite
        
        # Timeout pour accept()
        server_socket.settimeout(30.0)
        
        ip = wlan.ifconfig()[0]
        print(f"\n🌐 Serveur web actif sur:")
        print(f"   http://{ip}")
        print(f"   Connectez-vous depuis votre navigateur")
        print("=" * 50)
        
        request_count = 0
        
        while True:
            client_conn = None
            try:
                # Accepter une connexion
                client_conn, addr = server_socket.accept()
                request_count += 1
                print(f"\n[{request_count}] Connexion de {addr[0]}:{addr[1]}")
                
                # Traiter la requête
                success = handle_request(client_conn)
                
                if success:
                    print(f"[{request_count}] ✅ Requête traitée avec succès")
                else:
                    print(f"[{request_count}] ❌ Erreur lors du traitement")
                
                # Nettoyage mémoire périodique
                if request_count % 10 == 0:
                    gc.collect()
                    print(f"Mémoire libre: {gc.mem_free()} bytes")
                    
            except OSError as e:
                if e.args[0] == 110:  # ETIMEDOUT sur accept
                    print(".", end="")  # Heartbeat silencieux
                else:
                    print(f"Erreur serveur: {e}")
                    
            except Exception as e:
                print(f"Erreur inattendue: {e}")
                
            finally:
                # Fermer la connexion client
                if client_conn:
                    try:
                        client_conn.close()
                    except:
                        pass
                        
    except Exception as e:
        print(f"Erreur critique serveur: {e}")
        
    finally:
        # Nettoyer le socket serveur
        if server_socket:
            try:
                server_socket.close()
            except:
                pass
        print("\nServeur arrêté")

if __name__ == "__main__":
    print("🚀 Démarrage ESP32 Web Server")
    
    # Configuration WiFi (décommentez celle qui marche)
    # my_wlan = connect_to_wifi(ssid="JUNIA_GUEST", password="813nV3nue@2024")
    my_wlan = connect_to_wifi(ssid="JUNIA_STUDENTS", password="813nV3nue@Jun1a")
    # my_wlan = connect_to_wifi(ssid="JUNIA_LAB", password="")
    # my_wlan = connect_to_wifi(ssid="VotreWiFi", password="VotreMotDePasse")
    
    display_wifi_info(my_wlan)
    
    # Démarrer le serveur
    print("\n🔧 Configuration du serveur web...")
    start_server(my_wlan)