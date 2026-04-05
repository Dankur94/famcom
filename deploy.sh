#!/bin/bash
# FamCom — Git-based Deploy Script
# Workflow: git push lokal → VM pullt von GitHub → Service restart → Health-Check

set -e

VM_HOST="ubuntu@13.60.99.119"
VM_PATH="/home/ubuntu/famcom/"
SSH_KEY="$HOME/Downloads/family-hub-key.pem"
HEALTH_URL="http://localhost:8001/health"
REPO_URL="github-famcom:Dankur94/famcom.git"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "==============================="
echo " FamCom — Git Deploy"
echo "==============================="
echo ""

# --- Step 1: Preflight checks ---
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}[FEHLER] SSH Key nicht gefunden: $SSH_KEY${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] SSH Key gefunden${NC}"

# Check for uncommitted changes
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo -e "${YELLOW}[WARNUNG] Es gibt uncommitted Changes:${NC}"
    git status --short
    echo ""
    read -p "Trotzdem deployen (nur committed Code wird deployed)? (y/N): " CONTINUE
    if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
        echo "Abbruch. Bitte erst committen."
        exit 1
    fi
fi

# Check if local is ahead of remote
LOCAL_HEAD=$(git rev-parse HEAD)
REMOTE_HEAD=$(git rev-parse origin/main 2>/dev/null || echo "unknown")

if [ "$LOCAL_HEAD" != "$REMOTE_HEAD" ]; then
    echo -e "${YELLOW}Lokale Commits noch nicht gepusht. Pushe jetzt...${NC}"
    git push origin main
    echo -e "${GREEN}[OK] Code gepusht${NC}"
else
    echo -e "${GREEN}[OK] GitHub ist aktuell${NC}"
fi

# --- Step 2: VM Setup (einmalig) oder Pull ---
echo ""
echo "Pruefe VM-Setup..."

VM_HAS_REPO=$(ssh -i "$SSH_KEY" "$VM_HOST" "test -d ${VM_PATH}.git && echo 'yes' || echo 'no'" 2>/dev/null)

if [ "$VM_HAS_REPO" = "no" ]; then
    echo -e "${YELLOW}VM hat noch kein Git-Repo. Richte ein...${NC}"

    # Backup existing config.yaml on VM
    ssh -i "$SSH_KEY" "$VM_HOST" "cp ${VM_PATH}config.yaml /tmp/famcom-config.yaml.bak 2>/dev/null || true"

    # Backup existing database
    ssh -i "$SSH_KEY" "$VM_HOST" "cp ${VM_PATH}famcom.db /tmp/famcom.db.bak 2>/dev/null || true"

    # Backup wa-session
    ssh -i "$SSH_KEY" "$VM_HOST" "cp -r ${VM_PATH}whatsapp-bridge/wa-session /tmp/famcom-wa-session.bak 2>/dev/null || true"

    # Remove old directory and clone fresh
    ssh -i "$SSH_KEY" "$VM_HOST" "rm -rf ${VM_PATH} && git clone ${REPO_URL} ${VM_PATH}"

    # Restore config, database, and wa-session
    ssh -i "$SSH_KEY" "$VM_HOST" "cp /tmp/famcom-config.yaml.bak ${VM_PATH}config.yaml 2>/dev/null || true"
    ssh -i "$SSH_KEY" "$VM_HOST" "cp /tmp/famcom.db.bak ${VM_PATH}famcom.db 2>/dev/null || true"
    ssh -i "$SSH_KEY" "$VM_HOST" "mkdir -p ${VM_PATH}whatsapp-bridge/wa-session && cp -r /tmp/famcom-wa-session.bak/* ${VM_PATH}whatsapp-bridge/wa-session/ 2>/dev/null || true"

    echo -e "${GREEN}[OK] VM Git-Repo eingerichtet + Daten wiederhergestellt${NC}"
else
    echo "Pulle neusten Code auf VM..."
    ssh -i "$SSH_KEY" "$VM_HOST" "cd ${VM_PATH} && git fetch origin && git reset --hard origin/main"
    echo -e "${GREEN}[OK] VM auf neustem Stand${NC}"
fi

# --- Step 3: Verify config.yaml on VM ---
echo ""
echo "Pruefe VM config.yaml..."
VM_HAS_CONFIG=$(ssh -i "$SSH_KEY" "$VM_HOST" "test -f ${VM_PATH}config.yaml && echo 'yes' || echo 'no'" 2>/dev/null)

