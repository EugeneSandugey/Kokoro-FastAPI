#!/bin/bash
#
# Setup Cloudflare Tunnel for HD Transfers Sales Training
#

TUNNEL_NAME="hdtransfers-training"
HOSTNAME="hdtransfers-training.eugenes.ai"

echo "=========================================="
echo "  Cloudflare Tunnel Setup"
echo "=========================================="
echo
echo "Setting up tunnel: $TUNNEL_NAME"
echo "Public URL: https://$HOSTNAME"
echo

# Check if tunnel already exists
echo "🔍 Checking if tunnel exists..."
if cloudflared tunnel list | grep -q "$TUNNEL_NAME"; then
    echo "✅ Tunnel '$TUNNEL_NAME' already exists"
    TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
    echo "   Tunnel ID: $TUNNEL_ID"
else
    echo "📦 Creating new tunnel..."
    cloudflared tunnel create $TUNNEL_NAME
    TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
    echo "✅ Created tunnel: $TUNNEL_ID"
fi

# Create DNS route
echo
echo "🌐 Setting up DNS route..."
echo "   Running: cloudflared tunnel route dns $TUNNEL_ID $HOSTNAME"

if cloudflared tunnel route dns $TUNNEL_ID $HOSTNAME; then
    echo "✅ DNS route created"
else
    echo "⚠️  DNS route may already exist (this is OK)"
fi

echo
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo
echo "To start the tunnel, run:"
echo "  ./start-tunnel.sh"
echo
echo "Public URL: https://$HOSTNAME"
echo
