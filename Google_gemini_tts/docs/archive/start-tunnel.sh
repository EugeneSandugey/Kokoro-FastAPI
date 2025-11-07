#!/bin/bash
#
# Start Cloudflare Tunnel for HD Transfers Sales Training
#

cd "$(dirname "$0")"

echo "=========================================="
echo "  Starting Cloudflare Tunnel"
echo "=========================================="
echo
echo "Public URL: https://hdtransfers-training.eugenes.ai"
echo "Local:      http://127.0.0.1:5180"
echo
echo "Press Ctrl+C to stop"
echo

cloudflared tunnel --config tunnel-config.yml run hdtransfers-training
