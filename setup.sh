#!/bin/bash

# Farben für Output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Initiales Setup Script ===${NC}"

# Überprüfen ob root
if [ "$EUID" -ne 0 ]; then 
  echo "Bitte als root ausführen"
  exit 1
fi

# 1. System Update
echo -e "${GREEN}Aktualisiere Systempakete...${NC}"
apt update && apt upgrade -y

# 2. Abhängigkeiten installieren
echo -e "${GREEN}Installiere Abhängigkeiten...${NC}"
apt install -y curl git ca-certificates gnupg

# 2.1 Konfiguration abfragen (falls .env nicht existiert)
if [ ! -f .env ]; then
    echo -e "${BLUE}=== Konfiguration ===${NC}"
    echo "Die .env Datei wurde nicht gefunden. Wir erstellen sie jetzt."
    
    read -p "Bitte gib dein NOTION_TOKEN ein: " NOTION_TOKEN
    read -p "Bitte gib deine NOTION_DATABASE_ID ein: " NOTION_DATABASE_ID
    read -p "Bitte gib das SYNC_INTERVAL ein (Standard: 300): " SYNC_INTERVAL
    
    # Standardwert setzen falls leer
    if [ -z "$SYNC_INTERVAL" ]; then
        SYNC_INTERVAL=300
    fi
    
    # .env Datei schreiben
    echo "NOTION_TOKEN=$NOTION_TOKEN" > .env
    echo "NOTION_DATABASE_ID=$NOTION_DATABASE_ID" >> .env
    echo "SYNC_INTERVAL=$SYNC_INTERVAL" >> .env
    
    echo -e "${GREEN}.env Datei wurde erstellt!${NC}"
else
    echo -e "${GREEN}.env Datei bereits vorhanden. Überspringe Konfiguration.${NC}"
fi

# 3. Docker installieren (falls nicht vorhanden)
if ! command -v docker &> /dev/null; then
    echo -e "${GREEN}Docker wird installiert...${NC}"
    # Offizielles Docker Installations-Script
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
else
    echo -e "${GREEN}Docker ist bereits installiert.${NC}"
fi

# 4. Update-Script ausführbar machen und global verlinken
echo -e "${GREEN}Konfiguriere 'update' Befehl...${NC}"
chmod +x update_app.sh

# Pfad zum aktuellen Verzeichnis
CURRENT_DIR=$(pwd)
UPDATE_SCRIPT="$CURRENT_DIR/update_app.sh"
LINK_path="/usr/local/bin/update"

if [ -f "$LINK_path" ]; then
    rm "$LINK_path"
fi

# Wrapper Script erstellen, das in das richtige Verzeichnis wechselt
echo "#!/bin/bash
cd $CURRENT_DIR
./update_app.sh" > $LINK_path

chmod +x $LINK_path

echo -e "${GREEN}'update' Befehl wurde erstellt. Du kannst nun einfach 'update' eingeben.${NC}"

# 5. Erster Start
echo -e "${GREEN}Starte Anwendung zum ersten Mal...${NC}"
docker compose up -d

echo -e "${BLUE}=== Setup abgeschlossen ===${NC}"
echo -e "Die Anwendung läuft nun."
echo -e "Verwende 'update' um zukünftige Updates einzuspielen."
