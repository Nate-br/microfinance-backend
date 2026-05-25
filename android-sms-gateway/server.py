#!/usr/bin/env python3
import os
import uuid
import time
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from functools import wraps

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = os.getenv('API_KEY', '')
PORT = int(os.getenv('PORT', 8080))
HOST = os.getenv('HOST', '0.0.0.0')

messages_db = {}


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if API_KEY:
            api_key = request.headers.get('X-API-Key')
            if api_key != API_KEY:
                return jsonify({'error': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated


def send_sms_android(phone: str, message: str) -> dict:
    try:
        import androidhelper as android
    except ImportError:
        try:
            import android
        except ImportError:
            return {
                'success': False,
                'error': 'Android module not available. Install android-tools in Termux: pkg install android-tools',
                'mock': True
            }

    try:
        droid = android.Android()
        result = droid.smsSend(phone, message)

        if result[0]:
            return {'success': True, 'mock': False}
        else:
            return {'success': False, 'error': str(result[1])}
    except Exception as e:
        logger.error(f"SMS send error: {str(e)}")
        return {'success': False, 'error': str(e), 'mock': True}


@app.route('/api/send-sms', methods=['POST'])
@require_api_key
def send_sms():
    data = request.get_json()

    if not data or 'phone' not in data or 'message' not in data:
        return jsonify({'error': 'Missing phone or message'}), 400

    phone = data['phone']
    message = data['message']
    message_id = data.get('message_id', str(uuid.uuid4()))

    logger.info(f"Sending SMS to {phone}: {message[:50]}...")

    result = send_sms_android(phone, message)

    messages_db[message_id] = {
        'phone': phone,
        'message': message,
        'status': 'delivered' if result.get('success') else 'failed',
        'timestamp': datetime.now().isoformat(),
        'response': result
    }

    if result.get('success'):
        return jsonify({
            'success': True,
            'message_id': message_id,
            'status': 'sent'
        })
    else:
        error_msg = result.get('error', 'Failed to send SMS')
        if result.get('mock'):
            logger.warning(f"Mock mode: SMS would be sent to {phone}")
            messages_db[message_id]['status'] = 'mock_sent'
            return jsonify({
                'success': True,
                'message_id': message_id,
                'status': 'mock_sent',
                'note': 'Running in mock mode - SMS not actually sent'
            })

        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@app.route('/api/balance', methods=['GET'])
@require_api_key
def get_balance():
    return jsonify({
        'balance': 100,
        'currency': 'ETB',
        'messages_left': 100
    })


@app.route('/api/message/<message_id>/status', methods=['GET'])
@require_api_key
def get_message_status(message_id):
    message = messages_db.get(message_id)

    if not message:
        return jsonify({
            'status': 'not_found',
            'message_id': message_id
        }), 404

    return jsonify({
        'status': message['status'],
        'message_id': message_id,
        'timestamp': message['timestamp']
    })


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'android-sms-gateway',
        'version': '1.0.0'
    })


@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'service': 'Android SMS Gateway',
        'version': '1.0.0',
        'endpoints': {
            'send_sms': 'POST /api/send-sms',
            'balance': 'GET /api/balance',
            'message_status': 'GET /api/message/{id}/status',
            'health': 'GET /health'
        }
    })


if __name__ == '__main__':
    logger.info(f"Starting Android SMS Gateway on {HOST}:{PORT}")
    logger.info(f"API Key required: {bool(API_KEY)}")

    try:
        app.run(host=HOST, port=PORT, debug=False)
    except KeyboardInterrupt:
        logger.info("Server stopped")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise