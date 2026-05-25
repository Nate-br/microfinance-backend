#!/bin/bash
# SMS Gateway Setup Script for Termux
# Run this once to set up the SMS gateway

echo "========================================"
echo "  SMS Gateway Setup"
echo "========================================"
echo ""

# Update package list
echo "[1/6] Updating packages..."
pkg update && pkg upgrade -y

# Install Python and Flask
echo "[2/6] Installing Python and dependencies..."
pkg install python -y
pip install flask requests

# Create gateway directory
echo "[3/6] Creating gateway directory..."
mkdir -p ~/gateway
cd ~/gateway

# Create database directory
mkdir -p /data/data/com.termux/files/home/gateway

# Request SMS permission
echo "[4/6] Setting up SMS permission..."
echo "Please grant SMS permission when prompted:"
termux-setup-sms

# Wait for permission
sleep 3

# Create database
echo "[5/6] Creating database..."
python3 << 'EOF'
import sqlite3
import os

DB_PATH = '/data/data/com.termux/files/home/gateway/sms_log.db'

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

print("Database created successfully!")
EOF

echo "[6/6] Setup complete!"
echo ""

echo "========================================"
echo "  NEXT STEPS"
echo "========================================"
echo ""
echo "1. Copy server.py to ~/gateway/"
echo "2. Get your phone's IP address:"
echo "   ip addr show wlan0 | grep inet"
echo ""
echo "3. Start the server:"
echo "   cd ~/gateway"
echo "   python server.py"
echo ""
echo "4. Test the server:"
echo "   curl -X POST http://localhost:9000/send \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"phone\": \"+251912345678\", \"message\": \"Test SMS\"}'"
echo ""
echo "========================================"