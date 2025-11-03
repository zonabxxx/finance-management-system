# Finstat API Integrácia - Dokumentácia

## 📋 Prehľad

Finance Tracker používa [Finstat API](https://www.finstat.sk/api) pre automatickú identifikáciu firiem a ich činnosti na základe IČO.

## 🔑 Autentifikácia

Finstat API používa **SHA256 hash autentifikáciu** s dvoma kľúčmi:

1. **API Key** (verejný kľúč) - identifikuje vášho používateľa
2. **Private Key** (súkromný reťazec) - použitý pre generovanie hash

### Získanie API kľúčov

1. Registrujte sa na [https://www.finstat.sk](https://www.finstat.sk)
2. Zakúpte API prístup (plány: Štandardné, Premium, Elite, Ultimate)
3. V profile nájdete:
   - **API Key** - použite pre `FINSTAT_API_KEY`
   - **Private Key** - použite pre `FINSTAT_PRIVATE_KEY`
4. Kontaktujte `info@finstat.sk` pre detaily o Private Key

## ⚙️ Konfigurácia

Pridajte do `.env` súboru:

```env
# Finstat API Configuration
FINSTAT_API_KEY=your-api-key-here
FINSTAT_PRIVATE_KEY=your-private-key-here
FINSTAT_API_URL=https://www.finstat.sk/api
FINSTAT_STATION_ID=FinanceTracker_001
FINSTAT_STATION_NAME=Finance_Tracker_App
```

### Parametre

| Parameter | Povinný | Popis |
|-----------|---------|-------|
| `FINSTAT_API_KEY` | ✅ | API kľúč pridelený Finstatom |
| `FINSTAT_PRIVATE_KEY` | ✅ | Súkromný kľúč pre hash generovanie |
| `FINSTAT_API_URL` | ❌ | URL API (default: https://www.finstat.sk/api) |
| `FINSTAT_STATION_ID` | ❌ | ID stanice (pre tracking) |
| `FINSTAT_STATION_NAME` | ❌ | Názov stanice |

## 🔐 Hash Generovanie

Finance Tracker automaticky generuje SHA256 hash pre každú požiadavku:

```python
# Príklad pre IČO lookup
ico = "47165367"
hash_string = ico + private_key
hash = SHA256(hash_string)

# Výsledná URL
https://www.finstat.sk/api/detail?ico=47165367&apikey=YOUR_API_KEY&hash=GENERATED_HASH
```

## 📡 Použitie v kóde

### Základné použitie

```python
from finstat_client import get_company_info

# Vyhľadať firmu podľa IČO
company = get_company_info(ico='47165367')

if company:
    print(f"Názov: {company.name}")
    print(f"Činnosť: {company.activity}")
    print(f"Navrhovaná kategória: {company.suggested_category}")
```

### Pokročilé použitie

```python
from finstat_client import FinstatClient

# Vytvor vlastný klient s custom konfiguráciou
client = FinstatClient(
    api_key='your-api-key',
    private_key='your-private-key',
    station_id='MyApp_v1.0'
)

# Vyhľadaj firmu
company = client.get_company_by_ico('47165367')
```

## 📊 Podporované API volania

### ✅ Detail API (Implementované)

**Endpoint:** `GET /api/detail`

**Parametre:**
- `ico` - IČO firmy (povinný)
- `apikey` - API kľúč (povinný)
- `hash` - SHA256 hash (povinný)
- `StationId` - ID stanice (voliteľný)
- `StationName` - Názov stanice (voliteľný)

**Odpoveď (XML):**
```xml
<DetailResult>
  <Ico>47165367</Ico>
  <Name>FinStat, s. r. o.</Name>
  <Activity>Informačné technológie</Activity>
  <SkNaceText>Služby webového portálu</SkNaceText>
  <LegalFormText>Spol. s r. o.</LegalFormText>
  ...
</DetailResult>
```

### ❌ Search API (Nie je implementované)

Pre vyhľadávanie podľa názvu alebo IBAN by bolo potrebné rozšírenie implementácie.

## 🎯 Automatická kategorizácia

Finstat klient automaticky mapuje činnosť firmy na kategórie:

| Činnosť firmy | Kategória |
|---------------|-----------|
| "maloobchod s potravinami" | Potraviny |
| "drogéria", "lekáreň" | Drogéria |
| "reštaurácia", "pohostinstvo" | Reštaurácie a Kaviarne |
| "doprava", "preprava" | Doprava |
| atď. | ... |

## 🚨 Error Handling

### HTTP Error kódy

| Kód | Význam | Riešenie |
|-----|--------|----------|
| 400 | Chýba povinný parameter | Skontrolujte IČO |
| 402 | Prekročený limit | Počkajte alebo upgradujte plán |
| 403 | Neoprávnený prístup | Skontrolujte API Key a hash |
| 404 | Firma nenájdená | IČO neexistuje v databáze |
| 429 | Príliš veľa požiadaviek | Znížte frekvenciu volaní |

### Príklad error handling

```python
from finstat_client import get_company_info
import logging

company = get_company_info(ico='12345678')

if company is None:
    logging.warning("Firma nenájdená v Finstat")
    # Fallback na AI kategorizáciu
```

## 📈 Limity API

Limity závisia od vášho plánu:

| Plán | Denný limit | Mesačný limit |
|------|-------------|---------------|
| Štandardné | 1,000 | 30,000 |
| Premium | 5,000 | 150,000 |
| Elite | 20,000 | 600,000 |
| Ultimate | Neobmedzené | Neobmedzené |

## 🔄 Workflow v Finance Trackeri

```
1. B-mail notifikácia → Email Parser
   ├─ Extrahuje "KAUFLAND 1120, 23.00 EUR"
   └─ Žiadne IČO dostupné

2. Fallback stratégie:
   ├─ Pravidlová kategorizácia: "KAUFLAND" → Potraviny ✓
   └─ (Finstat nie je potrebný)

Alternatívny scenár:
1. Transakcia s IČO (napr. z faktúry)
   └─ IČO: 47165367

2. Finstat lookup:
   ├─ GET /api/detail?ico=47165367&apikey=...&hash=...
   ├─ Odpoveď: "FinStat s.r.o.", Activity: "Informačné technológie"
   └─ Mapuje na kategóriu: "Iné" alebo "Vzdelávanie"

3. Uloženie do DB:
   ├─ Merchants table (s Finstat dátami)
   └─ Transactions table (s kategóriou)
```

## 🧪 Testovanie

### Test Finstat API

```bash
# Test s príkladovým IČO (FinStat s.r.o.)
python3 -c "
from finstat_client import get_company_info

company = get_company_info(ico='47165367')
if company:
    print(f'✅ Success: {company.name}')
    print(f'   Activity: {company.activity}')
    print(f'   Category: {company.suggested_category}')
else:
    print('❌ Failed to fetch company info')
"
```

### Test hash generovania

```bash
python3 -c "
import hashlib

ico = '47165367'
private_key = 'your-private-key'
hash_string = ico + private_key
hash_value = hashlib.sha256(hash_string.encode('utf-8')).hexdigest()

print(f'IČO: {ico}')
print(f'Hash: {hash_value}')
"
```

## 💡 Tipy a best practices

### 1. Caching
```python
# Cachujte výsledky pre opakované IČO
# (implementované v database_client.py v Merchants table)
```

### 2. Batch processing
```python
# Pre veľké množstvo transakcií spracujte v dávkach
# aby ste nepresiahli rate limit
```

### 3. Fallback stratégia
```python
# Vždy majte fallback na AI kategorizáciu
if not company_info:
    # Použite OpenAI GPT-4 kategorizáciu
    category = categorize_with_ai(merchant_name)
```

### 4. Logging
```python
# Monitorujte Finstat API volania
logger.info(f"Finstat API call: IČO {ico}")
logger.info(f"Response: {company.name if company else 'Not found'}")
```

## 📞 Podpora

- **Technická dokumentácia:** https://www.finstat.sk/api
- **Support email:** info@finstat.sk
- **Telefón:** +421 2 ...

## 📝 Poznámky

1. **IBAN lookup nie je podporovaný** - Finstat Detail API nepodporuje vyhľadávanie podľa IBAN
2. **Search API nie je implementované** - Pre vyhľadávanie podľa názvu je potrebné rozšírenie
3. **XML format** - Finstat API vracia XML (nie JSON)
4. **Anonymizované záznamy** - Živnostníci zrušení pred 10+ rokmi sú anonymizovaní

## 🔄 Verzie

- **v1.0** (November 2025) - Základná integrácia s Detail API
- **Planned v1.1** - Search API integrácia
- **Planned v1.2** - Caching a rate limiting optimalizácia

---

**Last updated:** November 2, 2025  
**API Version:** Finstat API v1  
**Documentation:** [www.finstat.sk/api](https://www.finstat.sk/api)

