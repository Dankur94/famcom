# FamCom — Family Contributions Tracker

## Projektbeschreibung
WhatsApp-basierter Family-Contributions-Tracker. Drei Familienmitglieder (Daniel, Frau, Vater) tracken Ausgaben, Zeitinvestments, und zeigen Wertschaetzung. Plus: AI-powered Reminder Builder.

## Architektur
- **Frontend:** WhatsApp-Gruppe "FamCom" (Baileys v7 Bridge, Node.js)
- **Backend:** Python FastAPI, SQLite, APScheduler
- **Design:** Modulares Plugin-System — jedes Feature = ein Ordner, an/aus via config.yaml
- **Routing:** Bot reagiert auf Regex-Trigger. Bei keinem Match: AI Fallback (DeepSeek) fuer natuerliche Saetze. Normale Gespraeche werden ignoriert.
- **Waehrung:** HKD (Hong Kong Dollar)

## Deployment
- **VM:** AWS t3.micro, IP `13.60.99.119`, User: `ubuntu`
- **SSH:** `ssh -i ~/Downloads/family-hub-key.pem ubuntu@13.60.99.119`
- **Services:** `famcom-bridge.service` (Port 3002) + `famcom.service` (Port 8001)
- **Pfad auf VM:** `/home/ubuntu/famcom/`
- **Timezone:** Asia/Hong_Kong (HKT, UTC+8)

## Deploy-Workflow (Git-based)
```bash
# Lokal editieren, committen, dann:
bash deploy.sh
```
Das Script macht automatisch: git push → VM pullt von GitHub → Service restart → Health-Check.

**Rollback:** `ssh -i ~/Downloads/family-hub-key.pem ubuntu@13.60.99.119 'cd /home/ubuntu/famcom && git reset --hard HEAD~1 && sudo systemctl restart famcom.service'`

WICHTIG: config.yaml ist in .gitignore — lebt NUR auf der VM mit echten Credentials. Lokal hat sie Platzhalter.

## Module (7 aktiv)

| Modul | Trigger | Status |
|---|---|---|
| expense | `$50 groceries`, `expense 150 taxi` | LIVE |
| time_log | `2h cooking`, `30min cleaning` | LIVE |
| thanks | `thanks papa for shopping`, `danke [name] [reason]` | LIVE |
| reports | `report`, `weekly`, `monthly`, `today` + Sonntag 20:00 auto | LIVE |
| reminders | `remind 15:00 call doctor`, `remind me in 2h ...`, `reminders` | LIVE |
| help | `help`, `?`, `commands` | LIVE |
| delete | `undo`, `delete expense/time/thanks HH:MM` | LIVE |

## Deploy-Checkliste (jedes neue Modul)
1. [ ] `modules/{name}/module.py` erstellt (implementiert can_handle, handle, get_scheduled_jobs)
2. [ ] `VOICE_INFO` definiert (command + examples) — AI-Prompt baut sich automatisch
3. [ ] `server.py` — Import + `register_module()` hinzugefuegt
4. [ ] `config.yaml` — Modul mit `enabled: true` hinzugefuegt
5. [ ] `database.py` — Tabelle + Methoden hinzugefuegt (falls noetig)
6. [ ] `modules/help/module.py` — HELP_TEXT aktualisiert
7. [ ] Service neu gestartet: `sudo systemctl restart famcom.service`
8. [ ] Health-Check: `curl -s localhost:8001/health` — alle Module geladen?

## Projektstruktur
```
FamCom/
├── server.py              # FastAPI App, Port 8001, Module-Imports, Message-Routing
├── registry.py            # Module-Registry, load/route
├── database.py            # SQLite Layer (4 Tabellen: expenses, time_entries, thanks, reminders)
├── voice.py               # VoiceProcessor (Groq STT + DeepSeek normalize)
├── whatsapp.py            # WhatsApp Client (HTTP zu Bridge, Port 3002)
├── config.yaml            # Module an/aus, Parameter, Credentials
├── modules/
│   ├── base.py            # BaseModule, Message, Response, ScheduledJob
│   ├── expense/           # Ausgaben-Tracking (HKD)
│   ├── time_log/          # Zeit-Investment-Tracking
│   ├── thanks/            # Kudos / Wertschaetzung
│   ├── reports/           # Weekly/Monthly per-person Breakdown
│   ├── reminders/         # DB-backed Reminders
│   ├── help/              # Befehlsuebersicht
│   └── delete/            # Undo + gezieltes Loeschen
└── whatsapp-bridge/
    ├── bridge.js          # Baileys v7 Bridge, Port 3002
    ├── package.json
    └── wa-session/        # WhatsApp Auth (NICHT committen!)
```

## Kritische Regeln
- **Baileys v7**: Import ist `require('baileys')` NICHT `@whiskeysockets/baileys`
- **fromMe-Fix**: Linked Device sieht eigene Nachrichten als fromMe. Bridge trackt sentMessageIds.
- **config.yaml Credentials**: Nie blind ueberschreiben! VM hat echte Credentials, lokal Platzhalter.
- **WhatsApp Gruppe**: "FamCom" (eigene Gruppe, nicht Family Hub!)
- **Ports**: Backend 8001, Bridge 3002 (FamilyHub nutzt 8000/3001)

## Datenbank-Tabellen
expenses, time_entries, thanks, reminders

## AI Integration
1. **Voice Notes** → Groq Whisper STT + DeepSeek Normalize
2. **Text Fallback** → `might_be_command()` Vorfilter + DeepSeek Normalize
3. **Kategorie-Erkennung** → Keyword-Map (kostenlos, instant) — KEIN AI pro Expense
4. **Reminder-Parsing** → Regex fuer HH:MM, "in Xh", "tomorrow HH:MM"
5. **VOICE_INFO** in jedem Modul → dynamischer AI-Prompt
