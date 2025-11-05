# 🤖 GPT Bulk Categorization - Návod na nastavenie

## ✨ Čo to je?

Nový endpoint, ktorý umožňuje ChatGPT agentovi **kategorizovať viaceré transakcie naraz**.

Systém sa **automaticky učí** z GPT priradení - ak GPT zmení "BILLA" na "Potraviny", systém si to zapamätá a budúce transakcie od BILLA automaticky zaradí do Potravín.

---

## 🎯 Výhody

1. **Rýchla kategorizácia** - môžeš povedať: *"Zmeň všetky nezaradené obchody na správne kategórie"*
2. **Automatické učenie** - systém si pamätá tvoje rozhodnutia
3. **Inteligentné** - GPT dokáže rozpoznať obchody a správne ich zaradiť

---

## 🔧 Nastavenie v GPT (ChatGPT.com)

### Krok 1: Otvor GPT editor
1. Choď na [chatgpt.com/gpts/editor](https://chatgpt.com/gpts/editor)
2. Otvor svojho **Finance Assistant SK** GPTa

### Krok 2: Updatni OpenAPI schema
1. Klikni na **Configure** tab
2. Scroll down na **Actions**
3. Klikni na existujúcu Action (alebo **Add action**)
4. Klikni na **Edit** vedľa Schema
5. **Skopíruj celý obsah z `openapi_full.json`** a nahraď ním existujúcu schému
6. Klikni **Save**
7. Klikni **Update** (vpravo hore)

### Krok 3: Test
V ChatGPT konverzácii napíš:
```
Ukáž mi nezaradené transakcie
```

Potom:
```
Zmeň BILLA 122 na Potraviny a Dr.Max na Zdravie a lieky
```

GPT by mal:
1. Nájsť transakcie (pomocou `/api/gpt/transactions/search`)
2. Zmeniť ich kategórie (pomocou `/api/gpt/transactions/bulk-categorize`)
3. Potvrdiť: "Zmenené 2 transakcie, systém sa naučil 2 pravidlá"

---

## 📋 API Endpoint Detail

### URL
```
POST https://finance-management-system-production.up.railway.app/api/gpt/transactions/bulk-categorize
```

### Authentication
```
Bearer <tvoj_gpt_api_secret_key>
```

### Request Body
```json
{
  "updates": [
    {
      "transaction_id": 123,
      "category_name": "Potraviny"
    },
    {
      "transaction_id": 124,
      "category_name": "Zdravie a lieky 💊"
    }
  ]
}
```

### Response
```json
{
  "success": true,
  "updated": 2,
  "learned_rules": 2,
  "total_requested": 2,
  "errors": null
}
```

---

## 💡 Príklady použitia

### Príklad 1: Manuálna kategorizácia
**User:**
```
Zmeň transakciu BILLA 122 na kategóriu Potraviny
```

**GPT:**
1. Zavolá `/api/gpt/transactions/search?merchant=BILLA`
2. Nájde transaction_id: 123
3. Zavolá `/api/gpt/transactions/bulk-categorize`:
   ```json
   {
     "updates": [
       {"transaction_id": 123, "category_name": "Potraviny"}
     ]
   }
   ```
4. Systém:
   - ✅ Zmení kategóriu
   - ✅ Naučí pravidlo: `BILLA → Potraviny`
   - ✅ Budúce transakcie od BILLA budú automaticky Potraviny

### Príklad 2: Hromadná kategorizácia
**User:**
```
Zober všetky nezaradené transakcie a priraď ich do správnych kategórií
```

**GPT:**
1. Zavolá `/api/gpt/transactions/search?category=Nezaradené`
2. Pre každú transakciu:
   - Zhodnotí názov obchodníka/merchant
   - Priradí najlepšiu kategóriu
3. Zavolá `/api/gpt/transactions/bulk-categorize` s celým zoznamom
4. Systém sa naučí všetky pravidlá naraz!

### Príklad 3: Inteligentná kategorizácia
**User:**
```
BOLT a taxify daj do dopravy, McDonald a KFC do reštaurácií
```

**GPT:**
1. Vyhľadá všetky transakcie obsahujúce tieto názvy
2. Kategorizuje ich hromadne
3. Systém si zapamätá:
   - `BOLT → Doprava`
   - `taxify → Doprava`
   - `McDonald → Reštaurácie`
   - `KFC → Reštaurácie`

---

## 🔄 Ako funguje učenie?

1. **GPT zmení kategóriu transakcie**
   ```json
   {"transaction_id": 123, "category_name": "Potraviny"}
   ```

2. **Systém sa pozrie na merchant tej transakcie**
   ```
   Merchant: "BILLA 122, BA"
   ```

3. **Vytvorí pravidlo v tabuľke MerchantRules**
   ```sql
   INSERT INTO MerchantRules (MerchantPattern, CategoryID)
   VALUES ('BILLA', <Potraviny_ID>);
   ```

4. **Budúce transakcie**
   - Príde nová transakcia: `"BILLA 456, BA"`
   - Systém nájde pravidlo: `BILLA → Potraviny`
   - Automaticky zaradí do Potravín!

---

## 🎉 Výsledok

Systém sa postupne učí z tvojich rozhodnutí (alebo GPT rozhodnutí) a stáva sa čím ďalej presnejším!

**Prvýkrát:**
```
BILLA → ❓ Nezaradené
→ GPT zmení na Potraviny
→ ✨ Systém si zapamätá
```

**Druhýkrát:**
```
BILLA → ✅ Automaticky Potraviny!
```

---

## 🐛 Troubleshooting

### "Category not found"
- Kategória neexistuje v databáze
- Skontroluj dostupné kategórie: `/api/gpt/categories/list`
- Vytvor novú kategóriu cez web UI alebo API

### "Unauthorized"
- Skontroluj GPT API Secret Key v Railway environment variables
- Musí byť nastavený `GPT_API_SECRET_KEY` v Railway

### "No updates provided"
- Request body neobsahuje `updates` pole
- Skontroluj JSON format

---

## 📚 Súvisiace súbory

- **`openapi_full.json`** - OpenAPI schema pre GPT Actions
- **`web_ui.py`** - Flask backend s `/api/gpt/transactions/bulk-categorize` endpointom
- **`smart_categorizer.py`** - Smart Categorizer modul (learning system)
- **`MerchantRules` tabuľka** - Databáza naučených pravidiel

---

## ✅ Checklist

- [ ] Railway deployment úspešný
- [ ] OpenAPI schema updated v GPT editor
- [ ] GPT API Secret Key nastavený v Railway
- [ ] Test: "Ukáž nezaradené transakcie"
- [ ] Test: "Zmeň XYZ na kategóriu ABC"
- [ ] Skontroluj, že systém sa učí (check MerchantRules tabuľka)

---

🎯 **Ready to go!** Teraz môžeš kategorizovať transakcie cez ChatGPT agenta!

