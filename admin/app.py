from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import sqlite3
import logging
import os
from datetime import datetime
from typing import Dict, List, Tuple

# ----------------- Config -----------------
PRODUCER_SECRET = os.environ.get("PRODUCER_SECRET", "ChangeThisProducerSecret!")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['DATABASE'] = 'kafka_system.db'
CORS(app)


# ----------------- DB Service -----------------
class DatabaseService:
    """Service for database operations"""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS topics (
                    topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_name VARCHAR(255) UNIQUE NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    partitions INTEGER DEFAULT 1,
                    replication_factor INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMP,
                    created_by VARCHAR(100),
                    activated_at TIMESTAMP,
                    description TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id VARCHAR(100) NOT NULL,
                    topic_id INTEGER NOT NULL,
                    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'active',
                    FOREIGN KEY (topic_id) REFERENCES topics(topic_id),
                    UNIQUE(user_id, topic_id)
                )
            ''')

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_topics_status ON topics(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sub_user_topic ON user_subscriptions(user_id, topic_id)')

            conn.commit()
            conn.close()
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_all_topics(self) -> List[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT topic_id, topic_name, status, partitions, replication_factor,
                       created_at, approved_at, activated_at, created_by, description
                FROM topics
                ORDER BY created_at DESC
            ''')
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing topics: {e}")
            return []

    def get_topic_by_id(self, topic_id: int) -> Dict:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM topics WHERE topic_id = ?', (topic_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting topic: {e}")
            return None

    def get_topic_by_name(self, topic_name: str) -> Dict:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM topics WHERE topic_name = ?', (topic_name,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting topic by name: {e}")
            return None

    def create_topic_request(self, topic_name: str, partitions: int = 1,
                             replication_factor: int = 1, created_by: str = None,
                             description: str = None) -> Tuple[bool, str, int]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO topics (topic_name, status, partitions, replication_factor,
                                    created_by, description)
                VALUES (?, 'pending', ?, ?, ?, ?)
            ''', (topic_name, partitions, replication_factor, created_by, description))
            conn.commit()
            topic_id = cursor.lastrowid
            conn.close()
            logger.info(f"Topic request created: {topic_name}")
            return True, "Topic creation request submitted", topic_id
        except sqlite3.IntegrityError:
            return False, "Topic already exists", None
        except Exception as e:
            logger.error(f"Error creating topic request: {e}")
            return False, str(e), None

    def approve_topic(self, topic_id: int) -> Tuple[bool, str]:
        try:
            topic = self.get_topic_by_id(topic_id)
            if not topic:
                return False, "Topic not found"
            if topic['status'] != 'pending':
                return False, f"Topic is already {topic['status']}"
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE topics
                SET status = 'approved', approved_at = ?
                WHERE topic_id = ?
            ''', (datetime.utcnow().isoformat(), topic_id))
            conn.commit()
            conn.close()
            logger.info(f"Topic {topic_id} approved")
            return True, "Topic approved successfully"
        except Exception as e:
            logger.error(f"Error approving topic: {e}")
            return False, str(e)

    def activate_topic_by_name(self, topic_name: str) -> Tuple[bool, str]:
        try:
            topic = self.get_topic_by_name(topic_name)
            if not topic:
                return False, "Topic not found"
            if topic['status'] == 'active':
                return True, "Topic already active"
            if topic['status'] not in ('approved', 'active'):
                # Optional: allow activation from pending if you want
                logger.warning(f"Activating topic '{topic_name}' from status '{topic['status']}'")
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE topics
                SET status = 'active', activated_at = ?
                WHERE topic_name = ?
            ''', (datetime.utcnow().isoformat(), topic_name))
            conn.commit()
            conn.close()
            logger.info(f"Topic '{topic_name}' marked ACTIVE")
            return True, "Topic activated"
        except Exception as e:
            logger.error(f"Error activating topic: {e}")
            return False, str(e)

    def deactivate_topic(self, topic_id: int) -> Tuple[bool, str]:
        try:
            topic = self.get_topic_by_id(topic_id)
            if not topic:
                return False, "Topic not found"
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE topics SET status = \'inactive\' WHERE topic_id = ?', (topic_id,))
            cursor.execute('UPDATE user_subscriptions SET status = \'inactive\' WHERE topic_id = ?', (topic_id,))
            conn.commit()
            conn.close()
            logger.info(f"Topic {topic_id} deactivated")
            return True, "Topic deactivated successfully"
        except Exception as e:
            logger.error(f"Error deactivating topic: {e}")
            return False, str(e)

    def list_subscriptions(self, user_id: str = None) -> List[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if user_id:
                cursor.execute('''
                    SELECT s.subscription_id, s.user_id, t.topic_name,
                           s.subscribed_at, s.status
                    FROM user_subscriptions s
                    JOIN topics t ON s.topic_id = t.topic_id
                    WHERE s.user_id = ?
                    ORDER BY s.subscribed_at DESC
                ''', (user_id,))
            else:
                cursor.execute('''
                    SELECT s.subscription_id, s.user_id, t.topic_name,
                           s.subscribed_at, s.status
                    FROM user_subscriptions s
                    JOIN topics t ON s.topic_id = t.topic_id
                    ORDER BY s.subscribed_at DESC
                ''')
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing subscriptions: {e}")
            return []

    def add_subscription(self, user_id: str, topic_name: str) -> Tuple[bool, str]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT topic_id FROM topics WHERE topic_name = ?', (topic_name,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False, "Topic not found"
            topic_id = row[0]
            cursor.execute('''
                INSERT INTO user_subscriptions (user_id, topic_id, status)
                VALUES (?, ?, 'active')
            ''', (user_id, topic_id))
            conn.commit()
            conn.close()
            logger.info(f"User {user_id} subscribed to {topic_name}")
            return True, "Subscription added successfully"
        except sqlite3.IntegrityError:
            return False, "Already subscribed to this topic"
        except Exception as e:
            logger.error(f"Error adding subscription: {e}")
            return False, str(e)

    def remove_subscription(self, user_id: str, topic_name: str) -> Tuple[bool, str]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM user_subscriptions
                WHERE user_id = ? AND topic_id = (
                    SELECT topic_id FROM topics WHERE topic_name = ?
                )
            ''', (user_id, topic_name))
            conn.commit()
            conn.close()
            logger.info(f"User {user_id} unsubscribed from {topic_name}")
            return True, "Subscription removed successfully"
        except Exception as e:
            logger.error(f"Error removing subscription: {e}")
            return False, str(e)

    def get_stats(self) -> Dict:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM topics')
            total_topics = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM topics WHERE status = 'pending'")
            pending_topics = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM topics WHERE status = 'active'")
            active_topics = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM user_subscriptions')
            total_subscriptions = cursor.fetchone()[0]
            conn.close()
            return {
                'total_topics': total_topics,
                'pending_topics': pending_topics,
                'active_topics': active_topics,
                'total_subscriptions': total_subscriptions,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}


