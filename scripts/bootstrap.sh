sudo apt update
sudo apt full-upgrade -y
# Might not be needed.
# sudo apt install python3-picamera2 python3-opencv -y

libcamera-hello --list-cameras

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

echo "Setting up SSH keys..."
ssh-keygen -t ed25519 -C "rasppi"
cat ~/.ssh/id_ed25519.pub

echo "Visit https://github.com/settings/keys and copy the key above."