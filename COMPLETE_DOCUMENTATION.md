# COMPLETE_DOCUMENTATION.md

# 🚀 Kafka Dynamic Content Streaming System - COMPLETE GUIDE

---

## PROJECT OVERVIEW

**A distributed real-time event streaming system using Apache Kafka, SQLite, and Flask.**

### What It Does
- **Admin Dashboard** (`app.py`): Web UI to create topics, approve/manage workflows, view live stats
- **Producer** (`producer.py`): Auto-generates realistic data and publishes to Kafka topics
- **Consumer** (`consumer.py`): Interactive CLI to subscribe to topics and receive messages in real-time
- **Broker**: Kafka message queue + SQLite metadata database

### Key Features
✅ Dynamic topic creation & approval  
✅ Multi-user subscriptions  
✅ Type-specific data generation (sensor, payment, weather, logs, user activity)  
✅ Beautiful web dashboard with live stats  
✅ Interactive consumer CLI menu  
✅ Cross-machine deployment support  
✅ Full REST API  
✅ Complete logging & auditing  

---

## QUICK START (5 MINUTES)

### Prerequisites
- Python 3.7+
- 4 machines/laptops (or 1 for testing)
- Apache Kafka 2.8+

### Step 1: Install Dependencies (All Machines)
```bash
pip install kafka-python Flask Flask-Cors requests
```

### Step 2: Start Kafka (Broker Machine: 10.214.203.73)
```bash
# Download Kafka
wget https://archive.apache.org/dist/kafka/3.0.0/kafka_2.13-3.0.0.tgz
tar -xzf kafka_2.13-3.0.0.tgz
cd kafka_2.13-3.0.0

# Edit config/server.properties
nano config/server.properties
# Set:
# listeners=PLAINTEXT://0.0.0.0:9092
# advertised.listeners=PLAINTEXT://10.214.203.73:9092
# auto.create.topics.enable=false

# Start Zookeeper & Kafka
bin/zookeeper-server-start.sh config/zookeeper.properties &
bin/kafka-server-start.sh config/server.properties &
```

### Step 3: Run Admin Dashboard (Admin Machine: 10.214.203.13)
```bash
python app.py
# Open browser: http://10.214.203.13:5000
```

### Step 4: Run Producer (Producer Machine)
```bash
export PRODUCER_SECRET="ChangeThisProducerSecret!"
python producer.py
```

### Step 5: Run Consumer (Consumer Machine)
```bash
python consumer.py
# Follow CLI menu to subscribe & view messages
```

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────┐
│  BROKER MACHINE (10.214.203.73)                │
│  ┌──────────────────────────────────────────┐  │
│  │ Apache Kafka (Port 9092)                 │  │
│  │ Zookeeper (Port 2181)                    │  │
│  │ SQLite Database: kafka_system.db         │  │
│  └──────────────────────────────────────────┘  │
└────────┬─────────────────┬──────────────┬────┘
         │                 │              │
    ┌────▼────┐    ┌───────▼────┐  ┌────▼─────┐
    │ ADMIN    │    │ PRODUCER   │  │ CONSUMER │
    │ MACHINE  │    │ MACHINE    │  │ MACHINE  │
    │ (10.214. │    │            │  │          │
    │ 203.13)  │    │            │  │          │
    │          │    │            │  │          │
    │ app.py   │    │ producer.  │  │ consumer │
    │ :5000    │    │ py         │  │ .py      │
    │          │    │            │  │          │
    │ Dashboard│    │ Publishes  │  │ Subscribes
    │ + API    │    │ data       │  │ & reads  │
    └──────────┘    └────────────┘  └──────────┘
