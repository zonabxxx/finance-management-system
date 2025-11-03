# Finance Tracker - Projektová štruktúra

## 📁 Súbory projektu

```
Sprava financii/
│
├── 📋 Konfigurácia
│   ├── config.py                    # Hlavná konfigurácia (Pydantic settings)
│   ├── config.env.example           # Šablóna pre environment variables
│   ├── .env                         # Environment variables (ignorované v git)
│   ├── .gitignore                   # Git ignore pravidlá
│   ├── requirements.txt             # Python dependencies
│   ├── host.json                    # Azure Functions konfigurácia
│   └── azure_logic_app.json         # Logic App workflow definícia
│
├── 🔧 Core moduly
│   ├── email_parser.py              # Parser pre B-mail notifikácie
│   ├── finstat_client.py            # Finstat API integrácia
│   ├── ai_categorization.py         # AI kategorizácia (OpenAI)
│   ├── database_client.py           # Azure SQL Database klient
│   ├── chatgpt_agent.py             # ChatGPT Agent (OpenAI Assistant)
│   └── function_app.py              # Azure Functions endpoints
│
├── 🗄️ Databáza
│   └── database_schema.sql          # SQL schéma pre Azure SQL
│
├── 📖 Dokumentácia
│   ├── README.md                    # Hlavná dokumentácia
│   ├── DEPLOYMENT.md                # Deployment guide
│   └── PROJECT_STRUCTURE.md         # Tento súbor
│
├── 🧪 Príklady a testy
│   ├── examples.py                  # Príklady použitia
│   └── setup.sh                     # Quick start setup script
│
└── 🚫 Ignorované súbory
    ├── venv/                        # Virtual environment
    ├── __pycache__/                 # Python cache
    └── .env                         # Secrets
```

## 🔄 Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    B-MAIL NOTIFIKÁCIA                       │
│  "KAUFLAND 1120 - 23,00 EUR - 3. novembra 2025"            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              AZURE LOGIC APP (Email Trigger)                 │
│  • Monitoruje Office 365 Inbox                              │
│  • Filter: "Pohyby na účte"                                 │
│  • Spúšťa sa pri každom novom emaile                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         AZURE FUNCTION: ProcessEmailNotification            │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │ 1. EMAIL PARSER (email_parser.py)                  │   │
│  │    • Extrahuje: obchodník, suma, dátum, IBAN       │   │
│  │    • Parsuje CO2 stopu, symboly                    │   │
│  │    Result: TransactionData                         │   │
│  └──────────────────┬─────────────────────────────────┘   │
│                     │                                       │
│                     ▼                                       │
│  ┌────────────────────────────────────────────────────┐   │
│  │ 2. FINSTAT CLIENT (finstat_client.py)             │   │
│  │    • Vyhľadanie firmy podľa IBAN/názvu            │   │
│  │    • Získanie IČO, činnosti                       │   │
│  │    Result: CompanyInfo                            │   │
│  └──────────────────┬─────────────────────────────────┘   │
│                     │                                       │
│                     ▼                                       │
│  ┌────────────────────────────────────────────────────┐   │
│  │ 3. AI CATEGORIZATION (ai_categorization.py)       │   │
│  │                                                    │   │
│  │    a) Pravidlová kategorizácia (rýchla)          │   │
│  │       ├─ "KAUFLAND" → Potraviny (95%)            │   │
│  │       └─ Pattern matching                         │   │
│  │                                                    │   │
│  │    b) Finstat kategorizácia                       │   │
│  │       ├─ Na základe činnosti firmy               │   │
│  │       └─ Mapped categories (85%)                  │   │
│  │                                                    │   │
│  │    c) OpenAI GPT-4 kategorizácia                 │   │
│  │       ├─ Semantic understanding                   │   │
│  │       └─ JSON response (70-90%)                   │   │
│  │                                                    │   │
│  │    Result: CategoryPrediction                     │   │
│  └──────────────────┬─────────────────────────────────┘   │
│                     │                                       │
│                     ▼                                       │
│  ┌────────────────────────────────────────────────────┐   │
│  │ 4. DATABASE CLIENT (database_client.py)           │   │
│  │    • Vytvorí/nájde obchodníka (Merchants)        │   │
│  │    • Uloží transakciu (Transactions)             │   │
│  │    • Prepojí s kategóriou (Categories)           │   │
│  │    Result: transaction_id                         │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  AZURE SQL DATABASE                          │
│                                                             │
│  Tables:                                                    │
│  ├─ Transactions (hlavná tabuľka)                         │
│  ├─ Merchants (obchodníci)                                │
│  ├─ Categories (kategórie)                                │
│  ├─ CategoryRules (pravidlá)                              │
│  └─ CategoryTraining (AI learning)                        │
│                                                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│             CHATGPT AGENT (chatgpt_agent.py)                │
│                                                             │
│  OpenAI Assistant API:                                      │
│  • Konverzačné rozhranie (slovenčina)                      │
│  • Function calling pre prístup k DB                       │
│  • Analýza výdavkov, insights                             │
│                                                             │
│  Príklady:                                                  │
│  ├─ "Koľko som minul tento mesiac?"                       │
│  ├─ "Ukáž transakcie na potraviny"                        │
│  └─ "Aký je priemerný mesačný výdavok?"                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Použitie modulov