if [ "$VM_HAS_CONFIG" = "no" ]; then
    echo -e "${RED}[FEHLER] config.yaml fehlt auf VM!${NC}"
    echo "  Die VM braucht eine config.yaml mit echten Credentials."
    echo "  Erstelle sie manuell: ssh -i $SSH_KEY $VM_HOST 'nano ${VM_PATH}config.yaml'"
    exit 1
fi

VM_HAS_PLACEHOLDERS=$(ssh -i "$SSH_KEY" "$VM_HOST" "grep -c 'YOUR_' ${VM_PATH}config.yaml" 2>/dev/null || echo "0")
if [ "$VM_HAS_PLACEHOLDERS" -gt 0 ]; then
    echo -e "${YELLOW}[WARNUNG] VM config.yaml hat $VM_HAS_PLACEHOLDERS Platzhalter${NC}"
else
    echo -e "${GREEN}[OK] VM config.yaml hat echte Credentials${NC}"
fi

# --- Step 4: Install dependencies ---
echo ""
echo "Pruefe Dependencies..."
ssh -i "$SSH_KEY" "$VM_HOST" "cd $VM_PATH && venv/bin/pip install -q -r requirements.txt 2>/dev/null" || true
ssh -i "$SSH_KEY" "$VM_HOST" "cd ${VM_PATH}whatsapp-bridge && npm install --production 2>/dev/null" || true
echo -e "${GREEN}[OK] Dependencies aktuell${NC}"

# --- Step 5: Restart services ---
echo ""
echo "Starte Services neu..."
ssh -i "$SSH_KEY" "$VM_HOST" "sudo systemctl restart famcom.service"
echo -e "${GREEN}[OK] famcom.service neu gestartet${NC}"

read -p "WhatsApp Bridge auch neu starten? (y/N): " RESTART_BRIDGE
if [ "$RESTART_BRIDGE" = "y" ] || [ "$RESTART_BRIDGE" = "Y" ]; then
    ssh -i "$SSH_KEY" "$VM_HOST" "sudo systemctl restart famcom-bridge.service"
    echo -e "${GREEN}[OK] famcom-bridge.service neu gestartet${NC}"
fi

# --- Step 6: Health-Check ---
echo ""
echo "Warte 3 Sekunden auf Startup..."
sleep 3

echo "Pruefe Health-Endpoint..."
HEALTH=$(ssh -i "$SSH_KEY" "$VM_HOST" "curl -s $HEALTH_URL" 2>/dev/null)

if echo "$HEALTH" | grep -q '"status":"running"'; then
    MODULE_COUNT=$(echo "$HEALTH" | grep -o '"modules":[0-9]*' | grep -o '[0-9]*')
    BRIDGE_STATUS=$(echo "$HEALTH" | grep -o '"whatsapp_bridge":"[^"]*"' | cut -d'"' -f4)
    echo -e "${GREEN}[OK] Health Check bestanden!${NC}"
    echo "  Module geladen: $MODULE_COUNT"
    echo "  WhatsApp Bridge: $BRIDGE_STATUS"

    # Show deployed commit
    DEPLOYED_COMMIT=$(ssh -i "$SSH_KEY" "$VM_HOST" "cd ${VM_PATH} && git log --oneline -1" 2>/dev/null)
    echo "  Deployed: $DEPLOYED_COMMIT"
else
    echo -e "${RED}[FEHLER] Health Check fehlgeschlagen!${NC}"
    echo "  Response: $HEALTH"
    echo ""
    echo "Logs pruefen:"
    echo "  ssh -i $SSH_KEY $VM_HOST 'journalctl -u famcom.service -n 50 --no-pager'"
    echo ""
    echo "Rollback zum vorherigen Commit:"
    echo "  ssh -i $SSH_KEY $VM_HOST 'cd ${VM_PATH} && git reset --hard HEAD~1'"
    exit 1
fi

echo ""
echo "==============================="
echo -e "${GREEN} Deploy erfolgreich! ${NC}"
echo "==============================="
echo ""
echo "  Workflow-Erinnerung:"
echo "  1. Lokal editieren + committen"
echo "  2. bash deploy.sh"
echo "  3. Rollback: ssh VM 'cd famcom && git reset --hard HEAD~1'"
echo ""
