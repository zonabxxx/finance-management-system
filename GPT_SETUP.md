# 🤖 Napojenie ChatGPT GPT na tvoju finančnú databázu

## 📋 Prehľad

Tento návod ti ukáže, ako napojiť **vlastný ChatGPT GPT** na tvoju Turso databázu, aby si mohol pýtať otázky typu:
- *"Koľko som míňal tento mesiac?"*
- *"Kde míňam najviac peňazí?"*
- *"Ukáž mi výdavky za kávu"*

---

## 🚀 Krok 1: Nainštaluj závislosti

```bash
pip install flask flask-cors
```

---

## 🔧 Krok 2: Nastav API kľúč

1. Otvor `.env` súbor
2. Pridaj:
```bash
API_KEY=tvoj-super-tajny-api-key-123456789
```

**💡 Tip:** Vygeneruj silný API kľúč pomocou:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 🏃 Krok 3: Spusti API server

```bash
python3 api_server.py
```

Server bude bežať na: **http://localhost:5000**

---

## 🌐 Krok 4: Sprístupni server cez internet

ChatGPT potrebuje prístup k tvojmu API cez internet. Použiť môžeš **ngrok**:

### Inštalácia ngrok:
```bash
brew install ngrok
```

### Spustenie:
```bash
ngrok http 5000
```

Dostaneš URL typu: `https://abc123.ngrok.io`

---

## 🤖 Krok 5: Vytvor GPT na OpenAI

1. **Choď na:** https://chat.openai.com/gpts/editor
2. **Vyplň:**
   - **Name:** `Finančný Asistent SK`
   - **Description:** `Pomáha analyzovať výdavky a príjmy z Tatra banky`
   
3. **Instructions:**
```
Si finančný asistent pre slovenského používateľa. 

Máš prístup k jeho finančným dátam cez API. Používateľ ti môže klásť otázky v slovenčine o:
- Výdavkoch a príjmoch
- Transakciách podľa kategórií
- Top obchodníkoch kde míňa najviac
- Mesačných štatistikách

Vždy odpovedaj v **slovenčine** a používaj emoji pre prehľadnosť. 
Keď zobrazuješ sumy, formátuj ich ako "-15.50 EUR" alebo "+1000.00 EUR".
Keď zobrazuješ dátumy, použi slovenský formát (napr. 2.11.2025).

Ak používateľ položí otázku o výdavkoch, automaticky zavolaj príslušný API endpoint.
```

4. **Conversation starters:**
   - `Koľko som míňal tento mesiac?`
   - `Kde míňam najviac peňazí?`
   - `Ukáž mi posledné transakcie`
   - `Aké sú moje mesačné výdavky?`

---

## 🔗 Krok 6: Pridaj Actions (API integráciu)

1. V GPT editore klikni na **"Create new action"**
2. **Authentication:** Vyber `API Key`
   - **Auth Type:** `Bearer`
   - **API Key:** `tvoj-super-tajny-api-key-123456789` (z .env)
3. **Schema:** Skopíruj obsah súboru `openapi_spec.json`
4. **Server URL:** Nahraď `http://localhost:5000` tvojím ngrok URL (napr. `https://abc123.ngrok.io`)

---

## ✅ Krok 7: Otestuj GPT

Napíš svojmu GPT:
```
Koľko som míňal za posledných 30 dní?
```

GPT by mal zavolať API a vrátiť ti údaje z databázy! 🎉

---

## 📊 Dostupné API endpointy

| Endpoint | Popis | Príklad |
|----------|-------|---------|
| `/api/transactions/summary?days=30` | Celkové výdavky a príjmy | Koľko som míňal tento mesiac? |
| `/api/transactions/recent?limit=10` | Posledných N transakcií | Ukáž posledné transakcie |
| `/api/transactions/by-category?days=30` | Výdavky po kategóriách | Kde míňam najviac? |
| `/api/transactions/top-merchants?limit=10` | Top obchodníci | V ktorých obchodoch nakupujem? |
| `/api/transactions/monthly?months=6` | Mesačné štatistiky | Mesačné výdavky za polrok |
| `/api/transactions/search?merchant=TESCO` | Vyhľadávanie | Koľko som utratil v TESCU? |

---

## 🔒 Bezpečnosť

- **API kľúč** je potrebný pre všetky requesty
- Používaj **silný API kľúč** (min. 32 znakov)
- **Ngrok URL** zdieľaj iba s OpenAI
- Pre produkciu použi **vlastný server** s HTTPS

---

## 🆘 Riešenie problémov

### API nefunguje?
```bash
# Skontroluj či server beží
curl http://localhost:5000/api/health
```

### GPT nevidí API?
- Skontroluj či ngrok beží: `ngrok http 5000`
- Aktualizuj Server URL v GPT Actions

### "Unauthorized" chyba?
- Skontroluj API kľúč v .env
- Skontroluj API kľúč v GPT Authentication

---

## 🎉 Hotovo!

Teraz máš vlastného ChatGPT finančného asistenta! 🤖💰

**Príklady otázok:**
- *"Koľko som dnes utratil?"*
- *"Za čo míňam najviac tento mesiac?"*
- *"Porovnaj výdavky za október a november"*
- *"Koľko som celkovo zaplatil v Kauflande?"*

