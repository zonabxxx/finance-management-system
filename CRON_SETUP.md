# 📧 Automatická synchronizácia B-mailov cez Webhook + Cron

## 🎯 Prečo webhook namiesto workera?

Google blokuje IMAP prihlásenia z Railway (cloud IP adresy). 
Riešenie: External cron volá náš endpoint, ktorý interné pripojí k Gmail.

---

## 🚀 Setup kroky:

### 1. Over že máš API_SECRET_KEY v Railway

Railway Dashboard → Variables → Over:
```
API_SECRET_KEY=tvoj-tajny-kluc-123
```

*(Vygeneruj náhodný reťazec aspoň 20 znakov)*

---

### 2. Test endpoint lokálne

```bash
curl -X POST "http://localhost:3000/api/sync-emails?secret=tvoj-tajny-kluc-123"
```

Odpoveď:
```json
{
  "success": true,
  "message": "Email sync completed",
  "checked": 2,
  "processed": 0,
  "errors": 0
}
```

---

### 3. Test endpoint na Railway

```bash
curl -X POST "https://finance-management-system-production.up.railway.app/api/sync-emails?secret=tvoj-tajny-kluc-123"
```

---

### 4. Nastav cron-job.org (ZADARMO)

1. Choď na: **https://cron-job.org**
2. **Sign Up** (zadarmo, žiadna kreditka)
3. Po prihlásení klikni **Create cronjob**

**Nastavenia:**

| Pole | Hodnota |
|------|---------|
| **Title** | Finance B-mail Sync |
| **Address (URL)** | `https://finance-management-system-production.up.railway.app/api/sync-emails?secret=tvoj-tajny-kluc-123` |
| **Request method** | `POST` |
| **Execution schedule** | `Every minute` (*/1 * * * *) |
| **Timeout** | `30 seconds` |

4. Klikni **Create**
5. ✅ **Hotovo!**

---

### 5. Over že funguje

**cron-job.org Dashboard:**
- Uvidíš zelené ✅ pri každom úspešnom calle
- Klikni na job → **History** → vidíš response

**Railway Logs:**
- Malo by byť vidieť API cally každú minútu
- `POST /api/sync-emails`

**Tvoja aplikácia:**
- Choď na `/transactions`
- Mali by sa objaviť nové transakcie z B-mailov

---

## 🎯 Výsledok:

✅ B-maily sa synchronizujú každú minútu  
✅ Railway nemusí držať worker proces  
✅ Gmail autentifikácia funguje  
✅ Zadarmo (cron-job.org free tier: 50 jobs, 60s interval)  

---

## 🔧 Troubleshooting:

### Railway vraća 401 Unauthorized

→ Skontroluj že `API_SECRET_KEY` v Railway sedí s URL parametrom `?secret=...`

### Railway vraća 500 Error

→ Pozri Deploy Logs, pravdepodobne chybajú EMAIL_* env variables

### cron-job.org ukazuje timeout

→ Zvýš timeout na 60s (Gmail connection môže trvať dlhšie)

---

## 📊 Monitoring:

**Sleduj koľko B-mailov sa spracúva:**

```bash
curl "https://tvoja-app.railway.app/api/sync-emails?secret=KEY" | jq
```

Response:
```json
{
  "success": true,
  "checked": 2,      ← našiel 2 B-maily
  "processed": 0,    ← 0 nových (už boli v DB)
  "errors": 0
}
```

---

🎉 **Teraz máš plne automatický systém bez lokálneho servera!**
