#!/bin/bash

set -e

SSH_CONFIG="$HOME/.ssh/config"
HOST_ENTRY="Host raspberrypi
    HostName raspberrypi.local
    User travisbumgarner
    IdentitiesOnly yes"

# Ensure ~/.ssh exists
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

# Create config file if it doesn't exist
touch "$SSH_CONFIG"
chmod 600 "$SSH_CONFIG"

# Add entry only if it doesn't already exist
if ! grep -q "Host raspberrypi" "$SSH_CONFIG"; then
    echo -e "\n$HOST_ENTRY" >> "$SSH_CONFIG"
    echo "Added SSH config entry for raspberrypi."
else
    echo "SSH config entry for raspberrypi already exists. Skipping."
fi

echo "Generating SSH key..."
ssh-keygen -t ed25519 -C "vscode pi login"

echo "Copying SSH key to Raspberry Pi..."
ssh-copy-id travisbumgarner@raspberrypi.local
