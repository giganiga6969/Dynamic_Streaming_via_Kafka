# 📋 WORKFLOW.md

## Project Workflow: Kafka Dynamic Streaming System

### End-to-End Flow

```
1. ADMIN CREATES TOPIC
   └─> Dashboard: Fill form → "Create Topic Request"
   └─> Status: PENDING
   
2. ADMIN APPROVES TOPIC
   └─> Dashboard: Click "Approve" button
   └─> Status: APPROVED
   
3. PRODUCER POLLS FOR APPROVED TOPICS
   └─> Every 5 seconds: Fetch /api/topics with status in ['approved', 'active']
   └─> For each approved topic not yet created in Kafka:
       ├─> Create topic in Kafka (3 partitions, 1 replica)
       ├─> POST /api/topics/activate_by_name (with X-Producer-Key header)
       └─> Status: ACTIVE
   
4. PRODUCER GENERATES & PUBLISHES DATA
   └─> Type-specific message generation (sensor, weather, payment, etc.)
   └─> Kafka send(topic, value={payload, timestamp, data_type})
   └─> Log: "✅ Published to {topic}"
   
5. CONSUMER SUBSCRIBES TO TOPIC
   └─> CLI Menu: "Subscribe to Topic"
   └─> Enter topic name (e.g., "user_events")
   └─> POST /api/subscriptions {user_id: "user_1", topic_name: "user_events"}
   └─> Kafka Consumer.subscribe(["user_events"])
   
6. CONSUMER RECEIVES & DISPLAYS MESSAGES
   └─> Poll Kafka every 1 second
   └─> For each message:
       ├─> Parse JSON {topic, data_type, payload, timestamp}
       ├─> Print formatted: "📨 Topic: ..., 📦 Data: ..., 🧩 Payload: ..."
       └─> Log to SQLite (future: message store)
   
7. ADMIN MONITORS LIVE STATS
   └─> Dashboard auto-refreshes every 10 seconds
   └─> Cards show: Total Topics, Pending, Active, Subscriptions
   
8. CONSUMER UNSUB SCRIBES (Optional)
   └─> CLI Menu: "Unsubscribe from Topic"
   └─> DELETE /api/subscriptions
   └─> Kafka Consumer stops polling that topic
```

---

## User Journeys

### Journey 1: Admin Creates & Approves Topics

**Time: T=0m**

1. Admin opens browser → `http://10.214.203.13:5000`
2. Clicks **"Create Topic"** tab
3. Fills form:
   - Topic Name: `sensor_data`
   - Created By: `Admin01`
   - Partitions: `3`
   - Replication: `1`
   - Description: `Temperature and humidity sensors`
4. Clicks **"Create Topic Request"** button
5. Alert: "✅ Topic creation request submitted"
6. Topic appears in "Topics Management" table with status **PENDING**

**Time: T=1m**

7. Clicks **"Approve"** button next to `sensor_data`
8. Alert: "✅ Topic approved successfully"
9. Status changes to **APPROVED**

**Time: T=5m (Producer polling)**

10. Producer's Topic Watcher thread sees `sensor_data` in "approved" status
11. Creates topic in Kafka (if not exists)
12. Calls POST `/api/topics/activate_by_name` with header `X-Producer-Key: <SECRET>`
13. Status changes to **ACTIVE** in dashboard
14. Producer logs: `📌 Topic 'sensor_data' created in Kafka`

---

### Journey 2: Producer Publishes Data

**Continuous (every 0.5-1.5 seconds)**

1. Producer's **Data Generator Thread** runs:
   - Fetches active topics: `GET /api/topics/active`
   - Randomly picks topic (e.g., `sensor_data`)
   - Detects type from topic name → "sensor"
   - Generates: `{sensor_id: "sensor_42", temperature: 25.3, humidity: 65, ...}`

2. Producer's **Publisher Thread** pulls from queue:
   - Sends to Kafka: `producer.send("sensor_data", value=JSON_MESSAGE)`
   - Flushes & waits for ACK
   - Logs: `✅ Published to sensor_data: sensor`

3. Kafka stores message in partitions

---

### Journey 3: Consumer Subscribes & Receives

**Time: T=10m**

1. User runs `python consumer.py`
2. CLI Menu appears:
   ```
   🎛️ KAFKA CONSUMER MENU
   1. View Available Topics
   2. View My Subscriptions
   3. Subscribe to Topic
   ...
   ```

3. Selects **Option 1**: "View Available Topics"
   - Fetches: `GET /api/topics/active`
   - Displays: `sensor_data`, `user_events`, etc.

4. Selects **Option 3**: "Subscribe to Topic"
   - Prompted: "Enter topic to subscribe: `sensor_data`"
   - Calls: `POST /api/subscriptions {user_id: "user_1", topic_name: "sensor_data"}`
   - Consumer subscribes: `kafka_consumer.subscribe(["sensor_data"])`
   - Logs: `✅ Subscribed to sensor_data`

5. Selects **Option 5**: "Start Consumer"
   - Consumer enters polling loop
   - Every 1 second: `kafka_consumer.poll(timeout_ms=1000)`
   - Messages arrive in real-time!

   **Output:**
   ```
   📨 Topic: sensor_data
   📦 Data Type: sensor
   🕒 Timestamp: 2024-11-09T23:15:00.123
   🧩 Payload:
   {
     "sensor_id": "sensor_42",
     "temperature": 25.3,
     "humidity": 65,
     "pressure": 1013.25
   }
   ```

