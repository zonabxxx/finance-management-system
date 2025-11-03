#!/bin/bash

# Quick Start Script pre Finance Tracker
# Tento skript vás prevedie základným setupom

set -e  # Exit on error

echo "================================================"
echo "  Finance Tracker - Quick Start Setup"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check prerequisites
echo "1️⃣  Kontrola predpokladov..."
echo ""

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python $PYTHON_VERSION nainštalovaný"
else
    print_error "Python 3.9+ nie je nainštalovaný"
    exit 1
fi

# Check Azure CLI
if command -v az &> /dev/null; then
    AZ_VERSION=$(az version --output tsv --query '"azure-cli"')
    print_success "Azure CLI nainštalované"
else
    print_warning "Azure CLI nie je nainštalované (potrebné pre Azure deployment)"
fi

# Check Azure Functions Core Tools
if command -v func &> /dev/null; then
    FUNC_VERSION=$(func --version)
    print_success "Azure Functions Core Tools $FUNC_VERSION"
else
    print_warning "Azure Functions Core Tools nie sú nainštalované"
fi

echo ""
echo "2️⃣  Vytvorenie virtual environment..."
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment vytvorené"
else
    print_warning "Virtual environment už existuje"
fi

# Activate virtual environment
source venv/bin/activate
print_success "Virtual environment aktivované"

echo ""
echo "3️⃣  Inštalácia závislostí..."
echo ""

pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
print_success "Závislosti nainštalované"

echo ""
echo "4️⃣  Konfigurácia..."
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    if [ -f "config.env.example" ]; then
        cp config.env.example .env
        print_success ".env súbor vytvorený z šablóny"
        print_warning "PROSÍM UPRAVTE .env súbor s vašimi API kľúčmi!"
        echo ""
        echo "   Potrebujete:"
        echo "   - Azure SQL credentials"
        echo "   - OpenAI API key"
        echo "   - Finstat API key"
        echo ""
    else
        print_error "config.env.example not found"
        exit 1
    fi
else
    print_warning ".env súbor už existuje"
fi

echo ""
echo "5️⃣  Kontrola konfigurácie..."
echo ""

# Load .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check critical variables
MISSING=0

if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sk-your-openai-api-key" ]; then
    print_warning "OPENAI_API_KEY nie je nastavený"
    MISSING=1
fi

if [ -z "$FINSTAT_API_KEY" ] || [ "$FINSTAT_API_KEY" = "your-finstat-api-key" ]; then
    print_warning "FINSTAT_API_KEY nie je nastavený"
    MISSING=1
fi

if [ -z "$AZURE_SQL_SERVER" ] || [ "$AZURE_SQL_SERVER" = "your-server.database.windows.net" ]; then
    print_warning "AZURE_SQL_SERVER nie je nastavený"
    MISSING=1
fi

if [ $MISSING -eq 1 ]; then
    echo ""
    print_warning "Niektoré konfiguračné hodnoty chýbajú. Upravte .env súbor."
    echo ""
    echo "Pokračovať aj tak? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 0
    fi
else
    print_success "Všetky kritické premenné sú nastavené"
fi

echo ""
echo "6️⃣  Test základných komponentov..."
echo ""

# Test email parser
echo "Testing email parser..."
python3 -c "
from email_parser import EmailParser
parser = EmailParser()
print('✓ Email parser OK')
" 2>/dev/null && print_success "Email parser funguje" || print_warning "Email parser test failed"

# Test AI categorization (len import)
echo "Testing AI categorization..."
python3 -c "
from ai_categorization import AICategorizationService
print('✓ AI categorization OK')
" 2>/dev/null && print_success "AI categorization module OK" || print_warning "AI categorization test failed"

echo ""
echo "================================================"
echo "  Setup dokončený!"
echo "================================================"
echo ""

print_success "Systém je pripravený na použitie"
echo ""
echo "📚 Ďalšie kroky:"
echo ""
echo "   1. Upravte .env súbor s vašimi API kľúčmi:"
echo "      nano .env"
echo ""
echo "   2. Pre lokálne testovanie spustite:"
echo "      python3 examples.py"
echo ""
echo "   3. Pre spustenie Azure Functions lokálne:"
echo "      func start"
echo ""
echo "   4. Pre nasadenie do Azure:"
echo "      Postupujte podľa DEPLOYMENT.md"
echo ""
echo "   5. Dokumentácia:"
echo "      README.md - Hlavná dokumentácia"
echo "      DEPLOYMENT.md - Deployment guide"
echo ""

echo "================================================"
echo ""

