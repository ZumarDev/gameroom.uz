#!/bin/bash

# GameRoom.uz - Ishga tushirish scripti
# =====================================

# Ranglar
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════╗"
echo "║         🎮 GAMEROOM.UZ                   ║"
echo "║      O'yinxona Boshqaruv Tizimi          ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# Loyiha papkasiga o'tish
cd "$(dirname "$0")"
PROJECT_DIR=$(pwd)

echo -e "${YELLOW}📁 Loyiha papkasi: ${PROJECT_DIR}${NC}"

# .env faylini tekshirish
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚙️  .env fayli yaratilmoqda...${NC}"
    echo "SESSION_SECRET=$(openssl rand -hex 32)" > .env
    echo "SECRET_ADMIN_KEY=gameroom2026" >> .env
    echo -e "${GREEN}✅ .env fayli yaratildi${NC}"
else
    echo -e "${GREEN}✅ .env fayli mavjud${NC}"
fi

# Virtual muhitni tekshirish
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}🐍 Virtual muhit yaratilmoqda...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}✅ Virtual muhit yaratildi${NC}"
fi

# Virtual muhitni faollashtirish
echo -e "${YELLOW}🔄 Virtual muhit faollashtirilmoqda...${NC}"
source .venv/bin/activate

# Paketlarni o'rnatish
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}📦 Kerakli paketlar tekshirilmoqda...${NC}"
    pip install -q -r requirements.txt 2>/dev/null
    echo -e "${GREEN}✅ Paketlar o'rnatildi${NC}"
fi

# Eski jarayonlarni to'xtatish
echo -e "${YELLOW}🛑 Eski jarayonlar to'xtatilmoqda...${NC}"
pkill -f "python.*app.run" 2>/dev/null
fuser -k 3000/tcp 2>/dev/null
sleep 1

# Ma'lumotlar bazasini tekshirish
if [ ! -f "gaming_center.db" ]; then
    echo -e "${YELLOW}🗄️  Ma'lumotlar bazasi yaratilmoqda...${NC}"
    python3 -c "from app import app, db; app.app_context().push(); db.create_all()" 2>/dev/null
    echo -e "${GREEN}✅ Ma'lumotlar bazasi yaratildi${NC}"
else
    echo -e "${GREEN}✅ Ma'lumotlar bazasi mavjud${NC}"
fi

# Serverni ishga tushirish
echo ""
echo -e "${GREEN}🚀 Server ishga tushirilmoqda...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🌐 Brauzerda oching:${NC}"
echo -e "   ${YELLOW}➜ Local:   http://localhost:3000${NC}"
echo -e "   ${YELLOW}➜ Network: http://$(hostname -I | awk '{print $1}'):3000${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}To'xtatish: Ctrl+C${NC}"
echo ""

# Rejimni tanlash
MODE=${1:-dev}

if [ "$MODE" = "prod" ]; then
    echo -e "${GREEN}🏭 Production rejimida ishga tushirilmoqda (Gunicorn)...${NC}"
    pip install -q gunicorn 2>/dev/null
    gunicorn --bind 0.0.0.0:3000 --workers 4 --threads 2 app:app
else
    echo -e "${YELLOW}🔧 Development rejimida ishga tushirilmoqda...${NC}"
    python3 -c "from app import app; app.run(host='0.0.0.0', port=3000, debug=True)"
fi
