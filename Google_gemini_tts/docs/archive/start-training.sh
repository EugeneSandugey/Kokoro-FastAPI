#!/bin/bash
#
# Start HD Transfers Sales Training Web Server
#

cd "$(dirname "$0")"

echo "=========================================="
echo "  HD Transfers Sales Training Server"
echo "=========================================="
echo

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Start the server
echo
echo "🚀 Starting web server..."
echo "   Local:  http://127.0.0.1:5180"
echo "   Public: https://hdtransfers-training.eugenes.ai (after tunnel setup)"
echo
echo "Press Ctrl+C to stop"
echo

python3 web_server.py
