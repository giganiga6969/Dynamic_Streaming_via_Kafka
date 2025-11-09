import threading
import json
import logging
import time
from kafka import KafkaConsumer, TopicPartition, OffsetAndMetadata
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BOOTSTRAP_SERVERS = ['10.214.203.73:9092']
ADMIN_API_URL = 'http://10.214.203.13:5000'
USER_ID = 'user_1'

class AdminAPIClient:
    def __init__(self, admin_url: str):
        self.admin_url = admin_url
        self.timeout = 5

    def get_all_active_topics(self):
        try:
            r = requests.get(f'{self.admin_url}/api/topics/active', timeout=self.timeout)
            if r.status_code == 200:
                return [t['topic_name'] for t in r.json()]
            return []
        except Exception as e:
            logger.error(f"Error fetching active topics: {e}")
            return []

    def get_subscribed_topics(self, user_id: str):
        try:
            r = requests.get(f'{self.admin_url}/api/subscriptions', params={'user_id': user_id}, timeout=self.timeout)
            if r.status_code == 200:
                return [s['topic_name'] for s in r.json() if s.get('status') == 'active']
            return []
        except Exception as e:
            logger.error(f"Error fetching subscriptions: {e}")
            return []

    def subscribe_to_topic(self, user_id: str, topic_name: str):
        try:
            r = requests.post(f'{self.admin_url}/api/subscriptions', json={'user_id': user_id, 'topic_name': topic_name}, timeout=self.timeout)
            return r.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Error subscribing: {e}")
            return False

    def unsubscribe_from_topic(self, user_id: str, topic_name: str):
        try:
            r = requests.delete(f'{self.admin_url}/api/subscriptions', json={'user_id': user_id, 'topic_name': topic_name}, timeout=self.timeout)
            return r.status_code == 200
        except Exception as e:
            logger.error(f"Error unsubscribing: {e}")
            return False


class InteractiveConsumer:
    def __init__(self, bootstrap_servers, user_id, admin_api_url):
        self.bootstrap_servers = bootstrap_servers
        self.user_id = user_id
        self.admin_api = AdminAPIClient(admin_api_url)
        self.consumer = None
        self.running = False
        self.thread = None
        self.messages_processed = 0

    def init_consumer(self):
        subs = self.admin_api.get_subscribed_topics(self.user_id)
        self.consumer = KafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id=f'consumer-group-{self.user_id}',
            enable_auto_commit=False,
            auto_offset_reset='earliest',
            value_deserializer=lambda v: json.loads(v.decode('utf-8')) if v else None,
            client_id=f'consumer-{self.user_id}'
        )
        if subs:
            self.consumer.subscribe(subs)
        logger.info(f"Subscribed to: {subs}")

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.consume_loop, daemon=True)
        self.thread.start()
        print("✅ Streaming started...\n")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)
        print(f"\n⏹️  Consumer stopped. Total messages processed: {self.messages_processed}")

    def consume_loop(self):
        while self.running:
            try:
                records = self.consumer.poll(timeout_ms=1000)
                for tp, msgs in records.items():
                    for record in msgs:
                        self.display_message(record)
                        self.commit_offset(tp, record)
                        self.messages_processed += 1
            except Exception as e:
                logger.error(f"Consume error: {e}")
                time.sleep(1)

    def commit_offset(self, tp, record):
        try:
            # Handle both old/new kafka-python versions
            try:
                om = OffsetAndMetadata(record.offset + 1, '', None)
            except TypeError:
                om = OffsetAndMetadata(record.offset + 1, '')
            self.consumer.commit({tp: om})
        except Exception as e:
            logger.error(f"Commit error: {e}")

    def display_message(self, record):
        print("\n📨 Topic:", record.topic)
        print("📦 Data Type:", record.value.get('data_type', 'N/A'))
        print("🕒 Timestamp:", record.value.get('timestamp'))
        print("🧩 Payload:", json.dumps(record.value.get('payload', {}), indent=2))

    def show_menu(self):
        print("\n" + "="*60)
        print("🎛️  KAFKA CONSUMER MENU")
        print("="*60)
        print("1. View Available Topics")
        print("2. View My Subscriptions")
        print("3. Subscribe to Topic")
        print("4. Unsubscribe from Topic")
        print("5. Start/Restart Consumer")
        print("6. Stop Consumer")
        print("7. Show Statistics")
        print("0. Exit")
        print("="*60)

    def show_available_topics(self):
        topics = self.admin_api.get_all_active_topics()
        print("\n📋 ACTIVE TOPICS:")
        if topics:
            for i, t in enumerate(topics, 1):
                print(f"  {i}. {t}")
        else:
            print("  ❌ None found")

    def show_subscriptions(self):
        topics = self.admin_api.get_subscribed_topics(self.user_id)
        print("\n✅ My Subscriptions:")
        if topics:
            for i, t in enumerate(topics, 1):
                print(f"  {i}. {t}")
        else:
            print("  ❌ None found")

    def show_stats(self):
        print("\n📊 CONSUMER STATS")
        print(f"Running: {'Yes ✅' if self.running else 'No ⏹️'}")
        print(f"Messages Processed: {self.messages_processed}")

    def run(self):
        self.init_consumer()
        while True:
            self.show_menu()
            choice = input("\n➡️  Select option: ").strip()

            if choice == '1':
                self.show_available_topics()
            elif choice == '2':
                self.show_subscriptions()
            elif choice == '3':
                self.show_available_topics()
                topic = input("\n🔔 Enter topic to subscribe: ").strip()
                if self.admin_api.subscribe_to_topic(self.user_id, topic):
                    print(f"✅ Subscribed to {topic}")
                    subs = self.admin_api.get_subscribed_topics(self.user_id)
                    self.consumer.subscribe(subs)
            elif choice == '4':
                self.show_subscriptions()
                topic = input("\n🔕 Enter topic to unsubscribe: ").strip()
                if self.admin_api.unsubscribe_from_topic(self.user_id, topic):
                    print(f"✅ Unsubscribed from {topic}")
                    subs = self.admin_api.get_subscribed_topics(self.user_id)
                    if subs:
                        self.consumer.subscribe(subs)
                    else:
                        self.consumer.unsubscribe()
            elif choice == '5':
                if not self.running:
                    self.start()
                else:
                    print("⚠️ Already running!")
            elif choice == '6':
                if self.running:
                    self.stop()
                else:
                    print("⚠️ Not running.")
            elif choice == '7':
                self.show_stats()
            elif choice == '0':
                if self.running:
                    self.stop()
                print("\n👋 Exiting...")
                break
            else:
                print("❌ Invalid option")
            input("\nPress Enter to continue...")

def main():
    c = InteractiveConsumer(BOOTSTRAP_SERVERS, USER_ID, ADMIN_API_URL)
    try:
        c.run()
    except KeyboardInterrupt:
        c.stop()

if __name__ == '__main__':
    main()