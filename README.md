# Digital Signage Middleware

Dieses Projekt ist eine Middleware für Digital Signage, die als FastAPI-Anwendung implementiert ist und Notion als Datenquelle nutzt.

## Voraussetzungen

- Ein Proxmox Container (LXC) oder eine VM (Debian/Ubuntu empfohlen).
- `git` und `curl` sollten installiert sein (werden aber auch vom Setup-Script geprüft).

## Installation auf Proxmox

1.  Verbinde dich per SSH mit deinem Proxmox-Container.
2.  Klone dieses Repository in den gewünschten Ordner (z.B. `/opt/werbung`):
    ```bash
    cd /opt
    git clone <DEIN_REPO_URL> werbung
    cd werbung
    ```
3.  Führe das Setup-Script aus:
    ```bash
    chmod +x setup.sh
    ./setup.sh
    ```
    Das Script wird dich nach deinen Konfigurationsdaten (Notion Token, Database ID) fragen und die `.env` Datei automatisch für dich erstellen.

Das Setup-Script wird außerdem:
- Das System aktualisieren.
- Docker und Docker Compose installieren (falls nicht vorhanden).
- Den `update`-Befehl systemweit einrichten.
- Die Anwendung starten.

## Nutzung des Update-Befehls

Nach der erfolgreichen Installation kannst du jederzeit per SSH den Befehl `update` eingeben, um die Anwendung zu aktualisieren:

```bash
update
```

Dieser Befehl führt folgende Schritte aus:
1.  Zieht die neuesten Änderungen von Git (`git pull`).
2.  Stoppt die alten Container (`docker compose down`).
3.  Baut die Container neu und startet sie (`docker compose up -d --build`).
4.  Bereinigt nicht mehr benötigte Docker-Images (`docker image prune`).

## Konfiguration

Die Konfiguration erfolgt über Umgebungsvariablen in der `.env` Datei oder direkt in der `docker-compose.yml`.

| Variable | Beschreibung |
| :--- | :--- |
| `NOTION_TOKEN` | Dein Notion Integration Token |
| `NOTION_DATABASE_ID` | Die ID der Notion Datenbank |
| `SYNC_INTERVAL` | Intervall für die Synchronisation in Sekunden |

## Notion Datenbank Struktur

Damit die Anwendung die Inhalte korrekt aus Notion lesen kann, muss die Datenbank folgende Spalten (Properties) enthalten. Die Namen müssen exakt übereinstimmen (Groß-/Kleinschreibung beachten!):

| Spaltenname | Typ | Beschreibung |
| :--- | :--- | :--- |
| **Name** | `Title` | Der Name des Beitrags (wird als Titel angezeigt). |
| **Media** | `Files & Media` | Hier muss das Bild oder Video hochgeladen werden (nur die erste Datei wird verwendet). |
| **Active** | `Checkbox` | Wenn angehakt, wird der Inhalt angezeigt. Zum Pausieren einfach Haken entfernen. |
| **Start** | `Date` | Datumsfeld. Kann einen Start- und optional einen Endzeitpunkt haben. <br> - **Nur Start**: Aktiv ab diesem Zeitpunkt. <br> - **Start & Ende**: Aktiv nur in diesem Zeitraum. <br> - **Leer**: Immer aktiv (wenn `Active` angehakt). |
| **Duration** | `Number` | Anzeigedauer in Sekunden (Standard: 10). |
| **Description** | `Text` | (Optional) Zusätzliche Beschreibung. |

### Hinweise zu Medien
- Unterstützte Bildformate: `.jpg`, `.png`, etc.
- Unterstützte Videoformate: `.mp4`, `.mov`, `.webm`
- Videos werden automatisch erkannt und die Anzeigedauer wird ignoriert (Video spielt einmal komplett).
