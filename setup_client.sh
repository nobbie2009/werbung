#!/bin/bash

# Digital Signage Client Setup for Raspberry Pi OS (Triixie/Bookworm)
# This script configures the Pi as a Kiosk connecting to the Digital Signage Server.

USER_HOME=$(eval echo ~${SUDO_USER})
AUTOSTART_DIR="$USER_HOME/.config/autostart"
KIOSK_SCRIPT="$USER_HOME/kiosk.sh"

echo "-----------------------------------------------------"
echo "  Digital Signage Client Setup (Raspberry Pi)"
echo "-----------------------------------------------------"

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./setup_client.sh)"
  exit 1
fi

# 1. Prompt for Server Address
read -p "Enter the IP Address (or Hostname) of the Server [e.g. 192.168.1.100]: " SERVER_IP
read -p "Enter the Port [Default: 8000]: " SERVER_PORT
SERVER_PORT=${SERVER_PORT:-8000}
TARGET_URL="http://${SERVER_IP}:${SERVER_PORT}"

echo ">> Target URL set to: $TARGET_URL"

# 2. Update System & Install Dependencies
echo ">> Updating System (this may take a while)..."
apt-get update
# apt-get upgrade -y # Optional: skipped for speed, user can do manually if desired

echo ">> Installing Chromium and Unclutter..."
apt-get install -y chromium-browser unclutter

# 3. Create Kiosk Watchdog Script
echo ">> Creating Startup Script ($KIOSK_SCRIPT)..."

cat <<EOF > "$KIOSK_SCRIPT"
#!/bin/bash

# Hide mouse cursor when idle
unclutter -idle 0.1 -root &

# Disable power saving (Display Power Management Signaling)
xset s noblank
xset s off
xset -dpms

# Wayland compatibility tweaks (if needed)
export WIGGLE_WAYLAND=1 

# Cleanup
sed -i 's/"exited_cleanly":false/"exited_cleanly":true/' ~/.config/chromium/Default/Preferences
sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/' ~/.config/chromium/Default/Preferences

# Kiosk Loop (Watchdog)
while true; do
  echo "Starting Chromium Kiosk..."
  chromium-browser \\
    --noerrdialogs \\
    --disable-infobars \\
    --kiosk \\
    --test-type \\
    --check-for-update-interval=31536000 \\
    "$TARGET_URL"
  
  echo "Chromium crashed or closed. Restarting in 2 seconds..."
  sleep 2
done
EOF

chmod +x "$KIOSK_SCRIPT"
chown $SUDO_USER:$SUDO_USER "$KIOSK_SCRIPT"

# 4. Configure Autostart (Works for X11 and some Wayland setups via XDG Autostart)
echo ">> Configuring Autostart..."
mkdir -p "$AUTOSTART_DIR"
chown $SUDO_USER:$SUDO_USER "$USER_HOME/.config" "$AUTOSTART_DIR"

cat <<EOF > "$AUTOSTART_DIR/kiosk.desktop"
[Desktop Entry]
Type=Application
Name=Kiosk
Exec=$KIOSK_SCRIPT
X-GNOME-Autostart-enabled=true
EOF

chown $SUDO_USER:$SUDO_USER "$AUTOSTART_DIR/kiosk.desktop"

# 5. Setup Nightly Reboot (Cron)
echo ">> Setting up Nightly Reboot at 01:00 AM..."
CRON_JOB="0 1 * * * /sbin/shutdown -r now"

# Check if job already exists to avoid duplicates
crontab -u root -l 2>/dev/null | grep -F "$CRON_JOB" >/dev/null
if [ $? -ne 0 ]; then
    (crontab -u root -l 2>/dev/null; echo "$CRON_JOB") | crontab -u root -
    echo "   Cron job added."
else
    echo "   Cron job already exists."
fi

echo "-----------------------------------------------------"
echo "Setup Complete!"
echo "1. Ensure this Pi is set to 'Boot to Desktop (Auto Login)' via raspi-config."
echo "2. Reboot now to start the Kiosk."
echo "-----------------------------------------------------"
read -p "Reboot now? (y/n): " DO_REBOOT
if [[ "$DO_REBOOT" =~ ^[Yy]$ ]]; then
    reboot
fi
