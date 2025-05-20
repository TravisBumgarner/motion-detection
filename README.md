# Motion Tracking with Raspberry Pi Camera Module 3

Flask server running on a Raspberry Pi, using the Camera Module 3 to track and serve motion data over time.

## Local Development

### Laptop

1. Append the following to ~/.ssh/config

```
Host raspberrypi
    HostName raspberrypi.local
    User travisbumgarner
    IdentitiesOnly yes
```

1. Copy ssh key to raspberry pi

``
ssh-keygen -t ed25519 -C "vscode pi login"
ssh-copy-id travisbumgarner@raspberrypi.local

```

1. Connect to Raspberry Pi
    - `ssh raspberrypi`

### Raspberry Pi

1. Bootstrap
   - Clone repo `git clone https://github.com/TravisBumgarner/motion-detection.git`
   - `make bootstrap-rasppi`
```
