#!/bin/bash

# Farben für Output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starte Update-Prozess...${NC}"

# 1. Neueste Änderungen von Git ziehen
echo -e "${GREEN}Ziehe neueste Änderungen von Git...${NC}"
git pull

# 2. Container stoppen
echo -e "${GREEN}Stoppe Container...${NC}"
docker compose down

# 3. Container neu bauen und starten
echo -e "${GREEN}Baue und starte Container neu...${NC}"
docker compose up -d --build --remove-orphans

# 4. Aufräumen
echo -e "${GREEN}Bereinige alte Docker Images...${NC}"
docker image prune -f

echo -e "${GREEN}Update erfolgreich abgeschlossen!${NC}"
