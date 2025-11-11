# 🚀 Kafka Dynamic Content Streaming System

> **A real-time distributed event streaming platform using Apache Kafka, SQLite, and Flask. Enables teams to dynamically create topics, approve workflows, and stream/consume messages across multiple machines.**

---

## 🎯 Overview

This project implements a **distributed event streaming system** where:
- **Admin/Dashboard** (`app.py`): Flask web interface for topic management, approval workflow, subscription tracking.
- **Producer** (`producer.py`): Auto-generates realistic, type-specific events and publishes to approved/active Kafka topics.
- **Consumer** (`consumer.py`): Interactive CLI tool to subscribe to topics, receive messages in real-time, view statistics.
- **Broker** (Apache Kafka + SQLite): Central message queue + metadata store.

**Use cases:** Real-time analytics, event sourcing, IoT sensor streaming, user activity tracking, payment processing pipelines.

---

## ✨ Features

- ✅ **Dynamic Topic Management**: Create topics, submit for approval, auto-activate.
- ✅ **Multi-User Subscriptions**: Users independently subscribe/unsubscribe from topics.
- ✅ **Type-Specific Data Generation**: Sensor, weather, payment, logs, user activity samples.
- ✅ **Beautiful Dashboard**: React-inspired HTML5 UI with live statistics.
- ✅ **Interactive Consumer CLI**: Menu-driven subscription and message consumption.
- ✅ **RESTful API**: Fully documented endpoints for all operations.
- ✅ **Cross-Machine Deployment**: Kafka on one host, Admin/Producer/Consumer on separate laptops.
- ✅ **Logging & Auditing**: All operations logged for debugging and compliance.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BROKER MACHINE                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Kafka Broker (10.214.203.73:9092)                  │  │
│  │  Topics: user_events, sensor_data, payments, etc.  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  SQLite Database (kafka_system.db)                  │  │
│  │  Tables: topics, user_subscriptions                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
           ↑                          ↑                   ↑
           │                          │                   │
    ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
    │ ADMIN MACHINE    │  │ PRODUCER MACHINE │  │ CONSUMER MACHINE │
    │ (10.214.203.13)  │  │  (10.214.203.73) │  │  (10.214.203.73) │
    │                  │  │                  │  │                  │
    │  app.py          │  │  producer.py     │  │  consumer.py     │
    │  :5000 (HTTP)    │  │  (Daemon)        │  │  (CLI Menu)      │
    │                  │  │  Publishes data  │  │  Subscribes &    │
    │  Dashboard       │  │  to topics       │  │  receives msgs   │
    │  Topic approval  │  │  Requests API    │  │  User: user_1    │
    │  Stats & UI      │  │  activation      │  │                  │
    └──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 📦 Prerequisites

- **Python 3.7+**
- **Apache Kafka 2.8+** (broker machine)
- **pip packages**: `kafka-python`, `Flask`, `Flask-Cors`, `requests`
- **Minimum 4 machines** (or 1 for testing):
  - Broker: Kafka + SQLite
  - Admin: Flask app (app.py)
  - Producer: Data generator (producer.py)
  - Consumer: Message reader (consumer.py)

---

## 🔧 Installation

### 1. Clone/Setup Repository

```bash
git clone <your-repo-url>
cd kafka-streaming-project
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Kafka Broker (on broker machine)

```bash
# Download Kafka
wget https://archive.apache.org/dist/kafka/3.0.0/kafka_2.13-3.0.0.tgz
tar -xzf kafka_2.13-3.0.0.tgz
cd kafka_2.13-3.0.0

# Edit config/server.properties
nano config/server.properties

# Set these values:
# listeners=PLAINTEXT://0.0.0.0:9092
# advertised.listeners=PLAINTEXT://10.214.203.73:9092  (your broker IP)
# auto.create.topics.enable=false

