# Android SMS Gateway Setup

## Overview

This is a Flask server that runs on your Android phone using Termux. It receives HTTP requests from your Django backend and sends SMS messages using your phone's SIM card.

## Requirements

- Android phone with Termux installed
- Ethiopian SIM card (for sending SMS)
- Same WiFi network as your backend server

## Setup on Android Phone

### Step 1: Install Termux
Download from F-Droid (recommended) or Google Play

### Step 2: Grant SMS Permission
Open Termux and run:
```bash
termux-setup-sms
```
Grant permission when prompted.

### Step 3: Setup Script (One-time)
Copy `setup.sh` to your phone and run:
```bash
bash setup.sh
```

Or manually:
```bash
pkg update && pkg upgrade -y
pkg install python -y
pip install flask requests
mkdir -p ~/gateway
```

### Step 4: Get Your Phone's IP
```bash
ip addr show wlan0 | grep inet
```
Example output: `192.168.1.100`

### Step 5: Start the Server
```bash
cd ~/gateway
python server.py
```

You should see:
```
==================================================
  SMS Gateway Server
==================================================
  Make sure Termux SMS permission is granted:
  termux-setup-sms
==================================================

 * Serving Flask app 'server'
 * Running on http://0.0.0.0:9000
```

### Step 6: Test
On your computer (or Django server):
```bash
curl -X POST http://192.168.1.100:9000/send \
  -H "Content-Type: application/json" \
  -d '{"phone": "+251912345678", "message": "Test SMS from Gateway"}'
```

## Server Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/send` | POST | Send SMS |
| `/logs` | GET | View SMS logs |
| `/balance` | GET | Check SMS status |

## API Usage

### Send SMS
```bash
curl -X POST http://YOUR_PHONE_IP:9000/send \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+251912345678",
    "message": "Your OTP is 123456"
  }'
```

### Response
```json
{
  "success": true,
  "message": "SMS sent successfully",
  "phone": "+251912345678",
  "timestamp": "2024-01-15T10:30:00"
}
```

## Django Integration

In your `sms_service.py`:
```python
import requests

SMS_GATEWAY_URL = "http://192.168.1.100:9000/send"

def send_sms(phone, message):
    try:
        response = requests.post(
            SMS_GATEWAY_URL,
            json={"phone": phone, "message": message},
            timeout=30
        )
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}
```

## Troubleshooting

### "Permission denied" error
Make sure SMS permission is granted:
```bash
termux-setup-sms
```

### "Connection refused" error
- Check if server is running
- Check firewall settings
- Make sure phone and computer are on same WiFi

### SMS not sent
- Check SIM card balance
- Restart Termux
- Check logs: `curl http://YOUR_PHONE_IP:9000/logs`

## Security Note

This gateway is designed for local network use. For production:
- Add authentication to the endpoints
- Use HTTPS
- Restrict access by IP