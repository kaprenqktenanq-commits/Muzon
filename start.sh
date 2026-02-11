#!/bin/bash
# ArmedMusic Bot startup script

set -e

echo "🎵 ArmedMusic Bot - Startup Script"
echo "=================================="

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $python_version detected"

# Check if requirements are installed
echo ""
echo "Checking dependencies..."
pip install -q -r requirements.txt || {
    echo "✗ Failed to install dependencies"
    exit 1
}
echo "✓ Dependencies installed"

# Verify critical packages
echo ""
echo "Verifying critical packages..."
python3 -c "import pyrogram; print(f'✓ Pyrogram {pyrogram.__version__}')" || exit 1
python3 -c "import pytgcalls; print('✓ PyTgCalls installed')" || exit 1
python3 -c "import motor; print('✓ Motor installed')" || exit 1

# Check environment variables
echo ""
echo "Checking environment variables..."
if [ -z "$API_ID" ]; then
    echo "✗ API_ID not set"
    exit 1
fi
if [ -z "$API_HASH" ]; then
    echo "✗ API_HASH not set"
    exit 1
fi
if [ -z "$BOT_TOKEN" ]; then
    echo "✗ BOT_TOKEN not set"
    exit 1
fi
echo "✓ Required environment variables set"

# Start the bot
echo ""
echo "Starting ArmedMusic Bot..."
echo "=================================="
python3 -m ArmedMusic
