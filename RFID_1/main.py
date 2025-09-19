from mfrc522 import MFRC522
from machine import Pin, SPI
import time
from os import uname

def convert_uid_to_string(uid):
    """Convertit l'UID en format hexadécimal lisible"""
    return ":".join(["{:02X}".format(x) for x in uid[:4]])

def test_registres(rdr):
    """Test de lecture des registres principaux du RC522"""
    print("\n=== Lecture des registres du RC522 ===")
    registres = {
        0x00: "CommandReg",
        0x01: "ComIEnReg", 
        0x02: "DivlEnReg",
        0x04: "ComIrqReg",
        0x06: "ErrorReg",
        0x0A: "FIFODataReg",
        0x0C: "FIFOLevelReg",
        0x14: "TxControlReg",
        0x37: "VersionReg"
    }
    
    for reg_addr, reg_name in registres.items():
        try:
            val = rdr._rreg(reg_addr)
            print(f"{reg_name} (0x{reg_addr:02X}) = 0x{val:02X}")
        except Exception as e:
            print(f"Erreur lecture {reg_name}: {e}")

def lire_carte_simple(rdr):
    """Lecture simple d'une carte RFID"""
    print("\n=== Lecture de carte RFID ===")
    
    try:
        # Demande de détection de carte
        stat, tag_type = rdr.request(rdr.REQIDL)
        print(f"Request status: {stat}, Tag type: {tag_type}")
        
        if stat == rdr.OK:
            print("Carte détectée !")
            
            # Anti-collision pour obtenir l'UID
            stat, raw_uid = rdr.anticoll()
            print(f"Anticoll status: {stat}, Raw UID: {raw_uid}")
            
            if stat == rdr.OK and len(raw_uid) >= 4:
                uid_string = convert_uid_to_string(raw_uid)
                print(f"UID de la carte: {uid_string}")
                
                # Sélection de la carte
                if rdr.select_tag(raw_uid) == rdr.OK:
                    print("Carte sélectionnée avec succès")
                    return raw_uid
                else:
                    print("Erreur lors de la sélection de la carte")
            else:
                print("Erreur lors de l'anti-collision")
        else:
            print("Aucune carte détectée")
            
    except Exception as e:
        print(f"Erreur lors de la lecture: {e}")
        
    return None

def lire_bloc_donnees(rdr, uid, secteur=1, bloc=4):
    """Lecture d'un bloc de données avec authentification"""
    print(f"\n=== Lecture du bloc {bloc} (secteur {secteur}) ===")
    
    # Clé par défaut pour l'authentification
    key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
    
    try:
        # Authentification
        auth_status = rdr.auth(rdr.AUTHENT1A, bloc, key, uid)
        
        if auth_status == rdr.OK:
            print("Authentification réussie")
            
            # Lecture du bloc
            data = rdr.read(bloc)
            
            if data:
                print(f"Données du bloc {bloc}:")
                print("Hex:", " ".join([f"{x:02X}" for x in data]))
                print("ASCII:", "".join([chr(x) if 32 <= x <= 126 else '.' for x in data]))
                return data
            else:
                print(f"Erreur lors de la lecture du bloc {bloc}")
        else:
            print(f"Échec de l'authentification pour le bloc {bloc}")
            
        # Arrêt de l'authentification
        rdr.stop_crypto1()
        
    except Exception as e:
        print(f"Erreur lors de la lecture des données: {e}")
        
    return None

def ecrire_bloc_donnees(rdr, uid, bloc, donnees):
    """Écriture dans un bloc de données"""
    print(f"\n=== Écriture dans le bloc {bloc} ===")
    
    # Clé par défaut pour l'authentification
    key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
    
    # S'assurer que les données font exactement 16 bytes
    if len(donnees) < 16:
        donnees = donnees + [0x00] * (16 - len(donnees))
    elif len(donnees) > 16:
        donnees = donnees[:16]
    
    try:
        # Authentification
        auth_status = rdr.auth(rdr.AUTHENT1A, bloc, key, uid)
        
        if auth_status == rdr.OK:
            print("Authentification réussie")
            
            # Écriture
            write_status = rdr.write(bloc, donnees)
            
            if write_status == rdr.OK:
                print(f"Écriture réussie dans le bloc {bloc}")
                print("Données écrites:", " ".join([f"{x:02X}" for x in donnees]))
                return True
            else:
                print(f"Erreur lors de l'écriture dans le bloc {bloc}")
        else:
            print(f"Échec de l'authentification pour le bloc {bloc}")
            
        # Arrêt de l'authentification
        rdr.stop_crypto1()
        
    except Exception as e:
        print(f"Erreur lors de l'écriture: {e}")
        
    return False

def main():
    """Fonction principale"""
    print("=== Initialisation du lecteur MFRC522 sur ESP32 ===")
    print(f"Plateforme détectée: {uname()[0]}")
    
    try:
        # Initialisation du lecteur MFRC522
        # Pins: SCK=18, MOSI=23, MISO=19, RST=22, CS=5
        rdr = MFRC522(18, 23, 19, 22, 5)
        print("Lecteur MFRC522 initialisé avec succès")
        
        # Test des registres
        test_registres(rdr)
        
        print("\n" + "="*50)
        print("Approchez une carte RFID du lecteur...")
        print("Appuyez sur Ctrl+C pour arrêter")
        
        while True:
            # Tentative de lecture d'une carte
            uid = lire_carte_simple(rdr)
            
            if uid:
                # Lecture d'un bloc de données (bloc 4 par exemple)
                data = lire_bloc_donnees(rdr, uid, secteur=1, bloc=4)
                
                # Exemple d'écriture (décommentez si nécessaire)
                # nouvelles_donnees = [0x48, 0x65, 0x6C, 0x6C, 0x6F, 0x20, 0x52, 0x46, 0x49, 0x44, 0x21, 0x00, 0x00, 0x00, 0x00, 0x00]  # "Hello RFID!"
                # ecrire_bloc_donnees(rdr, uid, 4, nouvelles_donnees)
                
                print("\nRetirez la carte et approchez-en une autre...")
                time.sleep(2)
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nArrêt du programme...")
    except Exception as e:
        print(f"Erreur d'initialisation: {e}")
        print("Vérifiez les connexions:")
        print("- SCK  -> GPIO 18")
        print("- MOSI -> GPIO 23") 
        print("- MISO -> GPIO 19")
        print("- RST  -> GPIO 22")
        print("- CS   -> GPIO 5")
        print("- VCC  -> 3.3V")
        print("- GND  -> GND")

if __name__ == "__main__":
    main()