```

---

## DETAILED SETUP

### BROKER MACHINE SETUP (10.214.203.73)

#### 1. Install Java (if not present)
```bash
sudo apt update
sudo apt install openjdk-11-jdk -y
java -version
```

#### 2. Download & Extract Kafka
```bash
cd /opt
wget https://archive.apache.org/dist/kafka/3.0.0/kafka_2.13-3.0.0.tgz
tar -xzf kafka_2.13-3.0.0.tgz
cd kafka_2.13-3.0.0
```

#### 3. Configure Kafka
```bash
nano config/server.properties
```
Change/add:
```
broker.id=1
listeners=PLAINTEXT://0.0.0.0:9092
advertised.listeners=PLAINTEXT://10.214.203.73:9092
log.dirs=/tmp/kafka-logs
auto.create.topics.enable=false
num.partitions=3
default.replication.factor=1
```

#### 4. Start Services
```bash
# Terminal 1 - Zookeeper
bin/zookeeper-server-start.sh config/zookeeper.properties

# Terminal 2 - Kafka Broker
bin/kafka-server-start.sh config/server.properties
```

#### 5. Verify
```bash
netstat -tuln | grep 9092
# Should show: LISTEN 0.0.0.0:9092
```

---

### ADMIN MACHINE SETUP (10.214.203.13)

#### 1. Create Project Directory
```bash
mkdir -p kafka-streaming-project
cd kafka-streaming-project
```

#### 2. Create requirements.txt
```bash
cat > requirements.txt << 'EOF'
kafka-python==2.0.2
Flask==3.0.0
Flask-Cors==4.0.0
requests==2.31.0
Werkzeug==3.0.0
EOF
```

#### 3. Create templates directory
```bash
mkdir -p templates
```

#### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 5. Copy app.py, producer.py, consumer.py, dashboard.html (from provided code)

#### 6. Update IPs in Files
In **app.py** last line:
```python
app.run(host='10.214.203.13', port=5000)
```

In **producer.py** top section:
```python
BOOTSTRAP_SERVERS = ['10.214.203.73:9092']
ADMIN_API_URL = 'http://10.214.203.13:5000'
```

In **consumer.py** top section:
```python
BOOTSTRAP_SERVERS = ['10.214.203.73:9092']
ADMIN_API_URL = 'http://10.214.203.13:5000'
```

#### 7. Run Admin
```bash
python app.py
# Open: http://10.214.203.13:5000
```

---

### PRODUCER MACHINE SETUP

```bash
pip install -r requirements.txt
export PRODUCER_SECRET="ChangeThisProducerSecret!"
python producer.py
```

---

### CONSUMER MACHINE SETUP

```bash
pip install -r requirements.txt
python consumer.py
```

---

## COMPLETE WORKFLOW

### Timeline of Events

**T=0m: Admin Creates Topic**
```
Dashboard → Click "Create Topic" tab
→ Fill: Name="sensor_data", Created By="Admin01"
→ Click "Create Topic Request"
→ Status: PENDING
```

**T=1m: Admin Approves Topic**
```
Dashboard → Topics table
→ Click "Approve" button next to sensor_data
→ Status: APPROVED
```

**T=5m: Producer Discovers & Activates**
```
Producer's Topic Watcher thread polls /api/topics
→ Finds "sensor_data" with status APPROVED
→ Creates topic in Kafka
→ Calls POST /api/topics/activate_by_name
→ Status: ACTIVE
```

**T=6m: Producer Publishes Data**
```
Producer's Data Generator thread:
→ Selects random active topic (e.g., sensor_data)
→ Detects type from topic name
→ Generates: {sensor_id: "42", temperature: 25.3, humidity: 65}
→ Publishes to Kafka

Producer's Publisher thread:
→ Pulls from queue
→ Sends to Kafka broker
→ Logs: "✅ Published to sensor_data"

(Repeats every 0.5-1.5 seconds)
```

**T=10m: Consumer Subscribes**
```
Consumer → CLI Menu
→ Option 1: "View Available Topics"
   → Displays: sensor_data, user_events, etc.
→ Option 3: "Subscribe to Topic"
   → Enter: sensor_data
   → Kafka Consumer subscribes
   → Logs: "✅ Subscribed to sensor_data"
