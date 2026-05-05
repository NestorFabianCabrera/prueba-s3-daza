import os
import json
import time
import redis
import psycopg2
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [aggregator] %(message)s'
)
log = logging.getLogger(__name__)

r = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    password=os.environ.get('REDIS_PASSWORD') or None,
    decode_responses=True
)

def get_db():
    return psycopg2.connect(os.environ['POSTGRES_DSN'])

def ensure_schema(conn):
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id          SERIAL PRIMARY KEY,
            service     VARCHAR(100) NOT NULL,
            metric_name VARCHAR(100) NOT NULL,
            value       FLOAT        NOT NULL,
            timestamp   TIMESTAMP,
            recorded_at TIMESTAMP    DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id           SERIAL PRIMARY KEY,
            service      VARCHAR(100) NOT NULL,
            metric_name  VARCHAR(100) NOT NULL,
            value        FLOAT        NOT NULL,
            threshold    FLOAT        NOT NULL,
            triggered_at TIMESTAMP    DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_metrics_service    ON metrics (service);
        CREATE INDEX IF NOT EXISTS idx_metrics_recorded   ON metrics (recorded_at DESC);
        CREATE INDEX IF NOT EXISTS idx_alerts_triggered   ON alerts  (triggered_at DESC);
    ''')
    conn.commit()
    cur.close()
    log.info('schema ready')

def process(conn, raw):
    data = json.loads(raw)
    cur = conn.cursor()
    cur.execute(
        '''INSERT INTO metrics (service, metric_name, value, timestamp)
           VALUES (%s, %s, %s, to_timestamp(%s))''',
        (data['service'], data['metric_name'], data['value'],
         data.get('timestamp', time.time()))
    )
    conn.commit()
    cur.close()
    log.info("stored %s/%s=%.2f", data['service'], data['metric_name'], data['value'])

def main():
    log.info('starting — waiting for messages on metrics_queue')
    conn = None
    while True:
        try:
            if conn is None or conn.closed:
                conn = get_db()
                ensure_schema(conn)
            result = r.blpop('metrics_queue', timeout=5)
            if result:
                _, raw = result
                process(conn, raw)
        except psycopg2.Error as e:
            log.error('db error: %s', e)
            try:
                conn.close()
            except Exception:
                pass
            conn = None
            time.sleep(3)
        except redis.RedisError as e:
            log.error('redis error: %s', e)
            time.sleep(3)
        except Exception as e:
            log.error('unexpected: %s', e)
            time.sleep(1)

if __name__ == '__main__':
    main()
