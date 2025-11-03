# 🤖 ChatGPT GPT - Finance Assistant - Setup Guide

## 📋 Krok 1: Základné informácie

### **Name:**
```
Finance Assistant SK
```

### **Description:**
```
Tvoj osobný finančný asistent. Analyzuje výdavky, príjmy a bankové účty. Odpovedá v slovenčine.
```

### **Instructions:**
```
Ty si osobný finančný asistent pre používateľa v Slovensku.

**Tvoja úloha:**
- Analyzovať výdavky a príjmy používateľa
- Odpovedať na otázky o financiách v slovenčine
- Poskytovať prehľady transakcií, kategórií a bankových účtov
- Pomáhať s rozpočtovaním a sledovaním výdavkov
- Identifikovať trendy a odporučiť úspory

**Pravidlá:**
- Vždy odpovedaj v SLOVENČINE
- Sumy uvádzaj v EUR s dvoma desatinnými miestami (napr: -10.18 EUR)
- Negatívne sumy = výdavky, pozitívne = príjmy
- Buď priateľský, ale profesionálny
- Ak nemáš dáta, povedz to priamo
- Používaj emoji pre lepšiu čitateľnosť 💰📊🏦

**Dostupné dáta:**
- Bankové účty (IBAN, názov, banka)
- Transakcie (dátum, suma, obchodník, kategória, účet)
- Kategórie výdavkov (jedlo, doprava, bývanie, atď.)
- Mesačné štatistiky a trendy

**Príklady otázok:**
- "Koľko som minul tento mesiac?"
- "Aké sú moje top 5 výdavkov?"
- "Ukáž mi transakcie z účtu Môj účet"
- "Koľko míňam na jedlo?"
- "Porovnaj tento mesiac s minulým"

Vždy najprv načítaj aktuálne dáta cez API, potom odpovedz.
```

### **Conversation starters:**
```
💰 Koľko som minul tento mesiac?
🏦 Aké účty mám?
📊 Top 5 výdavkov?
🍔 Koľko míňam na jedlo?
```

---

## 🔧 Krok 2: Actions (API Integration)

V sekcii **Configure** → scroll down → **Actions** → **Create new action**

### **Metóda 1: Import z URL (Odporúčané)**

1. Klikni **Import from URL**
2. Vlož URL:
```
https://raw.githubusercontent.com/zonabxxx/finance-management-system/main/openapi_gpt.json
```
3. Klikni **Import**

### **Metóda 2: Manuálne nahratie**

1. Klikni **Import** → **Upload file**
2. Vyber súbor: `openapi_gpt.json` z projektu
3. Klikni **Upload**

---

## 🔐 Krok 3: Authentication

Po importe API schémy:

1. V Actions editore scroll down na **Authentication**
2. Vyber **Authentication Type:** `Bearer`
3. Vlož **Bearer Token:**
   ```
   <TVOJ_API_KEY_Z_.env>
   ```
   (Vezmi ho z `.env` súboru - premenná `API_KEY`)

4. Klikni **Save**

---

## 🚀 Krok 4: Deployment

### **Railway už beží!**

Tvoj API server už beží na Railway:
```
https://finance-management-system-production.up.railway.app
```

**Ale potrebujeme pridať API routes do `web_ui.py`!**

Momentálne Railway používa `web_ui.py`, ale GPT API endpointy sú v `api_server.py`.

**Riešenie:** Pridáme GPT API endpointy do `web_ui.py` aby všetko bežalo na jednom serveri.

---

## 🧪 Krok 5: Testovanie

1. **Test API endpoint priamo:**
   ```bash
   curl -H "Authorization: Bearer <API_KEY>" \
        https://finance-management-system-production.up.railway.app/api/health
   ```

2. **Test v GPT:**
   - Klikni **Preview** vpravo hore
   - Napíš: "Koľko som minul tento mesiac?"
   - GPT by mal zavolať API a vrátiť odpoveď v slovenčine

---

## 📝 Príklady otázok pre GPT:

```
1. "Koľko som minul tento mesiac?"
   → Zavolá: GET /api/transactions/summary?days=30

2. "Aké účty mám?"
   → Zavolá: GET /api/accounts/list

3. "Ukáž mi posledných 5 transakcií"
   → Zavolá: GET /api/transactions/recent?limit=5

4. "Koľko som minul na BOLT?"
   → Zavolá: GET /api/transactions/search?merchant=BOLT

5. "Daj mi prehľad môjho prvého účtu"
   → Zavolá: GET /api/accounts/1/summary?days=30

6. "Aké kategórie výdavkov mám?"
   → Zavolá: GET /api/categories/list

7. "Top 10 obchodníkov kde míňam najviac"
   → Zavolá: GET /api/transactions/top-merchants?limit=10

8. "Mesačný prehľad za posledných 6 mesiacov"
   → Zavolá: GET /api/transactions/monthly?months=6
```

---

## 🎨 Ikonka (Optional)

Nahraj nejakú finančnú ikonku (💰, 🏦, 📊) alebo vytvor vlastnú.

---

## ⚠️ Dôležité poznámky:

1. **API Key musí byť tajný** - nikdy ho nezdieľaj
2. **Railway beží 24/7** - GPT bude fungovať kedykoľvek
3. **Odpovede sú v real-time** - vždy aktuálne dáta
4. **SSL/HTTPS** - Railway už má SSL certifikát

---

## 🔧 Troubleshooting:

### "Unauthorized"
→ Skontroluj API Key v Authentication

### "API call failed"
→ Skontroluj či Railway beží: https://finance-management-system-production.up.railway.app/api/health

### "No data"
→ Skontroluj či máš transakcie v databáze

---

## 📞 API Endpoints (Pre referenciu):

| Endpoint | Popis |
|----------|-------|
| `GET /api/health` | Health check |
| `GET /api/accounts/list` | Zoznam účtov |
| `GET /api/accounts/{id}/summary` | Štatistiky účtu |
| `GET /api/transactions/summary` | Zhrnutie transakcií |
| `GET /api/transactions/recent` | Posledné transakcie |
| `GET /api/transactions/by-category` | Výdavky podľa kategórií |
| `GET /api/transactions/top-merchants` | Top obchodníci |
| `GET /api/transactions/monthly` | Mesačné štatistiky |
| `GET /api/transactions/search` | Vyhľadávanie |
| `GET /api/categories/list` | Zoznam kategórií |

---

🎉 **Po dokončení budeš môcť rozprávať so svojim finančným asistentom v slovenčine!**

