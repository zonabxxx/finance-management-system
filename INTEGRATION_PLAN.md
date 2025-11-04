# Smart Categorizer Integration - Manuálne kroky

## Čo už je hotové:
✅ MerchantRules tabuľka vytvorená v DB
✅ smart_categorizer.py modul vytvorený  
✅ Import pridaný do web_ui.py
✅ get_smart_categorizer() funkcia pridaná

## ČO MUSÍŠ UROBIŤ:

### 1. Nahraď starú kategorizáciu v web_ui.py

**Nájdi tento blok** (riadky ~1217-1304):
```python
# Automatická kategorizácia
try:
    # 80+ riadkov starého kódu s hardcoded keywords...
```

**Nahraď ho týmto** (iba 23 riadkov):
```python
# 🧠 Smart Categorization with Learning + AI
try:
    # Získaj ID novo vytvorenej transakcie
    last_id_query = "SELECT TransactionID FROM Transactions ORDER BY TransactionID DESC LIMIT 1;"
    last_id_result = turso_query(last_id_query)
    
    if last_id_result and 'rows' in last_id_result and len(last_id_result['rows']) > 0:
        transaction_id = int(last_id_result['rows'][0][0]['value'])
        
        # Použij Smart Categorizer
        categorizer = get_smart_categorizer()
        category_id = categorizer.categorize(merchant, description, amount)
        
        # Ak našiel kategóriu, priradíme ju
        if category_id:
            update_query = f"""
            UPDATE Transactions 
            SET CategoryID = {category_id}, CategorySource = 'Auto'
            WHERE TransactionID = {transaction_id};
            """
            turso_query(update_query)
            print(f"   ✅ Smart categorized: CategoryID={category_id}")
except Exception as e:
    print(f"   ⚠️  Auto-categorization failed: {e}")
```

### 2. Pridaj learning pri manuálnom priradení

**V web_ui.py, nájdi funkciu** `update_transaction_category` (okolo riadku 520):

**Pridaj tento kód na koniec funkcie** (pred return):
```python
# Learn from manual assignment
categorizer = get_smart_categorizer()
categorizer.learn_from_manual_assignment(transaction_id, category_id)
```

### 3. Commit a push

```bash
git add smart_categorizer.py web_ui.py create_merchant_rules.sql
git commit -m "🧠 Add Smart Categorizer with AI + Learning"
git push origin main
```

---

## Alebo môžem pushnúť to čo je hotové a dopracujem integráciu v ďalšom nasadení?
