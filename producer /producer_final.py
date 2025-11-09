import threading
import queue
import json
import time
import logging
import random
import uuid
from datetime import datetime
from typing import List
from kafka import KafkaProducer, KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError
import requests
import os

# ================= CONFIGURATION =================
BOOTSTRAP_SERVERS = ['10.214.203.73:9092']   # Kafka broker
ADMIN_API_URL = 'http://10.214.203.13:5000'  # Flask Admin API
POLL_INTERVAL = 5
PRODUCER_SECRET = os.environ.get("PRODUCER_SECRET", "ChangeThisProducerSecret!")

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("producer.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ===================================================
#  Random Data Generator
# ===================================================
class RandomDataGenerator:
    """Generate realistic structured data for different topic types."""

    @staticmethod
    def generate(topic_type):
        if topic_type == 'sensor':
            return {
                'sensor_id': f'sensor_{random.randint(1,100)}',
                'temperature': round(random.uniform(20, 40), 2),
                'humidity': random.randint(30, 90),
                'pressure': round(random.uniform(950, 1050), 2),
                'timestamp': datetime.now().isoformat()
            }
        elif topic_type == 'user_activity':
            return {
                'user_id': f'user_{random.randint(1,1000)}',
                'action': random.choice(['login', 'logout', 'click', 'purchase']),
                'page': f'/page/{random.randint(1,50)}',
                'duration': random.randint(1, 300)
            }
        elif topic_type == 'logs':
            return {
                'service': random.choice(['auth', 'api', 'db', 'cache']),
                'level': random.choice(['INFO', 'WARN', 'ERROR']),
                'message': f'Log entry #{random.randint(100, 999)}',
                'response_time_ms': random.randint(10, 500)
            }
        elif topic_type == 'payments':
            return {
                'transaction_id': str(uuid.uuid4()),
                'amount': round(random.uniform(5, 500), 2),
                'currency': random.choice(['USD', 'EUR', 'INR']),
                'method': random.choice(['card', 'upi', 'wallet'])
            }
        elif topic_type == 'weather':
            return {
                'city': random.choice(['Bangalore', 'NYC', 'London', 'Tokyo']),
                'temperature': random.randint(-5, 45),
                'condition': random.choice(['sunny', 'rainy', 'cloudy'])
            }
        else:
            return {
                'id': str(uuid.uuid4()),
                'value': random.randint(1, 1000),
                'timestamp': datetime.now().isoformat()
            }

# ===================================================
#  Admin API Client
# ===================================================
class AdminAPIClient:
    """Interface for Admin API."""
    def __init__(self, admin_url: str):
        self.admin_url = admin_url
        self.timeout = 5

    def get_topics_by_status(self, statuses: List[str]) -> List[str]:
        """Fetch topics matching one or more statuses."""
        try:
            res = requests.get(f"{self.admin_url}/api/topics", timeout=self.timeout)
            if res.status_code == 200:
                topics = res.json()
                return [t['topic_name'] for t in topics if t.get('status') in statuses]
            logger.error(f"Error fetching topics: {res.status_code}")
            return []
        except Exception as e:
            logger.error(f"Admin API unreachable: {e}")
            return []

    def health_check(self) -> bool:
        try:
            res = requests.get(f"{self.admin_url}/api/health", timeout=self.timeout)
            return res.status_code == 200
        except Exception:
            return False

    def mark_active(self, topic_name: str):
        """Mark topic as active via Admin API."""
        try:
            res = requests.post(
                f"{self.admin_url}/api/topics/activate_by_name",
                json={"topic_name": topic_name},
                headers={"X-Producer-Key": PRODUCER_SECRET},
                timeout=self.timeout
            )
            if res.status_code == 200:
                logger.info(f"✅ Marked '{topic_name}' ACTIVE in Admin API")
            else:
                logger.warning(f"⚠️ Failed to mark '{topic_name}' active: {res.text}")
        except Exception as e:
            logger.error(f"Error calling activate API for {topic_name}: {e}")

# ===================================================
#  Producer System
# ===================================================
class ProducerSystem:
    def __init__(self):
        self.admin_api = AdminAPIClient(ADMIN_API_URL)
        self.data_generator = RandomDataGenerator()
        self.queue = queue.Queue(maxsize=1000)
        self.shutdown_event = threading.Event()

        # Kafka clients
        self.producer = KafkaProducer(
            bootstrap_servers=BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all'
        )
        self.admin_client = KafkaAdminClient(bootstrap_servers=BOOTSTRAP_SERVERS)
        logger.info("✅ Kafka Producer and Admin Client initialized successfully")

    def create_topic_if_not_exists(self, topic_name: str):
        """Ensure topic exists in Kafka, and mark active in Admin API."""
        try:
            existing_topics = self.admin_client.list_topics()
            if topic_name not in existing_topics:
                topic = NewTopic(name=topic_name, num_partitions=3, replication_factor=1)
                self.admin_client.create_topics([topic])
                logger.info(f"🆕 Created topic '{topic_name}' in Kafka")

                # Immediately mark it active
                self.admin_api.mark_active(topic_name)
            else:
                logger.debug(f"Topic '{topic_name}' already exists")
        except TopicAlreadyExistsError:
            pass
        except Exception as e:
            logger.error(f"Error creating topic {topic_name}: {e}")

    # Thread 1: Data Generator
    def data_generator_thread(self):
        logger.info("🧠 Data Generator Thread started")
        while not self.shutdown_event.is_set():
            try:
                # Fetch approved + active topics
                topics = self.admin_api.get_topics_by_status(['approved', 'active'])
                if not topics:
                    logger.info("No approved/active topics found, waiting...")
                    time.sleep(5)
                    continue

                topic_name = random.choice(topics)
                self.create_topic_if_not_exists(topic_name)

                # Infer type
                lower = topic_name.lower()
                if 'sensor' in lower:
                    topic_type = 'sensor'
                elif 'log' in lower:
                    topic_type = 'logs'
                elif 'weather' in lower:
                    topic_type = 'weather'
                elif 'user' in lower:
                    topic_type = 'user_activity'
                elif 'payment' in lower:
                    topic_type = 'payments'
                else:
                    topic_type = 'generic'

                msg = {
                    'topic': topic_name,
                    'data_type': topic_type,
                    'payload': self.data_generator.generate(topic_type),
                    'timestamp': datetime.now().isoformat()
                }

                self.queue.put(msg, timeout=2)
                time.sleep(random.uniform(0.5, 1.5))
            except queue.Full:
                logger.warning("Queue full, dropping message.")
            except Exception as e:
                logger.error(f"Error in data generator: {e}")
                time.sleep(2)

    # Thread 2: Publisher
    def publisher_thread(self):
        logger.info("📤 Publisher Thread started")
        while not self.shutdown_event.is_set():
            try:
                msg = self.queue.get(timeout=3)
                topic = msg['topic']
                self.producer.send(topic, value=msg)
                self.producer.flush()
                logger.info(f"✅ Published to {topic}: {msg['data_type']}")
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in publisher: {e}")
                time.sleep(2)

    # Thread 3: Topic Watcher
    def topic_watcher_thread(self):
        logger.info("👀 Topic Watcher Thread started")
        known = set()
        while not self.shutdown_event.is_set():
            try:
                # Watch approved topics, create + activate new ones
                approved = self.admin_api.get_topics_by_status(['approved'])
                for topic in approved:
                    if topic not in known:
                        self.create_topic_if_not_exists(topic)
                        known.add(topic)
                time.sleep(POLL_INTERVAL)
            except Exception as e:
                logger.error(f"Error in topic watcher: {e}")
                time.sleep(POLL_INTERVAL)

    def start(self):
        if not self.admin_api.health_check():
            logger.error("❌ Admin API not reachable! Start Flask first.")
            return

        logger.info("✅ Admin API reachable. Starting producer system...")

        threads = [
            threading.Thread(target=self.data_generator_thread, daemon=True),
            threading.Thread(target=self.publisher_thread, daemon=True),
            threading.Thread(target=self.topic_watcher_thread, daemon=True)
        ]
        for t in threads:
            t.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown signal received")
            self.shutdown_event.set()
            self.producer.close()
            self.admin_client.close()
            logger.info("Producer system stopped cleanly.")

# ===================================================
# Main
# ===================================================
if __name__ == '__main__':
    system = ProducerSystem()
    system.start()
