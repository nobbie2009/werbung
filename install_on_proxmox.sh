#!/bin/bash

# Farben
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=== Digital Signage Middleware - Proxmox Installer ===${NC}"
echo "Dieses Script erstellt einen neuen LXC Container und installiert die Anwendung."

# Checks
if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}Bitte als root ausführen${NC}"
  exit 1
fi

if ! command -v pct &> /dev/null; then
    echo -e "${RED}Befehl 'pct' nicht gefunden. Bist du auf dem Proxmox Host?${NC}"
    exit 1
fi

# Eingaben
read -p "Container ID (z.B. 100): " CT_ID
while pct config $CT_ID &> /dev/null; do
    echo -e "${RED}Container ID $CT_ID existiert bereits.${NC}"
    read -p "Bitte andere ID wählen: " CT_ID
done

read -p "Hostname (z.B. digital-signage): " HOSTNAME
read -s -p "Password für Container root: " PASSWORD
echo ""
read -p "Storage Name (Standard: local-lvm): " STORAGE
STORAGE=${STORAGE:-local-lvm}

read -p "Bridge Interface (Standard: vmbr0): " BRIDGE
BRIDGE=${BRIDGE:-vmbr0}

read -p "Template (Standard: debian-12-standard_12.2-1_amd64.tar.zst): " TEMPLATE
# Versuche Standard-Template zu finden, falls leer
if [ -z "$TEMPLATE" ]; then
    # Liste verfügbare Templates auf und nimm das erste Debian 12
    DETECTED=$(pveam available | grep debian-12 | head -n 1 | awk '{print $2}')
    if [ -z "$DETECTED" ]; then
        echo -e "${RED}Kein Debian 12 Template gefunden. Bitte lade eines herunter (pveam download local debian-12-...) oder gib den Pfad manuell an.${NC}"
        read -p "Template Pfad: " TEMPLATE
    else
        echo -e "${GREEN}Verwende Template: $DETECTED${NC}"
        # Wenn es nicht lokal ist, downloaden
        if ! pveam list local | grep -q "$DETECTED"; then
            echo "Lade Template herunter..."
            pveam download local $DETECTED
        fi
        TEMPLATE="local:vztmpl/$(basename $DETECTED)"
    fi
fi

# Container erstellen
echo -e "${GREEN}Erstelle Container $CT_ID...${NC}"
pct create $CT_ID $TEMPLATE \
    --hostname $HOSTNAME \
    --password $PASSWORD \
    --rootfs $STORAGE:4 \
    --net0 name=eth0,bridge=$BRIDGE,ip=dhcp,type=veth \
    --features nesting=1,keyctl=1 \
    --onboot 1 \
    --unprivileged 1

if [ $? -ne 0 ]; then
    echo -e "${RED}Fehler beim Erstellen des Containers.${NC}"
    exit 1
fi

# Container starten
echo -e "${GREEN}Starte Container...${NC}"
pct start $CT_ID
sleep 10 # Warten bis Netzwerk da ist

# Git installieren im Container
echo -e "${GREEN}Bereite Container vor...${NC}"
pct exec $CT_ID -- apt-get update
pct exec $CT_ID -- apt-get install -y git curl

# Repo klonen
REPO_URL="https://github.com/nobbie2009/werbung.git"

echo -e "${BLUE}Wie soll der Code in den Container gelangen?${NC}"
echo "1) Git Clone (Github: nobbie2009/werbung)"
echo "2) Lokales Verzeichnis kopieren (wenn Script im Projekt-Ordner liegt)"
read -p "Auswahl [1]: " SOURCE_OPT
SOURCE_OPT=${SOURCE_OPT:-1}

TARGET_DIR="/opt/werbung"

if [ "$SOURCE_OPT" == "2" ]; then
    echo -e "${GREEN}Kopiere Dateien...${NC}"
    pct exec $CT_ID -- mkdir -p $TARGET_DIR
    tar -cf - . | pct exec $CT_ID -- tar -xf - -C $TARGET_DIR
else
    echo -e "${GREEN}Klone Repository...${NC}"
    read -p "Git URL (Standard: https://github.com/nobbie2009/werbung.git): " REPO_URL
    REPO_URL=${REPO_URL:-https://github.com/nobbie2009/werbung.git}
    
    # Check if repo exists/clones correctly
    pct exec $CT_ID -- git clone $REPO_URL $TARGET_DIR
    if [ $? -ne 0 ]; then
        echo -e "${RED}Fehler beim Klonen des Repositories!${NC}"
        echo -e "${RED}Bitte stelle sicher, dass das Repo existiert und öffentlich ist.${NC}"
        exit 1
    fi
fi

# Setup ausführen
echo -e "${GREEN}Führe Setup im Container aus...${NC}"

# Config abfragen
echo -e "${BLUE}=== App Konfiguration ===${NC}"
read -p "Notion Token: " NOTION_TOKEN
read -p "Notion Database ID: " NOTION_DATABASE_ID
SYNC_INTERVAL=300

# .env schreiben
pct exec $CT_ID -- bash -c "echo 'NOTION_TOKEN=$NOTION_TOKEN' > $TARGET_DIR/.env"
pct exec $CT_ID -- bash -c "echo 'NOTION_DATABASE_ID=$NOTION_DATABASE_ID' >> $TARGET_DIR/.env"
pct exec $CT_ID -- bash -c "echo 'SYNC_INTERVAL=$SYNC_INTERVAL' >> $TARGET_DIR/.env"

# Startsetup
pct exec $CT_ID -- chmod +x $TARGET_DIR/setup.sh
pct exec $CT_ID -- bash -c "if [ -f $TARGET_DIR/setup.sh ]; then cd $TARGET_DIR && ./setup.sh; else echo 'setup.sh nicht gefunden!'; exit 1; fi"

if [ $? -ne 0 ]; then
    echo -e "${RED}Fehler bei der Installation (setup.sh).${NC}"
    echo -e "Bitte logge dich in den Container ein und prüfe die Logs: pct enter $CT_ID"
    exit 1
fi

# IP ermitteln
IP=$(pct exec $CT_ID -- hostname -I | awk '{print $1}')

echo -e "${GREEN}=== Installation Erfolgreich! ===${NC}"
echo -e "Digital Signage läuft im Container $CT_ID"
echo -e "Webinterface: http://$IP:8000"
echo -e "Admin Panel:  http://$IP:8000/admin"
echo -e ""
echo -e "Logge dich ein mit: pct enter $CT_ID"
