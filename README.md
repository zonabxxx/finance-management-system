# Automatická správa financií - Azure & AI riešenie

Komplexný systém pre automatické zapisovanie a kategorizáciu bankových transakcií z B-mail notifikácií do Azure databázy s AI kategorizáciou a ChatGPT agentom.

## 🎯 Funkcie

✅ **Automatické spracovanie B-mail notifikácií** - Email parser pre slovenské banky  
✅ **AI Kategorizácia** - Použitie OpenAI GPT-4 + pravidlová logika  
✅ **Finstat integrácia** - Automatická identifikácia firiem podľa IČO/IBAN  
✅ **ChatGPT Agent** - Konverzačný asistent pre analýzu výdavkov  
✅ **Azure SQL Database** - Centrálne úložisko transakcií  
✅ **Azure Functions** - Serverless spracovanie  
✅ **Azure Logic App** - Automatizácia email workflow  

## 🏗️ Architektúra

```
┌─────────────────┐
│   B-mail        │
│   Notifikácia   │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Azure Logic    │ ← Email trigger
│  App            │
└────────┬────────┘
         │
         v
┌─────────────────────────────────────────┐
│  Azure Function: ProcessEmailNotification│
│  ┌──────────────────────────────────┐   │
│  │ 1. Email Parser                  │   │
│  │ 2. Finstat API (IČO/IBAN lookup) │   │
│  │ 3. AI Kategorization (OpenAI)    │   │
│  │ 4. Database Insert               │   │
│  └──────────────────────────────────┘   │
└────────┬────────────────────────────────┘
         │
         v
┌─────────────────┐
│  Azure SQL      │
│  Database       │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  ChatGPT Agent  │ ← Užívateľské dotazy
│  (OpenAI)       │
└─────────────────┘
```

## 📦 Komponenty

### 1. Email Parser (`email_parser.py`)
- Parsuje B-mail notifikácie
- Extrahuje: názov obchodníka, suma, dátum, IBAN, variabilný symbol, CO2 stopu
- Podporuje HTML aj plain text formát

### 2. Finstat Client (`finstat_client.py`)
- Integrácia s Finstat API
- Vyhľadávanie firiem podľa IČO, IBAN alebo názvu
- Automatické mapovanie činnosti na kategórie

### 3. AI Kategorization (`ai_categorization.py`)
- **3-stupňová kategorizácia:**
  1. **Pravidlová** (najrýchlejšia) - Pattern matching pre známe obchody
  2. **Finstat** - Na základe činnosti firmy
  3. **AI (OpenAI GPT-4)** - Inteligentné určenie kategórie

- **13 kategórií:**
  - Potraviny 🛒
  - Drogéria 🧴
  - Reštaurácie a Kaviarne ☕
  - Donáška jedla 🍕
  - Doprava 🚗
  - Bývanie 🏠
  - Zdravie ⚕️
  - Zábava 🎬
  - Oblečenie 👕
  - Telefón a Internet 📱
  - Vzdelávanie 📚
  - Šport ⚽
  - Iné 📦

### 4. Database Client (`database_client.py`)
- Azure SQL Database integrácia
- CRUD operácie pre transakcie, obchodníkov, kategórie
- Mesačné prehľady a štatistiky

### 5. Azure Functions (`function_app.py`)
- **ProcessEmailNotification** - Hlavný endpoint pre spracovanie emailov
- **GetTransactions** - API pre získanie transakcií
- **GetMonthlySummary** - API pre mesačné prehľady

### 6. ChatGPT Agent (`chatgpt_agent.py`)
- OpenAI Assistant API
- Konverzačné rozhranie v slovenčine
- Function calling pre prístup k databáze
- Príklady otázok:
  - "Koľko som minul tento mesiac?"
  - "Ukáž mi výdavky za november na potraviny"
  - "Aký je môj priemerný mesačný výdavok?"
  - "Najdrahšia transakcia minulý mesiac?"

## 🚀 Nasadenie

### Predpoklady

- Azure účet
- OpenAI API kľúč
- Finstat API kľúč
- Python 3.9+

### Krok 1: Azure SQL Database

1. Vytvorte Azure SQL Database:
```bash
az sql server create --name your-server --resource-group your-rg --location westeurope --admin-user sqladmin --admin-password YourPassword123!

az sql db create --resource-group your-rg --server your-server --name finance_tracker --service-objective S0
```

2. Spustite SQL skript:
```bash
sqlcmd -S your-server.database.windows.net -d finance_tracker -U sqladmin -P YourPassword123! -i database_schema.sql
```

### Krok 2: Azure Function App

1. Vytvorte Function App:
```bash
az functionapp create --resource-group your-rg --consumption-plan-location westeurope --runtime python --runtime-version 3.9 --functions-version 4 --name your-finance-function --storage-account yourstorage
```

2. Nastavte premenné prostredia:
```bash
az functionapp config appsettings set --name your-finance-function --resource-group your-rg --settings \
  AZURE_SQL_SERVER=your-server.database.windows.net \
  AZURE_SQL_DATABASE=finance_tracker \
  AZURE_SQL_USERNAME=sqladmin \
  AZURE_SQL_PASSWORD=YourPassword123! \
  OPENAI_API_KEY=sk-your-key \
  FINSTAT_API_KEY=your-finstat-key
```

3. Nasaďte kód:
```bash
func azure functionapp publish your-finance-function
```

### Krok 3: Azure Logic App

1. Vytvorte Logic App v Azure Portal
2. Importujte workflow z `azure_logic_app.json`
3. Nakonfigurujte:
   - Office 365 connector (pre B-mail)
   - Function App URL a kľúč
   - Email filter: "Pohyby na účte"

### Krok 4: B-mail nastavenie

1. Prihláste sa do internetbankingu
2. Prejdite do nastavení B-mail
3. Aktivujte notifikácie:
   - ✅ Kredit od zvolenej sumy (0,01 EUR)
   - ✅ Debet od zvolenej sumy (0,01 EUR)
   - ✅ Avízo o nezrealizovanej platbe
   - ✅ Pozdržať nočné správy (vypnúť)
4. Zadajte email adresu, ktorú monitoruje Logic App

### Krok 5: ChatGPT Agent

1. Agent sa vytvorí automaticky pri prvom použití
2. Alebo vytvorte manuálne v OpenAI Platform a nastavte `OPENAI_ASSISTANT_ID`

## 💻 Použitie

### API Endpoints

#### 1. Spracovanie emailu
```bash
POST https://your-finance-function.azurewebsites.net/api/process-email
Content-Type: application/json

{
  "body": "<html>...B-mail email...</html>",
  "subject": "Pohyby na účte"
}
```

Odpoveď:
```json
{
  "success": true,
  "transaction_id": 123,
  "merchant_name": "KAUFLAND 1120",
  "amount": 23.50,
  "category": "Potraviny",
  "confidence": 0.95,
  "source": "Rule"
}
```

#### 2. Získanie transakcií
```bash
GET https://your-finance-function.azurewebsites.net/api/transactions?start_date=2025-11-01&end_date=2025-11-30&limit=50
```

#### 3. Mesačný prehľad
```bash
GET https://your-finance-function.azurewebsites.net/api/summary/monthly?year=2025&month=11
```

### ChatGPT Agent (Python)

```python
from chatgpt_agent import ask_finance_question

# Prvá otázka (vytvorí nový thread)
response = ask_finance_question("Koľko som minul tento mesiac?")
print(response['response'])
thread_id = response['thread_id']

# Pokračovanie konverzácie
response = ask_finance_question(
    "A koľko z toho bolo na potraviny?", 
    thread_id=thread_id
)
print(response['response'])
```

## 📊 Príklady kategorizácie

### 1. Pravidlová kategorizácia (95% istota)
- `KAUFLAND 1120` → **Potraviny**
- `DR.MAX 039` → **Drogéria**
- `U Kocmundu Biely kríz` → **Reštaurácie a Kaviarne**

### 2. Finstat kategorizácia (85% istota)
- IBAN `SK8911200000198742637541` → Vyhľadá firmu → Získa činnosť → Mapuje na kategóriu

### 3. AI kategorizácia (70-90% istota)
- Neznámy obchodník → GPT-4 analyzuje názov → Určí kategóriu s odôvodnením

## 🔧 Konfigurácia

Vytvorte súbor `.env`:
```bash
cp config.env.example .env
```

Upravte hodnoty:
```env
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DATABASE=finance_tracker
AZURE_SQL_USERNAME=sqladmin
AZURE_SQL_PASSWORD=YourPassword123!

OPENAI_API_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-4-turbo-preview

FINSTAT_API_KEY=your-finstat-key

AI_CONFIDENCE_THRESHOLD=0.7
USE_FINSTAT_FOR_UNKNOWN=true
ENABLE_WEB_SCRAPING=true
```

## 📈 Databázová schéma

```sql
Transactions
├─ TransactionID (PK)
├─ TransactionDate
├─ Amount
├─ MerchantName
├─ CategoryID (FK → Categories)
├─ MerchantID (FK → Merchants)
├─ IBAN
├─ CO2Footprint
├─ AIConfidence
└─ CategorySource (Rule/Finstat/AI)

Categories
├─ CategoryID (PK)
├─ Name
└─ Icon

Merchants
├─ MerchantID (PK)
├─ Name
├─ IBAN
├─ ICO
├─ FinstatData (JSON)
└─ DefaultCategoryID (FK)
```

## 🧪 Testovanie

```bash
# Nainštalujte závislosti
pip install -r requirements.txt

# Spustite testy
pytest

# Test email parsera
python -c "from email_parser import parse_bmail_notification; print(parse_bmail_notification('<html>...</html>'))"

# Test Finstat API
python -c "from finstat_client import get_company_info; print(get_company_info(ico='31333532'))"

# Test AI kategorizácie
python -c "from ai_categorization import categorize_transaction; print(categorize_transaction('KAUFLAND', 25.50))"
```

## 💰 Náklady (približne)

- **Azure SQL Database S0**: ~15 EUR/mesiac
- **Azure Function App Consumption**: ~0-5 EUR/mesiac (prvých 1M volaní zadarmo)
- **Azure Logic App**: ~0-2 EUR/mesiac
- **OpenAI API**: 
  - GPT-4 Turbo: ~$0.01/transakcia
  - Assistant API: ~$0.01/otázka
- **Finstat API**: Závisí od plánu

**Celkom**: ~20-30 EUR/mesiac pre 500+ transakcií

## 🔐 Bezpečnosť

- Všetky API kľúče v Azure Key Vault (odporúčané)
- Azure Function auth level: `Function` (vyžaduje kľúč)
- SQL Database: Firewall pravidlá len pre Azure services
- HTTPS everywhere
- Email dáta šifrované v databáze

## 📝 Ďalší vývoj

- [ ] Web dashboard (React + Chart.js)
- [ ] Mobilná aplikácia
- [ ] Rozpočty a upozornenia
- [ ] Export do PDF/Excel
- [ ] Predikcia výdavkov (ML)
- [ ] Multi-user podpora
- [ ] Integrácia s viacerými bankami

## 🐛 Riešenie problémov

### Email sa nespracúva
1. Skontrolujte Logic App Run History
2. Overte email filter ("Pohyby na účte")
3. Skontrolujte Function App logs

### Zlá kategorizácia
1. Upravte pravidlá v `ai_categorization.py`
2. Znížte `AI_CONFIDENCE_THRESHOLD`
3. Pridajte training dáta do `CategoryTraining`

### Finstat API nefunguje
1. Overte API kľúč
2. Skontrolujte limit volaní
3. Fallback na AI kategorizáciu

## 📧 Podpora

Pre otázky a problémy vytvorte issue.

## 📄 Licencia

MIT License

---

**Vytvořené s ❤️ pre slovenských používateľov**

