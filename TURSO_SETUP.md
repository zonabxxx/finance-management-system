# Turso Database Setup - Návod

## 🎯 Prečo Turso?

✅ **Zadarmo až 9 GB storage**  
✅ **SQLite na cloud** (rýchle, jednoduché)  
✅ **Globálna replikácia** (nízka latencia)  
✅ **Automatické zálohy**  
✅ **Bez servera** (serverless)  

## 📝 Krok za krokom

### 1. Vytvorenie Turso účtu

1. Prejdite na [https://turso.tech](https://turso.tech)
2. Kliknite **Sign Up**
3. Prihláste sa cez GitHub
4. Potvrďte účet

### 2. Inštalácia Turso CLI (voliteľné)

```bash
# macOS/Linux
curl -sSfL https://get.tur.so/install.sh | bash

# Windows (PowerShell)
irm get.tur.so/install.ps1 | iex

# Overte inštaláciu
turso --version
```

### 3. Vytvorenie databázy (cez Web UI)

Už máte vytvorenú databázu: **financa-sprava**

📍 URL: `libsql://financa-sprava-zonabxxx.aws-eu-west-1.turso.io`

### 4. Vytvorenie Auth Tokenu

V Turso Dashboard:

1. Kliknite na databázu **financa-sprava**
2. Kliknite **"Create Token"**
3. Skopírujte vygenerovaný token
4. Token vyzerá takto: `eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9...`

### 5. Konfigurácia vo Finance Trackeri

Upravte `.env` súbor:

```bash
nano .env
```

Vyplňte:

```env
# Turso Database Configuration
TURSO_DATABASE_URL=libsql://financa-sprava-zonabxxx.aws-eu-west-1.turso.io
TURSO_AUTH_TOKEN=eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9...  # Váš token

# OpenAI Configuration
OPENAI_API_KEY=sk-proj-your-key-here
```

### 6. Inštalácia závislostí

```bash
pip install -r requirements.txt
```

### 7. Inicializácia databázovej schémy

#### Možnosť A: Cez Turso CLI (odporúčané)

```bash
# Prihláste sa do Turso
turso auth login

# Pripojte sa k databáze
turso db shell financa-sprava

# Spustite SQL schému
.read database_schema_turso.sql

# Overte tabuľky
.tables

# Overte kategórie
SELECT * FROM Categories;

# Ukončite
.exit
```

#### Možnosť B: Cez Python script

```bash
python3 << 'EOF'
from database_client import db_client

# Načítaj SQL schému
with open('database_schema_turso.sql', 'r') as f:
    sql_commands = f.read()

# Rozdeľ na jednotlivé príkazy a vykonaj
for command in sql_commands.split(';'):
    command = command.strip()
    if command:
        try:
            db_client.execute(command)
            print(f"✓ Executed: {command[:50]}...")
        except Exception as e:
            print(f"✗ Error: {e}")

print("\n✅ Database schema initialized!")
EOF
```

### 8. Testovanie pripojenia

```bash
python3 << 'EOF'
from database_client import db_client

# Test connection
try:
    result = db_client.execute("SELECT COUNT(*) FROM Categories")
    count = result.rows[0][0]
    print(f"✅ Pripojenie úspešné! Počet kategórií: {count}")
except Exception as e:
    print(f"❌ Chyba: {e}")
EOF
```

### 9. Vloženie testovacej transakcie

```bash
python3 << 'EOF'
from database_client import db_client
from datetime import datetime

# Získaj ID kategórie "Potraviny"
category_id = db_client.get_category_id_by_name("Potraviny")

# Vytvor obchodníka
merchant_id = db_client.get_or_create_merchant(
    name="KAUFLAND 1120",
    iban="SK8911200000198742637541"
)

# Vlož transakciu
transaction_id = db_client.insert_transaction(
    transaction_date=datetime.now(),
    amount=23.50,
    merchant_name="KAUFLAND 1120",
    merchant_id=merchant_id,
    category_id=category_id,
    payment_method="Card",
    co2_footprint=4.80,
    ai_confidence=0.95,
    category_source="Rule"
)

print(f"✅ Transakcia vložená s ID: {transaction_id}")

# Zobraz transakcie
transactions = db_client.get_transactions(limit=5)
print(f"\n📊 Posledných {len(transactions)} transakcií:")
for t in transactions:
    print(f"  - {t['MerchantName']}: {t['Amount']} €")
EOF
```

## 🔐 Turso Token Management

### Vytvorenie tokenu cez CLI

```bash
turso db tokens create financa-sprava
```

### Zrušenie tokenu

```bash
turso db tokens invalidate financa-sprava
```

### Zoznam tokenov

```bash
turso db tokens list financa-sprava
```

## 📊 Turso Dashboard Features

### Analytics
- Počet reads/writes
- Storage usage
- Query performance

### Monitoring
```bash
# Real-time logy
turso db shell financa-sprava --stream
```

### Zálohy
Turso automaticky zálohuje každých 24 hodín.

## 💾 Branches (Development databázy)

```bash
# Vytvor development branch
turso db create financa-sprava-dev --from-db financa-sprava

# Použite dev branch pre testovanie
TURSO_DATABASE_URL=libsql://financa-sprava-dev-zonabxxx.turso.io
```

## 🚀 Performance Tips

### 1. Indexes
Už sú vytvorené v `database_schema_turso.sql`:
- `idx_transactions_date`
- `idx_transactions_merchant`
- `idx_transactions_category`

### 2. Batch Inserts
```python
# Pre veľa transakcií naraz používajte transakcie
client = db_client._get_client()
client.execute("BEGIN")
try:
    for transaction in transactions:
        db_client.insert_transaction(**transaction)
    client.execute("COMMIT")
except:
    client.execute("ROLLBACK")
```

### 3. Connection Pooling
Turso automaticky spravuje connection pool.

## 📈 Limity (Free Plan)

| Resource | Limit |
|----------|-------|
| Storage | 9 GB |
| Reads | 2.5 B/mesiac |
| Writes | 25 M/mesiac |
| Databases | 500 aktívnych |
| Branches | Unlimited |

Pre Finance Tracker:
- ✅ 1000+ transakcií/mesiac = cca 1-2 MB
- ✅ Reads: ~100k/mesiac
- ✅ Writes: ~1000/mesiac

**Zadarmo pre roky!** 🎉

## 🔄 Migrácia z Azure SQL

Ak ste používali Azure SQL:

```bash
# Exportujte dáta z Azure
# Importujte do Turso
turso db shell financa-sprava < export.sql
```

## 🆘 Troubleshooting

### Error: "Authentication failed"
```bash
# Skontrolujte token v .env
echo $TURSO_AUTH_TOKEN

# Vygenerujte nový token
turso db tokens create financa-sprava
```

### Error: "Connection timeout"
```bash
# Skontrolujte URL
echo $TURSO_DATABASE_URL

# Ping databázy
turso db show financa-sprava
```

### Error: "Table already exists"
```bash
# Drop a znovu vytvor schému
turso db shell financa-sprava
DROP TABLE IF EXISTS Transactions;
DROP TABLE IF EXISTS Merchants;
DROP TABLE IF EXISTS Categories;
.read database_schema_turso.sql
```

## 📞 Podpora

- **Docs:** https://docs.turso.tech
- **Discord:** https://discord.gg/turso
- **GitHub:** https://github.com/tursodatabase/libsql

## ✅ Checklist

- [ ] Turso účet vytvorený
- [ ] Databáza **financa-sprava** existuje
- [ ] Auth token vygenerovaný
- [ ] `.env` vyplnený s URL a tokenom
- [ ] Dependencies nainštalované (`pip install -r requirements.txt`)
- [ ] SQL schéma nainicializovaná
- [ ] Test pripojenia úspešný ✓
- [ ] Testovacia transakcia vložená ✓

## 🎉 Hotovo!

Vaša Turso databáza je pripravená! Teraz môžete:

```bash
# Spustiť príklady
python3 examples.py

# Alebo začať používať systém
from database_client import db_client
transactions = db_client.get_transactions()
```

---

**Last updated:** November 2, 2025  
**Turso Version:** LibSQL (SQLite compatible)

