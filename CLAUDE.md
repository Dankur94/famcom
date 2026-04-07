# HeartSync — Emotional Sharing for Couples

## Projektbeschreibung
WhatsApp-basiertes Ehepaar-Emotional-Sharing-Tool. Daniel + Babe tracken Verletzungen (Hurt) und Freude-Momente (SmileJar). Taeglich 22:00 persoenliche Reports.

## Architektur
- **Frontend:** WhatsApp-Gruppe "HeartSync" (Baileys v7 Bridge, Node.js)
- **Backend:** Python FastAPI, SQLite, APScheduler
- **Design:** Modulares Plugin-System — jedes Feature = ein Ordner, an/aus via config.yaml
- **Routing:** Bot reagiert auf Regex-Trigger. Bei keinem Match: AI Fallback (DeepSeek). Normale Gespraeche werden ignoriert.

## Deployment
- **VM:** AWS t3.micro, IP `13.60.99.119`, User: `ubuntu`
- **SSH:** `ssh -i ~/Downloads/family-hub-key.pem ubuntu@13.60.99.119`
- **Services:** `heartsync-bridge.service` (Port 3002) + `heartsync.service` (Port 8001)
- **Pfad auf VM:** `/home/ubuntu/heartsync/`

## Deploy-Workflow (Git-based)
```bash
bash deploy.sh
```
WICHTIG: config.yaml ist in .gitignore — lebt NUR auf der VM mit echten Credentials.

## Module (5 aktiv)

| Modul | Trigger | Beschreibung |
|---|---|---|
| hurt | `hurt`, `ouch`, `aua`, `autsch`, `verletzt` + Nachricht | Verletzung loggen (Nachricht Pflicht) |
| smile | `smile`, `laugh`, `haha`, `lol`, `gelacht`, etc. | Freude-Moment zaehlen (+opt. Nachricht) |
| reports | `report`, `today`, `status` + 22:00 auto | Persoenlicher Daily Report |
| help | `help`, `?`, `hilfe` | Befehlsuebersicht |
| delete | `undo`, `delete hurt/smile HH:MM` | Eigene Eintraege loeschen |

## Datenbank-Tabellen
- `ouch_entries` — Verletzungen (logged_by, about_user, message, timestamp)
- `smiles` — Freude-Momente (logged_by, message, timestamp)

## Projektstruktur
```
HeartSync/
├── server.py              # FastAPI App, Message-Routing, AI Fallback
├── registry.py            # Module-Registry, load/route
├── database.py            # SQLite Layer (ouch_entries + smiles)
├── voice.py               # VoiceProcessor (Groq STT + DeepSeek normalize)
├── whatsapp.py            # WhatsApp Client (HTTP zu Bridge)
├── config.yaml            # Module an/aus, Credentials
├── modules/
│   ├── base.py            # BaseModule, Message, Response, ScheduledJob
│   ├── ouch/              # Hurt — Verletzungen loggen
│   ├── smile/             # SmileJar — Freude zaehlen
│   ├── reports/           # Persoenliche Daily Reports (22:00)
│   ├── help/              # Befehlsuebersicht
│   └── delete/            # Undo + gezieltes Loeschen
└── whatsapp-bridge/
    ├── bridge.js          # Baileys v7 Bridge, Port 3002
    └── package.json
```

## Kritische Regeln
- **Baileys v7**: Import ist `require('baileys')` NICHT `@whiskeysockets/baileys`
- **config.yaml Credentials**: Nie blind ueberschreiben! VM hat echte Credentials, lokal Platzhalter.
- **WhatsApp Gruppe**: "HeartSync"
- **Ports**: Backend 8001, Bridge 3002
- **Members**: Nur Daniel + Babe (kein Gerold)