# Start Zookeeper & Kafka
bin/zookeeper-server-start.sh config/zookeeper.properties &
bin/kafka-server-start.sh config/server.properties &
```

### 4. Create Database (broker machine)

```bash
cd /path/to/project
python -c "from app import db_service; db_service.init_db()"
```

---

## 🚀 Quick Start

### Machine 1: Broker
```bash
# Ensure Kafka & SQLite are running (see Installation above)
```

### Machine 2: Admin Dashboard
```bash
python app.py
# Open browser: http://10.214.203.13:5000
```

### Machine 3: Producer
```bash
export PRODUCER_SECRET="ChangeThisProducerSecret!"
python producer.py
```

### Machine 4: Consumer
```bash
python consumer.py
# Follow CLI menu to subscribe to topics and view messages
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Producer secret key (for authentication to activate topics)
export PRODUCER_SECRET="YourSecureSecret123!"

# Kafka broker address
BOOTSTRAP_SERVERS = ['10.214.203.73:9092']

# Admin API URL
ADMIN_API_URL = 'http://10.214.203.13:5000'

# Dashboard IP & Port
# In app.py: app.run(host='10.214.203.13', port=5000)
```

### Database Configuration

**SQLite location:** `kafka_system.db` (same directory as `app.py`)

**Tables:**
- `topics`: Topic metadata, approval status, partitions.
- `user_subscriptions`: User-topic relationships.

---

## 📡 API Documentation

### Health Check
```http
GET /api/health
Response: { "status": "healthy", "timestamp": "2024-11-09T..." }
```

### Topics API

**List all topics**
```http
GET /api/topics
Response: [{ "topic_id": 1, "topic_name": "user_events", "status": "active", ... }, ...]
```

**Create topic request**
```http
POST /api/topics
Content-Type: application/json
{
  "name": "user_events",
  "created_by": "admin",
  "partitions": 3,
  "replication_factor": 1,
  "description": "User activity events"
}
Response: { "message": "Topic creation request submitted", "topic_id": 1 }
```

**Approve topic**
```http
POST /api/topics/<topic_id>/approve
Response: { "message": "Topic approved successfully" }
```

**Activate topic (called by producer)**
```http
POST /api/topics/activate_by_name
X-Producer-Key: <PRODUCER_SECRET>
Content-Type: application/json
{ "topic_name": "user_events" }
Response: { "message": "Topic activated" }
```

**Get active topics only**
```http
GET /api/topics/active
Response: [{ "topic_name": "user_events", "activated_at": "2024-11-09T..." }, ...]
```

### Subscriptions API

**List all subscriptions**
```http
GET /api/subscriptions
Response: [{ "user_id": "user_1", "topic_name": "user_events", "status": "active", ... }, ...]
```

**Add subscription**
```http
POST /api/subscriptions
Content-Type: application/json
{ "user_id": "user_1", "topic_name": "user_events" }
Response: { "message": "Subscription added successfully" }
```

**Remove subscription**
```http
DELETE /api/subscriptions
Content-Type: application/json
{ "user_id": "user_1", "topic_name": "user_events" }
Response: { "message": "Subscription removed successfully" }
```

### Statistics API

```http
GET /api/stats
Response: {
  "total_topics": 3,
  "pending_topics": 1,
  "active_topics": 2,
  "total_subscriptions": 5,
  "timestamp": "2024-11-09T..."
}
```

---

## 🐛 Troubleshooting

### Kafka Connection Refused
```bash
# Check Kafka is listening
sudo ss -tulpen | grep 9092

# Verify advertised.listeners in server.properties
grep advertised.listeners /path/to/kafka/config/server.properties

# Ensure firewall allows 9092
sudo ufw allow 9092/tcp
```

### API Unreachable (Producer/Consumer can't reach Admin)
```bash
# Check Admin is running
curl http://10.214.203.13:5000/api/health

# Verify IP configuration in producer.py & consumer.py
# Test network connectivity
ping 10.214.203.13
```

### Producer Won't Activate Topics
```bash
# Check Producer Secret matches
echo $PRODUCER_SECRET
# Compare with app.py PRODUCER_SECRET

# Check Admin API logs for 401 Unauthorized errors
```

### Consumer Not Receiving Messages
```bash
# Verify subscription was created
curl "http://10.214.203.13:5000/api/subscriptions?user_id=user_1"

# Ensure topic is ACTIVE (not pending)
curl http://10.214.203.13:5000/api/topics/active

# Check Kafka broker has messages
# (kafka-console-consumer can verify)
```


---

## 👥Credits

**Project:** Kafka Dynamic Content Streaming System   
**Created:** 9th November 2025

---

