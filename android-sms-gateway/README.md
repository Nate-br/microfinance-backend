# Android SMS Gateway Server

This is a simple Flask server that can be run on an Android phone (using Termux or similar) to act as an SMS Gateway for sending OTPs.

## Installation on Android (using Termux)

```bash
# Install Python and required packages
pkg update
pkg install python python-pip git

# Clone or copy this directory
git clone <repository-url>
cd android-sms-gateway

# Install dependencies
pip install -r requirements.txt

# Run the server
python server.py
```

## Running the Server

```bash
python server.py --port 8080 --host 0.0.0.0
```

The server will start on the specified port (default: 8080).

## API Endpoints

### POST /api/send-sms

Send an SMS message.

**Request:**
```json
{
  "phone": "+251912345678",
  "message": "Your verification code is 123456"
}
```

**Response:**
```json
{
  "success": true,
  "message_id": "abc123"
}
```

### GET /api/balance

Check account balance (simulated).

**Response:**
```json
{
  "balance": 100,
  "currency": "ETB"
}
```

### GET /api/message/{message_id}/status

Check message delivery status.

**Response:**
```json
{
  "status": "delivered",
  "message_id": "abc123",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Configuration

- Port: Default 8080
- Host: Default 0.0.0.0
- API Key: Optional (can be set via environment variable)

## Network Setup

For the Django backend to reach this server:

1. **Same Network (LAN):**
   - Find Android phone's local IP: `ifconfig` or `ip addr`
   - Use: `http://192.168.x.x:8080`

2. **Internet Access (requires port forwarding or ngrok):**
   - Use ngrok: `ngrok http 8080`
   - Or configure router port forwarding

## Docker Alternative

You can also run this as a Docker container:

```bash
docker build -t sms-gateway .
docker run -p 8080:8080 sms-gateway
```

## Security Notes

- In production, enable HTTPS
- Use API key authentication
- Implement rate limiting
- Log all SMS activities
- Secure the endpoint with firewall rules