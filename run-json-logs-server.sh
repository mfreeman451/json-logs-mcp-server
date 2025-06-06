#!/bin/bash
# Save as: /Users/mfreeman/src/nco-mcp/run-json-logs-server.sh
# Make executable: chmod +x run-json-logs-server.sh

# Change to the project directory
cd /Users/mfreeman/src/nco-mcp

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment .venv not found in $(pwd)" >&2
    echo "Please create it with: python3 -m venv .venv" >&2
    exit 1
fi

# Activate the virtual environment
source .venv/bin/activate

# Install/upgrade dependencies if needed (optional - comment out if not needed)
# pip install -e . --quiet

# Run the MCP server
exec python json_logs_mcp_server.py