```

**T=11m: Consumer Receives Messages**
```
Consumer → Option 5: "Start Consumer"
→ Polls Kafka every 1 second
→ Displays:
   📨 Topic: sensor_data
   📦 Data Type: sensor
   🕒 Timestamp: 2024-11-09T23:15:00
   🧩 Payload: {sensor_id: "42", temperature: 25.3, ...}

(Repeats continuously for each message)
```

**Continuous: Admin Monitors Stats**
```
Dashboard auto-refreshes every 10 seconds
Stat cards update:
- Total Topics: 3
- Pending: 0
- Active: 3
- Subscriptions: 5
```

---

## API REFERENCE

### Base URL: `http://10.214.203.13:5000`

### Health Check
```
GET /api/health
Response: {"status": "healthy", "timestamp": "..."}
```

### Topics API

**List All Topics**
```
GET /api/topics
Response: [
  {
    "topic_id": 1,
    "topic_name": "sensor_data",
    "status": "active",
    "partitions": 3,
    "created_by": "admin",
    "created_at": "2024-11-09T10:00:00"
  }
]
```

**Create Topic Request**
```
POST /api/topics
Content-Type: application/json
{
  "name": "sensor_data",
  "created_by": "admin",
  "partitions": 3,
  "replication_factor": 1,
  "description": "IoT sensors"
}
Response: {"message": "Topic creation request submitted", "topic_id": 1}
```

**Approve Topic**
```
POST /api/topics/<topic_id>/approve
Response: {"message": "Topic approved successfully"}
```

**Producer Activates Topic**
```
POST /api/topics/activate_by_name
X-Producer-Key: ChangeThisProducerSecret!
Content-Type: application/json
{
  "topic_name": "sensor_data"
}
Response: {"message": "Topic activated"}
```

**List Active Topics Only**
```
GET /api/topics/active
Response: [
  {
    "topic_name": "sensor_data",
    "description": "IoT sensors",
    "activated_at": "2024-11-09T10:06:00"
  }
]
```

**Deactivate Topic**
```
POST /api/topics/<topic_id>/deactivate
Response: {"message": "Topic deactivated successfully"}
```

### Subscriptions API

**List Subscriptions**
```
GET /api/subscriptions
Optional: ?user_id=user_1

Response: [
  {
    "subscription_id": 1,
    "user_id": "user_1",
    "topic_name": "sensor_data",
    "subscribed_at": "2024-11-09T15:30:00",
    "status": "active"
  }
]
```

**Subscribe User**
```
POST /api/subscriptions
Content-Type: application/json
{
  "user_id": "user_1",
  "topic_name": "sensor_data"
}
Response: {"message": "Subscription added successfully"}
```

**Unsubscribe User**
```
DELETE /api/subscriptions
Content-Type: application/json
{
  "user_id": "user_1",
  "topic_name": "sensor_data"
}
Response: {"message": "Subscription removed successfully"}
```

**Get Statistics**
```
GET /api/stats
Response: {
  "total_topics": 5,
  "pending_topics": 1,
  "active_topics": 4,
  "total_subscriptions": 12,
  "timestamp": "2024-11-09T23:15:00"
}
```

---

## TROUBLESHOOTING

### Issue: "Can't connect to Kafka broker"

**Solution:**
```bash
# Check Kafka is running
ps aux | grep kafka

# Check port 9092 is open
netstat -tuln | grep 9092

# Verify advertised.listeners in server.properties
grep advertised.listeners /opt/kafka_2.13-3.0.0/config/server.properties
# Should show: PLAINTEXT://10.214.203.73:9092

# Restart Kafka
pkill -f kafka
bin/kafka-server-start.sh config/server.properties &
```

### Issue: "Producer can't reach Admin API"

