#!/bin/bash

# Check if --reset flag is provided
RESET_CSV=false
for arg in "$@"; do
    if [ "$arg" == "--reset" ]; then
        RESET_CSV=true
    fi
done

# If reset flag is provided, delete the existing block_time.csv file
if [ "$RESET_CSV" = true ]; then
    echo "Reset flag detected. Removing existing block_time.csv file..."
    if [ -f "block_time.csv" ]; then
        rm block_time.csv
        echo "Existing block_time.csv file has been deleted."
    else
        echo "No existing block_time.csv file found."
    fi
fi

# Check if layerd command is available
if command -v layerd &> /dev/null; then
    echo "Found layerd binary in path"
else
    echo "Warning: layerd binary not found in PATH. Make sure it's installed and accessible."
    echo "Please install layerd or add it to your PATH before running this script."
    echo "Continuing anyway, as the script will try to locate the binary..."
fi

# Ensure the RPC URL is set
if [ -z "$LAYER_RPC_URL" ]; then
    echo "Setting LAYER_RPC_URL to default value"
    export LAYER_RPC_URL="https://rpc.layer.exchange"
fi

# First test if the block time tracker works
echo "Testing block time tracking functionality..."
python -m layerbot track-block-time --test

# Check if the test was successful
if [ $? -ne 0 ]; then
    echo "Block time tracking test failed. Aborting."
    exit 1
fi

echo "Block time tracking test successful. Starting tracker..."

# Start the block time tracker in daemon mode
echo "Starting block time tracker in daemon mode..."
python -m layerbot track-block-time --daemon

# Wait a moment to allow the tracker to start
echo "Waiting for tracker to initialize..."
sleep 3

# Start the Flask web app
echo "Starting Flask web app..."
python app.py 