import os
import redis
import psycopg2
import psycopg2.extras
from flask import Flask, jsonify

app = Flask(__name__)

r = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    password=os.environ.get('REDIS_PASSWORD') or None,
    decode_responses=True
)

def get_db():
    return psycopg2.connect(os.environ['POSTGRES_DSN'])

@app.route('/health')
def health():
    conn = get_db()
    conn.close()
    return jsonify({'status': 'ok', 'service': 'query-api'})

@app.route('/query/metrics')
def get_metrics():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM metrics ORDER BY recorded_at DESC LIMIT 200')
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for row in rows:
        if row.get('recorded_at'):
            row['recorded_at'] = row['recorded_at'].isoformat()
        if row.get('timestamp'):
            row['timestamp'] = row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else row['timestamp']
    return jsonify(rows)

@app.route('/query/metrics/<service>')
def get_metrics_by_service(service):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        'SELECT * FROM metrics WHERE service=%s ORDER BY recorded_at DESC LIMIT 100',
        (service,)
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for row in rows:
        if row.get('recorded_at'):
            row['recorded_at'] = row['recorded_at'].isoformat()
    return jsonify(rows)

@app.route('/query/alerts')
def get_alerts():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM alerts ORDER BY triggered_at DESC LIMIT 100')
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for row in rows:
        if row.get('triggered_at'):
            row['triggered_at'] = row['triggered_at'].isoformat()
    return jsonify(rows)

@app.route('/query/services')
def get_services():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT service FROM metrics ORDER BY service')
    services = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(services)

@app.route('/query/summary')
def get_summary():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('''
        SELECT service, metric_name,
               ROUND(AVG(value)::numeric, 2) AS avg_value,
               ROUND(MAX(value)::numeric, 2) AS max_value,
               ROUND(MIN(value)::numeric, 2) AS min_value,
               COUNT(*) AS total
        FROM metrics
        WHERE recorded_at > NOW() - INTERVAL '5 minutes'
        GROUP BY service, metric_name
        ORDER BY service, metric_name
    ''')
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(rows)