6. Selects **Option 7**: "Show Statistics"
   - Displays:
     ```
     📊 CONSUMER STATS
     Running: Yes ✅
     Messages Processed: 42
     ```

---

### Journey 4: Admin Monitors Real-Time Stats

**Continuous background**

1. Dashboard auto-fetches `GET /api/stats` every 10 seconds
2. Stats cards update:
   - **Total Topics**: 3 (sensor_data, user_events, payments)
   - **Pending Approval**: 0
   - **Active Topics**: 3
   - **Total Subscriptions**: 5 (user_1, user_2, user_3, etc.)

3. Tables auto-refresh:
   - **Topics table**: Shows all topics with action buttons
   - **Subscriptions table**: Shows all user-topic pairs

---

## Data Flow Diagram

```
Dashboard (Admin UI)
       │
       ├─ POST /api/topics (create topic request)
       │    └─> SQLite: INSERT into topics (status='pending')
       │
       ├─ POST /api/topics/<id>/approve
       │    └─> SQLite: UPDATE topics SET status='approved'
       │
       └─ GET /api/stats (auto every 10s)
            └─> Refresh stat cards

Producer (Daemon)
       │
       ├─ GET /api/topics (filter by status in ['approved', 'active'])
       │    └─> Identify new approved topics
       │
       ├─ CREATE topic in Kafka (if needed)
       │    └─ bin/kafka-topics.sh --create --topic ABC --partitions 3
       │
       ├─ POST /api/topics/activate_by_name (with X-Producer-Key)
       │    └─> SQLite: UPDATE topics SET status='active'
       │    └─> Dashboard now shows ACTIVE
       │
       └─ Kafka Producer: send(topic, value=JSON)
            └─> Kafka Broker stores message

Consumer (CLI)
       │
       ├─ POST /api/subscriptions (subscribe)
       │    └─> SQLite: INSERT into user_subscriptions
       │
       ├─ Kafka Consumer: subscribe(["topic_name"])
       │    └─> Start polling from broker
       │
       └─ Display messages real-time
            └─ Poll Kafka every 1s
            └─ Format & print each message
```

---

## State Transitions

### Topic States

```
PENDING ──[Approve]──> APPROVED ──[Producer Activates]──> ACTIVE
   ↓                                                          ↓
[Reject]                                              [Deactivate]
   ↓                                                          ↓
REJECTED                                              INACTIVE
```

### Subscription States

```
User subscribes
     ↓
ACTIVE (receiving messages)
     ↓
User unsubscribes
     ↓
(DELETED from table)
```

---

## Error Scenarios & Recovery

### Scenario 1: Producer Can't Connect to Admin API

**Problem:** Producer logs `Error calling activate API: [Errno 111] Connection refused`

**Root Cause:** Admin API not running or unreachable IP

**Recovery:**
```bash
# On Admin machine:
python app.py
# Verify: curl http://10.214.203.13:5000/api/health
# Returns: {"status": "healthy", ...}
```

### Scenario 2: Consumer Sees No New Messages

**Problem:** Consumer subscribes but no messages appear

**Root Cause:** Topic is pending or topic name mismatch

**Recovery:**
```bash
# Check topic status
curl http://10.214.203.13:5000/api/topics

# Ensure topic is ACTIVE, not PENDING
# Wait for Producer to activate it (Topic Watcher polls every 5s)
```

### Scenario 3: Kafka Broker Crashes

**Problem:** Producer/Consumer get "NoBrokersAvailable"

**Root Cause:** Kafka process stopped

**Recovery:**
```bash
# On Broker machine:
cd /path/to/kafka
bin/kafka-server-start.sh config/server.properties &
# Wait 10 seconds for recovery
```

---

## Performance & Scalability

- **Message throughput:** ~100-1000 msgs/sec (depends on Kafka broker & network)
- **Subscription limit:** SQLite can handle 100+ concurrent subscriptions
- **Topic limit:** Tested up to 50 topics without degradation
- **Consumer groups:** Each consumer is an independent group (consumer_group_user_1, etc.)

---

## Time Estimates

| Activity | Duration |
|----------|----------|
| Setup Kafka broker | 5 minutes |
| Deploy Admin dashboard | 2 minutes |
| Start Producer daemon | 1 minute |
| Create topic (Admin) | 1 minute |
| Approve topic (Admin) | 1 minute |
| Topic activation (Auto) | 5-10 seconds |
| Start Consumer | 1 minute |
| Subscribe to topic (Consumer) | 1 minute |
| **Total end-to-end** | **~18 minutes** |

---

## Next Steps & Enhancements

1. **Multi-node Kafka cluster** (replication-factor > 1)
2. **Consumer groups** (multiple consumers per topic, auto-rebalance)
3. **Message persistence** (store all messages in MySQL/PostgreSQL)
4. **Authentication & authorization** (user roles, topic ACLs)
5. **Monitoring & alerting** (Prometheus, Grafana)
6. **Docker deployment** (docker-compose for instant multi-container setup)
7. **Schema registry** (Avro/Protobuf message validation)
8. **Dead-letter queues** (failed message handling)