db_service = DatabaseService(app.config['DATABASE'])


# ----------------- API -----------------
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}), 200

@app.route('/api/topics', methods=['GET'])
def list_topics():
    try:
        topics = db_service.list_all_topics()
        return jsonify(topics), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/topics', methods=['POST'])
def create_topic():
    try:
        data = request.get_json() or {}
        if 'name' not in data:
            return jsonify({'error': 'Topic name required (field: name)'}), 400
        ok, msg, topic_id = db_service.create_topic_request(
            topic_name=data['name'],
            partitions=data.get('partitions', 1),
            replication_factor=data.get('replication_factor', 1),
            created_by=data.get('created_by', 'unknown'),
            description=data.get('description', '')
        )
        if ok:
            return jsonify({'message': msg, 'topic_id': topic_id}), 201
        return jsonify({'error': msg}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/topics/<int:topic_id>', methods=['GET'])
def get_topic(topic_id):
    try:
        topic = db_service.get_topic_by_id(topic_id)
        if topic:
            return jsonify(topic), 200
        return jsonify({'error': 'Topic not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/topics/<int:topic_id>/approve', methods=['POST'])
def approve_topic(topic_id):
    try:
        ok, msg = db_service.approve_topic(topic_id)
        if ok:
            return jsonify({'message': msg}), 200
        return jsonify({'error': msg}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/topics/<int:topic_id>/deactivate', methods=['POST'])
def deactivate_topic(topic_id):
    try:
        ok, msg = db_service.deactivate_topic(topic_id)
        if ok:
            return jsonify({'message': msg}), 200
        return jsonify({'error': msg}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --------- NEW: Producer callback to mark ACTIVE ----------
@app.route('/api/topics/activate_by_name', methods=['POST'])
def activate_by_name():
    """
    Called by the PRODUCER after it successfully creates the Kafka topic.
    Requires header: X-Producer-Key: <PRODUCER_SECRET>
    Body: { "topic_name": "ABC" }
    """
    try:
        key = request.headers.get('X-Producer-Key', '')
        if key != PRODUCER_SECRET:
            return jsonify({'error': 'Unauthorized'}), 401

        data = request.get_json() or {}
        topic_name = data.get('topic_name')
        if not topic_name:
            return jsonify({'error': 'topic_name required'}), 400

        ok, msg = db_service.activate_topic_by_name(topic_name)
        if ok:
            return jsonify({'message': msg}), 200
        return jsonify({'error': msg}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --------- Lists only ACTIVE topics ----------
@app.route('/api/topics/active', methods=['GET'])
def get_active_topics():
    try:
        topics = db_service.list_all_topics()
        active = [ {'topic_name': t['topic_name'], 'description': t['description'], 'activated_at': t['activated_at']}
                   for t in topics if t['status'] == 'active' ]
        return jsonify(active), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Subscriptions
@app.route('/api/subscriptions', methods=['GET'])
def list_subscriptions():
    try:
        user_id = request.args.get('user_id')
        subs = db_service.list_subscriptions(user_id)
        return jsonify(subs), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/subscriptions', methods=['POST'])
def add_subscription():
    try:
        data = request.get_json() or {}
        if 'user_id' not in data or 'topic_name' not in data:
            return jsonify({'error': 'user_id and topic_name required'}), 400
        ok, msg = db_service.add_subscription(data['user_id'], data['topic_name'])
        if ok:
            return jsonify({'message': msg}), 201
        return jsonify({'error': msg}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/subscriptions', methods=['DELETE'])
def remove_subscription():
    try:
        data = request.get_json() or {}
        if 'user_id' not in data or 'topic_name' not in data:
            return jsonify({'error': 'user_id and topic_name required'}), 400
        ok, msg = db_service.remove_subscription(data['user_id'], data['topic_name'])
        if ok:
            return jsonify({'message': msg}), 200
        return jsonify({'error': msg}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        return jsonify(db_service.get_stats()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Frontend
@app.route('/')
def dashboard():
    return render_template('dashboard.html')


if __name__ == '__main__':
    # Bind to your ZeroTier/LAN IP so others can reach it
    app.run(host='10.214.203.13', port=5000, debug=True)
