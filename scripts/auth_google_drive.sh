#!/bin/bash
# Convenience script to trigger Google Drive OAuth authentication in Docker
# This runs the token generation inside the container and prints the auth URL to your terminal

set -e

echo "========================================================================"
echo "🔐 Google Drive OAuth Authentication"
echo "========================================================================"
echo ""
echo "Starting OAuth flow inside Docker container..."
echo ""

docker exec -it bookgateway python scripts/generate_token.py --headless

echo ""
echo "========================================================================"
echo "✅ Authentication complete!"
echo "========================================================================"
echo ""
echo "The container will now automatically detect the token and continue."
echo "No need to restart the container."
echo ""