### 1. Email Parser
```python
from email_parser import parse_bmail_notification

result = parse_bmail_notification(email_html)
# Returns: {
#   'merchant_name': 'KAUFLAND 1120',
#   'amount': 23.00,
#   'currency': 'EUR',
#   'transaction_date': '2025-11-03T00:00:00',
#   ...
# }
```

### 2. Finstat Client
```python
from finstat_client import get_company_info

company = get_company_info(ico='31333532')
# Returns: CompanyInfo(
#   ico='31333532',
#   name='KAUFLAND Slovenská republika v.o.s.',
#   activity='Maloobchod s potravinami',
#   suggested_category='Potraviny'
# )
```

### 3. AI Categorization
```python
from ai_categorization import categorize_transaction

result = categorize_transaction(
    merchant_name='KAUFLAND 1120',
    amount=23.00
)
# Returns: CategoryPrediction(
#   category='Potraviny',
#   confidence=0.95,
#   reasoning='Pravidlová zhoda pre KAUFLAND',
#   source='Rule'
# )
```

### 4. Database Client
```python
from database_client import db_client

# Insert transaction
transaction_id = db_client.insert_transaction(
    transaction_date=datetime.now(),
    amount=23.00,
    merchant_name='KAUFLAND 1120',
    category_id=1,
    ...
)

# Get transactions
transactions = db_client.get_transactions(
    start_date=datetime(2025, 11, 1),
    end_date=datetime(2025, 11, 30)
)

# Monthly summary
summary = db_client.get_monthly_summary(2025, 11)
```

### 5. ChatGPT Agent
```python
from chatgpt_agent import ask_finance_question

response = ask_finance_question("Koľko som minul tento mesiac?")
print(response['response'])
# "Tento mesiac si minul 1 234,56 EUR na celkovo 45 transakcií..."

# Continue conversation
response = ask_finance_question(
    "A koľko z toho bolo na potraviny?",
    thread_id=response['thread_id']
)
```

## 🔐 Konfigurácia (Environment Variables)

### Povinné
- `AZURE_SQL_SERVER` - Azure SQL server hostname
- `AZURE_SQL_DATABASE` - Názov databázy
- `AZURE_SQL_USERNAME` - SQL login
- `AZURE_SQL_PASSWORD` - SQL heslo
- `OPENAI_API_KEY` - OpenAI API kľúč

### Odporúčané
- `FINSTAT_API_KEY` - Finstat API kľúč
- `OPENAI_ASSISTANT_ID` - Pre existujúci assistant
- `APPINSIGHTS_INSTRUMENTATION_KEY` - Monitoring

### Voliteľné
- `AI_CONFIDENCE_THRESHOLD` - Min. istota pre AI (default: 0.7)
- `USE_FINSTAT_FOR_UNKNOWN` - Použiť Finstat fallback (default: true)
- `OPENAI_MODEL` - GPT model (default: gpt-4-turbo-preview)

## 📊 Databázové tabuľky

### Transactions
Hlavná tabuľka pre transakcie
```sql
TransactionID, TransactionDate, Amount, Currency,
MerchantID, MerchantName, CategoryID, Description,
IBAN, PaymentMethod, CO2Footprint,
AIConfidence, CategorySource
```

### Merchants
Obchodníci a firmy
```sql
MerchantID, Name, IBAN, ICO, 
FinstatData (JSON), DefaultCategoryID
```

### Categories
Kategórie výdavkov
```sql
CategoryID, Name, Icon, Color, ParentCategoryID
```

## 🚀 Quick Start Commands

```bash
# Setup
./setup.sh

# Lokálne testovanie
python3 examples.py

# Spustenie Azure Functions lokálne
func start

# Nasadenie do Azure
func azure functionapp publish your-function-app

# Testovanie API
curl -X POST http://localhost:7071/api/process-email \
  -H "Content-Type: application/json" \
  -d @test_email.json
```

## 📈 Metriky a monitoring

- **Application Insights** - Logy, metriky, traces
- **SQL Database** - Query performance, storage
- **Function App** - Execution count, duration, errors
- **OpenAI API** - Token usage, costs

## 🔄 Aktualizácie a údržba

### Pridanie novej kategórie
1. Pridaj do `database_schema.sql` (Categories)
2. Updatuj `CATEGORIES` v `ai_categorization.py`
3. Pridaj pravidlá do `rule_patterns`

### Vylepšenie kategorizácie
1. Pridaj training data do `CategoryTraining`
2. Updatuj pravidlá v `ai_categorization.py`
3. Fine-tune OpenAI prompt

### Nová banka/formát
1. Rozšír `email_parser.py` o nový pattern
2. Testuj s reálnymi emailami
3. Pridaj unit testy

---

**Verzia:** 1.0.0  
**Posledná aktualizácia:** November 2025  
**Autor:** Finance Tracker Team

