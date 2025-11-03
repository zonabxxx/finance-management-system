#!/bin/bash

# Quick Setup pre Turso databázu
# Tento script inicializuje databázu cez Turso CLI

echo "🚀 Turso Database Setup"
echo ""

# Check if Turso CLI is installed
if ! command -v turso &> /dev/null; then
    echo "❌ Turso CLI nie je nainštalované"
    echo ""
    echo "Nainštalujte pomocou:"
    echo "  curl -sSfL https://get.tur.so/install.sh | bash"
    echo ""
    exit 1
fi

echo "✓ Turso CLI nájdené"
echo ""

# Check if logged in
if ! turso auth token &> /dev/null; then
    echo "⚠️  Nie ste prihlásený do Turso"
    echo "  Prihláste sa pomocou: turso auth login"
    echo ""
    read -p "Prihlásiť sa teraz? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        turso auth login
    else
        exit 1
    fi
fi

echo "✓ Prihlásený do Turso"
echo ""

# Initialize database
echo "📊 Inicializujem databázu financa-sprava..."
echo ""

if [ ! -f "database_schema_turso.sql" ]; then
    echo "❌ Súbor database_schema_turso.sql nebol nájdený!"
    exit 1
fi

turso db shell financa-sprava < database_schema_turso.sql

echo ""
echo "✅ Databáza inicializovaná!"
echo ""

# Verify
echo "🔍 Overujem..."
turso db shell financa-sprava "SELECT COUNT(*) as count FROM Categories;"

echo ""
echo "🎉 Hotovo! Databáza je pripravená na použitie."
echo ""
echo "Teraz môžete spustiť:"
echo "  python3 examples.py"
echo ""

