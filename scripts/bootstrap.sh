sudo apt update
sudo apt full-upgrade -y
# Might not be needed.
# sudo apt install python3-picamera2 python3-opencv -y

libcamera-hello --list-cameras
sudo apt install python3-picamera2 --no-install-recommends

pip3 install -r requirements.txt --break-system-packages

echo "Setting up SSH keys..."
ssh-keygen -t ed25519 -C "rasppi"
cat ~/.ssh/id_ed25519.pub

echo "Visit https://github.com/settings/keys and copy the key above."