import os
import json
import time
import redis
from flask import Flask, request, jsonify

app = Flask(__name__)

r = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    password=os.environ.get('REDIS_PASSWORD') or None,
    decode_responses=True
)

@app.route('/health')
def health():
    r.ping()
    return jsonify({'status': 'ok', 'service': 'ingest-api'})

@app.route('/ingest/metric', methods=['POST'])
def ingest_metric():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'invalid json'}), 400

    required = ['service', 'metric_name', 'value']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'missing fields: {missing}'}), 422

    try:
        value = float(data['value'])
    except (TypeError, ValueError):
        return jsonify({'error': 'value must be numeric'}), 422

    payload = {
        'service': str(data['service']),
        'metric_name': str(data['metric_name']),
        'value': value,
        'timestamp': data.get('timestamp', time.time()),
    }
    r.rpush('metrics_queue', json.dumps(payload))
    return jsonify({'status': 'queued', 'data': payload}), 201

@app.route('/ingest/batch', methods=['POST'])
def ingest_batch():
    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return jsonify({'error': 'expected a list of metric objects'}), 400

    queued = 0
    errors = []
    for i, item in enumerate(data):
        required = ['service', 'metric_name', 'value']
        missing = [f for f in required if f not in item]
        if missing:
            errors.append({'index': i, 'error': f'missing fields: {missing}'})
            continue
        try:
            value = float(item['value'])
        except (TypeError, ValueError):
            errors.append({'index': i, 'error': 'value must be numeric'})
            continue
        payload = {
            'service': str(item['service']),
            'metric_name': str(item['metric_name']),
            'value': value,
            'timestamp': item.get('timestamp', time.time()),
        }
        r.rpush('metrics_queue', json.dumps(payload))
        queued += 1

    return jsonify({'queued': queued, 'errors': errors}), 201 if queued else 422
