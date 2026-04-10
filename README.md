# 📡 Système de Surveillance ESP32 + Jetson (Flask + Socket.IO)

Ce projet permet de créer une interface web temps réel pour surveiller et contrôler une **Jetson** connectée via un **ESP32**, avec transmission d’alertes (images + métadonnées).

---

## 🚀 Fonctionnalités

* 🔌 Connexion TCP avec un ESP32
* 📡 Communication bidirectionnelle ESP32 ↔ PC ↔ Jetson
* 🧠 Détection d’activité de la Jetson (heartbeat + timeout)
* 🖼️ Réception et sauvegarde d’images encodées en base64
* 📁 Stockage des alertes (image + JSON)
* 🌐 Interface web temps réel via Flask + Socket.IO
* 📢 Notifications instantanées des alertes
* 🎮 Commandes distantes (START / STOP)
* 🔄 Reconnexion automatique en cas de perte de liaison

---

## 🏗️ Architecture

```
Jetson Nano
    ↓ (JSON + image base64)
ESP32 (WiFi / TCP)
    ↓
PC (Flask + Socket.IO)
    ↓
Navigateur Web (interface temps réel)
```

---

## 📦 Installation

### 1. Cloner le projet

```bash
git clone <repo_url>
cd <repo>
```

### 2. Installer les dépendances

```bash
pip install flask flask-socketio eventlet
```

---

## ⚙️ Configuration

Modifier les paramètres dans le script :

```python
ESP32_IP = '192.168.4.1'
PORT = 3333
STORAGE_DIR = "captures"
```

---

## ▶️ Lancement

```bash
python app.py
```

➡️ Le navigateur s’ouvre automatiquement sur :

```
http://127.0.0.1:5000
```

---

## 📁 Structure des données

Les alertes sont sauvegardées dans le dossier :

```
captures/
```

### Exemple :

```
alerte_person_12_1710000000.jpg
alerte_person_12_1710000000.json
```

### Contenu JSON :

```json
{
    "id": 12,
    "classe": "person",
    "distance": 3.5,
    "timestamp": 1710000000,
    "fps_jetson": 15
}
```

---

## 🔄 Communication

### 📥 Données reçues (ESP32 → PC)

Format JSON (ligne par ligne) :

```json
{
  "type": "alert",
  "alerts": [
    {
      "id": 1,
      "cl": "person",
      "d": 2.3,
      "img": "<base64>"
    }
  ],
  "f": 20
}
```

### 💓 Heartbeat

```json
{
  "type": "heartbeat",
  "status": "active"
}
```

---

### 📤 Commandes envoyées (PC → Jetson via ESP32)

```json
{"cmd": "START"}
{"cmd": "STOP"}
```

---

### ✅ ACK envoyé

```json
{"type": "ack", "id": 1}
```

---

## 🌐 API HTTP

### Accueil

```
GET /
```

→ Interface web

---

### Quitter l’application

```
POST /quit
```

---

### Commandes distantes

```
POST /remote_cmd/<command>
```

Exemple :

```bash
curl -X POST http://localhost:5000/remote_cmd/start
```

---

## ⚡ WebSocket Events

### Émis vers le client

* `esp_status` → état de connexion ESP32
* `jetson_status` → état Jetson (online/offline + status)
* `new_alert` → nouvelle alerte reçue

---

## 🧠 Gestion des états

* **Jetson online** : si heartbeat reçu
* **Timeout** : 5 secondes sans message → offline
* **ESP32 offline** : reconnexion automatique toutes les 3 secondes

---

## 🛠️ Technologies utilisées

* Flask
* Flask-SocketIO
* Eventlet
* TCP sockets
* JSON
* Base64

---

## ⚠️ Remarques importantes

* Le serveur utilise `eventlet` → compatible avec Socket.IO async
* Le buffer TCP gère les messages fragmentés
* Les images sont décodées côté serveur
* Chaque alerte est confirmée par un ACK

---

## 💡 Améliorations possibles

* 🔐 Authentification utilisateur
* 📊 Dashboard avancé (stats, historique)
* ☁️ Upload vers cloud (AWS / GCP)
* 🧠 Ajout de nouvelles classes d’objets
* 📱 Interface mobile optimisée

---

## 👨‍💻 Auteur

Projet IoT temps réel combinant vision embarquée et interface web.
