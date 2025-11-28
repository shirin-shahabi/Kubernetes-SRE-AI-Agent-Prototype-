#!/bin/bash
# Fix Docker credential helper issue on macOS

echo "🔧 Fixing Docker credential helper..."

# Check if Docker config exists
CONFIG_FILE="$HOME/.docker/config.json"

if [ -f "$CONFIG_FILE" ]; then
    # Backup existing config
    cp "$CONFIG_FILE" "$CONFIG_FILE.backup"
    echo "✅ Backed up existing config to $CONFIG_FILE.backup"
    
    # Remove credential helper if it exists
    if grep -q "credsStore" "$CONFIG_FILE"; then
        # Use Python to properly edit JSON
        python3 << EOF
import json
import os

config_path = os.path.expanduser("$CONFIG_FILE")
with open(config_path, 'r') as f:
    config = json.load(f)

# Remove credsStore if it exists
if 'credsStore' in config:
    del config['credsStore']
    print("Removed credsStore")

# Remove credHelpers if it exists
if 'credHelpers' in config:
    del config['credHelpers']
    print("Removed credHelpers")

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print("✅ Updated Docker config")
EOF
    else
        echo "ℹ️  No credential helper found in config"
    fi
else
    # Create minimal config
    mkdir -p ~/.docker
    echo '{}' > "$CONFIG_FILE"
    echo "✅ Created Docker config file"
fi

echo ""
echo "✅ Docker credential helper fixed!"
echo "Try running: docker-compose up -d"

