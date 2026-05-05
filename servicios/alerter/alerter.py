import os
import time
import redis
import psycopg2
import psycopg2.extras
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [alerter] %(message)s'
)
log = logging.getLogger(__name__)

THRESHOLDS = {
    'cpu_usage':       float(os.environ.get('THRESHOLD_CPU', 80.0)),
    'memory_usage':    float(os.environ.get('THRESHOLD_MEMORY', 85.0)),
    'error_rate':      float(os.environ.get('THRESHOLD_ERROR_RATE', 5.0)),
    'response_time_ms': float(os.environ.get('THRESHOLD_RESPONSE_TIME', 2000.0)),
}

CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', 15))
ALERT_COOLDOWN = int(os.environ.get('ALERT_COOLDOWN', 60))

r = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    password=os.environ.get('REDIS_PASSWORD') or None,
    decode_responses=True
)

def get_db():
    return psycopg2.connect(os.environ['POSTGRES_DSN'])

def check_and_alert(conn):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    for metric_name, threshold in THRESHOLDS.items():
        cur.execute('''
            SELECT service, metric_name, ROUND(AVG(value)::numeric, 2) AS avg_value
            FROM metrics
            WHERE metric_name = %s
              AND recorded_at > NOW() - INTERVAL '1 minute'
            GROUP BY service, metric_name
            HAVING AVG(value) > %s
        ''', (metric_name, threshold))
        for row in cur.fetchall():
            key = f"alert_cooldown:{row['service']}:{metric_name}"
            if r.get(key):
                continue
            ins = conn.cursor()
            ins.execute(
                'INSERT INTO alerts (service, metric_name, value, threshold) VALUES (%s,%s,%s,%s)',
                (row['service'], metric_name, row['avg_value'], threshold)
            )
            conn.commit()
            ins.close()
            r.setex(key, ALERT_COOLDOWN, '1')
            r.publish('alerts', f"{row['service']}:{metric_name}={row['avg_value']} > {threshold}")
            log.warning(
                'ALERT %s/%s: %.2f > %.2f',
                row['service'], metric_name, row['avg_value'], threshold
            )
    cur.close()

def main():
    log.info('starting — checking every %ds, thresholds: %s', CHECK_INTERVAL, THRESHOLDS)
    conn = None
    while True:
        try:
            if conn is None or conn.closed:
                conn = get_db()
            check_and_alert(conn)
        except psycopg2.Error as e:
            log.error('db error: %s', e)
            try:
                conn.close()
            except Exception:
                pass
            conn = None
        except redis.RedisError as e:
            log.error('redis error: %s', e)
        except Exception as e:
            log.error('unexpected: %s', e)
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
