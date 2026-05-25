"""
Android SMS Gateway Server
Run this on your Android phone using Termux
"""

from flask import Flask, request, jsonify
import subprocess
import sqlite3
import hashlib
import secrets
import time
from datetime import datetime, timedelta

app = Flask(__name__)
DB_PATH = '/data/data/com.termux/files/home/gateway/sms_log.db'

def init_db():
    """Initialize the SQLite database for SMS logging"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sms_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            message TEXT,
            status TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def log_sms(phone, message, status):
    """Log SMS attempts to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            'INSERT INTO sms_log (phone, message, status) VALUES (?, ?, ?)',
            (phone, message, status)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'SMS Gateway',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/send', methods=['POST'])
def send_sms():
    """
    Send SMS via termux-sms-send
    
    Request body:
    {
        "phone": "+251912345678",
        "message": "Your OTP is 123456"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        phone = data.get('phone')
        message = data.get('message')
        
        if not phone or not message:
            return jsonify({
                'success': False,
                'error': 'Missing phone or message'
            }), 400
        
        # Clean phone number
        phone = phone.replace(' ', '').replace('-', '')
        if not phone.startswith('+'):
            phone = '+' + phone
        
        # Send SMS using termux-sms-send
        result = subprocess.run(
            ['termux-sms-send', '-n', phone, message],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            log_sms(phone, message, 'sent')
            return jsonify({
                'success': True,
                'message': 'SMS sent successfully',
                'phone': phone,
                'timestamp': datetime.now().isoformat()
            })
        else:
            log_sms(phone, message, f'failed: {result.stderr}')
            return jsonify({
                'success': False,
                'error': result.stderr or 'Failed to send SMS'
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'SMS send timed out'
        }), 504
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    """Get recent SMS logs"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            'SELECT phone, message, status, sent_at FROM sms_log ORDER BY id DESC LIMIT 50'
        )
        rows = c.fetchall()
        conn.close()
        
        logs = []
        for row in rows:
            logs.append({
                'phone': row[0],
                'message': row[1],
                'status': row[2],
                'sent_at': row[3]
            })
        
        return jsonify({
            'success': True,
            'logs': logs
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/balance', methods=['GET'])
def get_balance():
    """Check SIM balance (Ethio Telecom)"""
    try:
        result = subprocess.run(
            ['termux-sms-list'],
            capture_output=True,
            text=True,
            timeout=10
        )
        sms_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        
        return jsonify({
            'success': True,
            'sms_in_queue': sms_count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    print("=" * 50)
    print("  SMS Gateway Server")
    print("=" * 50)
    print("  Make sure Termux SMS permission is granted:")
    print("  termux-setup-sms")
    print("=" * 50)
    print()
    
    # Run server
    app.run(
        host='0.0.0.0',
        port=9000,
        debug=False,
        threaded=True
    )