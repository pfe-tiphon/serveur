import eventlet
eventlet.monkey_patch()

import webbrowser
import threading

import socket
import time
import base64
import json
import os
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Configuration
ESP32_IP = '192.168.4.1'
PORT = 3333
STORAGE_DIR = "captures"

if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

def listen_to_esp():
    """Gère la réception, le stockage et la notification."""
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(None) # Mode bloquant (plus robuste pour l'ESP32)
            
            print(f"[PC] Tentative de connexion à l'ESP32 ({ESP32_IP})...")
            s.connect((ESP32_IP, PORT))
            
            print("[PC] Connecté à l'ESP32 !")
            socketio.emit('esp_status', {'connected': True})

            buffer = ""
            while True:
                chunk = s.recv(16384).decode(errors='ignore')
                if not chunk: break
                buffer += chunk

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line: continue

                    try:
                        data = json.loads(line)
                        alerts = data.get("alerts", [])
                        for alert in alerts:
                            timestamp = int(time.time())
                            filename_base = f"alerte_{alert['cl']}_{alert['id']}_{timestamp}"
                            
                            # 1. Sauvegarde Image
                            img_data = base64.b64decode(alert["img"])
                            img_path = os.path.join(STORAGE_DIR, f"{filename_base}.jpg")
                            with open(img_path, "wb") as f:
                                f.write(img_data)

                            # 2. Sauvegarde JSON (Métadonnées)
                            meta = {
                                "id": alert["id"],
                                "classe": alert["cl"],
                                "distance": alert["d"],
                                "timestamp": timestamp,
                                "fps_jetson": data.get("f")
                            }
                            with open(os.path.join(STORAGE_DIR, f"{filename_base}.json"), "w") as f:
                                json.dump(meta, f, indent=4)

                            # 3. Envoi au navigateur
                            socketio.emit('new_alert', {
                                'id': alert['id'],
                                'label': f"{alert['cl']} ({alert['d']}m)",
                                'img': alert['img'],
                                'file': filename_base
                            })

                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"[PC] Erreur de liaison : {e}")
            socketio.emit('esp_status', {'connected': False})
            if s:
                s.close()
            eventlet.sleep(3) # Attendre 3s avant de retenter

def open_browser():
    """Ouvre le navigateur après un court délai pour laisser Flask démarrer."""
    webbrowser.open("http://127.0.0.1:5000")

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/quit', methods=['POST'])
def quit_app():
    os._exit(0)

if __name__ == '__main__':
    socketio.start_background_task(listen_to_esp)
    threading.Timer(1.5, open_browser).start()
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False)