**Solution:**
```bash
# Check Admin is running
curl http://10.214.203.13:5000/api/health
# Should return: {"status": "healthy", ...}

# Verify IP and port in producer.py
grep ADMIN_API_URL producer.py
# Should show: ADMIN_API_URL = 'http://10.214.203.13:5000'

# Test network connectivity
ping 10.214.203.13
```

### Issue: "Consumer sees no messages"

**Solution:**
```bash
# 1. Check topic is ACTIVE (not PENDING)
curl http://10.214.203.13:5000/api/topics

# 2. Wait 5-10 seconds for Producer to activate it

# 3. Verify subscription was created
curl "http://10.214.203.13:5000/api/subscriptions?user_id=user_1"

# 4. Check Kafka has messages using kafka-console-consumer
bin/kafka-console-consumer.sh --bootstrap-server 10.214.203.73:9092 \
  --topic sensor_data --from-beginning --max-messages 5
```

### Issue: "Dashboard stats not updating"

**Solution:**
```bash
# Check SQLite database
sqlite3 kafka_system.db
> SELECT COUNT(*) FROM topics;
> SELECT * FROM user_subscriptions;

# Restart app.py
pkill -f "python app.py"
python app.py
```

---

## FILE STRUCTURE

```
kafka-streaming-project/
├── README.md                      (project overview)
├── COMPLETE_DOCUMENTATION.md      (this file)
├── requirements.txt               (pip packages)
├── app.py                         (Flask admin API + dashboard)
├── producer.py                    (data generator)
├── consumer.py                    (CLI consumer)
├── templates/
│   └── dashboard.html             (web UI)
├── kafka_system.db                (SQLite, auto-created)
├── producer.log                   (producer debug log)
└── evidence/
    ├── dashboard.png              (screenshot)
    ├── producer.png               (screenshot)
    └── consumer.png               (screenshot)
```

---

## KEY COMMANDS

### Kafka Commands (on Broker)
```bash
# List topics
bin/kafka-topics.sh --list --bootstrap-server 10.214.203.73:9092

# Describe topic
bin/kafka-topics.sh --describe --topic sensor_data --bootstrap-server 10.214.203.73:9092

# Delete topic
bin/kafka-topics.sh --delete --topic sensor_data --bootstrap-server 10.214.203.73:9092

# Monitor broker
bin/kafka-broker-api-versions.sh --bootstrap-server 10.214.203.73:9092
```

### SQLite Commands (on Admin/Broker)
```bash
sqlite3 kafka_system.db

# List all topics
SELECT * FROM topics;

# List all subscriptions
SELECT * FROM user_subscriptions;

# Count by status
SELECT status, COUNT(*) FROM topics GROUP BY status;

# Exit
.quit
```

### Process Commands (All Machines)
```bash
# Check if running
ps aux | grep python
ps aux | grep kafka

# Kill process
pkill -f "python app.py"
pkill -f "python producer.py"
pkill -f kafka

# View logs
tail -f producer.log
tail -f /var/log/syslog | grep kafka
```

---

## NEXT STEPS

1. **Testing Phase**
   - Create 3 topics in dashboard
   - Approve all 3
   - Watch Producer activate them automatically
   - Subscribe Consumer to 2 topics
   - Verify messages flowing in Consumer CLI

2. **Take Evidence Screenshots**
   - Dashboard with stats cards populated
   - Producer daemon logs showing published messages
   - Consumer CLI showing received messages
   - Kafka topic list output

3. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Kafka streaming project with complete docs"
   git branch -M main
   git remote add origin https://github.com/your-username/repo.git
   git push -u origin main
   ```

4. **Production Enhancements** (Optional)
   - Add authentication to dashboard
   - Use PostgreSQL instead of SQLite
   - Add monitoring (Prometheus/Grafana)
   - Enable Kafka replication
   - Add message persistence database
   - Deploy to Docker

---


## 👥 Team & Credits

**Project:** Kafka Dynamic Content Streaming System 
**Created:** 9th November 2025

---
