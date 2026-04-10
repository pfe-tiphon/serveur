import eventlet
eventlet.monkey_patch()

import webbrowser
import socket
import time
import base64
import json
import os
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Configuration
ESP32_IP = '192.168.4.1'
PORT = 3333
STORAGE_DIR = "captures"

if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

# Variables de contrôle
jetson_online = False
last_jetson_time = 0
esp_socket = None 

def check_jetson_timeout():
    """Surveille si la Jetson ne donne plus de signe de vie."""
    global jetson_online, last_jetson_time
    while True:
        if jetson_online and (time.time() - last_jetson_time > 5.0):
            jetson_online = False
            print("[PC] Timeout : Perte de liaison avec la Jetson")
            socketio.emit('jetson_status', {'online': False})
        eventlet.sleep(1)

def listen_to_esp():
    """Gère la communication TCP bidirectionnelle avec l'ESP32."""
    global jetson_online, last_jetson_time, esp_socket
    
    socketio.start_background_task(check_jetson_timeout)

    while True:
        try:
            print(f"[PC] Tentative de connexion à l'ESP32 ({ESP32_IP})...")
            esp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            esp_socket.connect((ESP32_IP, PORT))
            
            print("[PC] Liaison ESP32 active.")
            socketio.emit('esp_status', {'connected': True})

            buffer = ""
            while True:
                chunk = esp_socket.recv(16384).decode(errors='ignore')
                if not chunk: break
                buffer += chunk

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line: continue

                    try:
                        data = json.loads(line)
                        
                        # Mise à jour du statut Jetson
                        last_jetson_time = time.time()
                        if not jetson_online:
                            jetson_online = True
                            socketio.emit('jetson_status', {'online': True})
                            print("[PC] Liaison Jetson détectée.")

                        # Ignorer si c'est un heartbeat pur
                        if data.get("type") == "heartbeat":
                            #status = data.get("status", "online")
                            # On envoie le statut précis au navigateur
                            #socketio.emit('jetson_status', {'online': True, 'status': status})
                            socketio.emit('jetson_status', data)
                            continue 
                        
                        # Traitement des alertes entrantes
                        alerts = data.get("alerts", [])
                        for alert in alerts:
                            timestamp = int(time.time())
                            filename_base = f"alerte_{alert['cl']}_{alert['id']}_{timestamp}"
                            
                            # 1. Sauvegarde Image
                            img_data = base64.b64decode(alert["img"])
                            img_path = os.path.join(STORAGE_DIR, f"{filename_base}.jpg")
                            with open(img_path, "wb") as f:
                                f.write(img_data)

                            # 2. Sauvegarde Métadonnées
                            meta = {
                                "id": alert["id"],
                                "classe": alert["cl"],
                                "distance": alert["d"],
                                "timestamp": timestamp,
                                "fps_jetson": data.get("f")
                            }
                            with open(os.path.join(STORAGE_DIR, f"{filename_base}.json"), "w") as f:
                                json.dump(meta, f, indent=4)

                            # 3. Notification Interface
                            socketio.emit('new_alert', {
                                'id': alert['id'],
                                'label': f"{alert['cl']} ({alert['d']}m)",
                                'img': alert['img'],
                                'file': filename_base
                            })

                            # 4. Envoi de l'accusé de réception (ACK) vers la Jetson
                            ack = json.dumps({"type": "ack", "id": alert['id']}) + "\n"
                            esp_socket.sendall(ack.encode('utf-8'))

                    except json.JSONDecodeError:
                        pass
                        
        except Exception as e:
            print(f"[PC] Erreur de liaison : {e}")
            socketio.emit('esp_status', {'connected': False})
            socketio.emit('jetson_status', {'online': False})
            jetson_online = False
            if esp_socket:
                esp_socket.close()
                esp_socket = None
            eventlet.sleep(3)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/quit', methods=['POST'])
def quit_app():
    os._exit(0)

@socketio.on('connect')
def handle_connect():
    global jetson_online, esp_socket
    # Dès qu'un navigateur se connecte, on lui envoie l'état actuel
    socketio.emit('esp_status', {'connected': esp_socket is not None})
    socketio.emit('jetson_status', {'online': jetson_online, 'status': 'active' if jetson_online else 'standby'})

@app.route('/remote_cmd/<command>', methods=['POST'])
def remote_cmd(command):
    """Envoie une commande START ou STOP à la Jetson via l'ESP32."""
    if esp_socket:
        try:
            msg = json.dumps({"cmd": command.upper()}) + "\n"
            esp_socket.sendall(msg.encode())
            return {"status": "ok", "cmd": command}
        except:
            return {"status": "error", "message": "Échec envoi"}, 500
    return {"status": "error", "message": "ESP32 hors-ligne"}, 400

if __name__ == '__main__':
    socketio.start_background_task(listen_to_esp)
    # Ouverture du navigateur après 1 seconde
    eventlet.spawn_after(1, lambda: webbrowser.open("http://127.0.0.1:5000"))
    socketio.run(app, host='0.0.0.0', port=5000)