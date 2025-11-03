# 📧 Nastavenie B-mail Email Receivera

Tento návod vás prevedie nastavením automatického prijímania a spracovania B-mail notifikácií z Tatra banky.

## 🚀 Krok za krokom

### 1. Vytvorenie Gmail účtu

1. **Vytvorte nový Gmail účet** na https://accounts.google.com/signup
   - Príklad: `vasemeno.finance@gmail.com`
   - Tento účet bude používaný **výhradne** pre B-mail notifikácie

2. **Povoľte 2-Factor Authentication (2FA)**
   - Prejdite na: https://myaccount.google.com/security
   - Zapnite "2-Step Verification"

3. **Vytvorte App Password**
   - Prejdite na: https://myaccount.google.com/apppasswords
   - Zvoľte "Mail" a "Other (Custom name)"
   - Zadajte názov: "Finance Tracker"
   - **Skopírujte vygenerované heslo** (16 znakov)

### 2. Nastavenie B-mail v Tatra banke

1. **Prihláste sa do Internet Banking Business**
   - https://www.tatrabanka.sk

2. **Prejdite na B-mail nastavenia:**
   ```
   Nastavenia → Upozornenia → B-mail
   ```

3. **Pridajte nový B-mail:**
   - Email adresa: `vasemeno.finance@gmail.com`
   - Vyberte typy notifikácií:
     - ✅ Prijaté platby
     - ✅ Odoslané platby
     - ✅ Platby kartou
     - ✅ Výbery z bankomatu
   
4. **Aktivujte B-mail:**
   - Skontrolujte email
   - Kliknite na aktivačný odkaz

### 3. Konfigurácia Email Receivera

1. **Otvorte súbor `email_receiver.py`**

2. **Upravte prihlasovacie údaje:**
   ```python
   EMAIL_ADDRESS = "vasemeno.finance@gmail.com"  # Váš Gmail
   EMAIL_PASSWORD = "abcd efgh ijkl mnop"        # App Password z kroku 1.3
   ```

3. **Uložte súbor**

### 4. Testovanie

#### Test 1: Pripojenie k Gmail
```bash
python3 email_receiver.py
```

Očakávaný výstup:
```
📧 B-mail Email Receiver
==================================================
✅ Pripojený k vasemeno.finance@gmail.com
📬 Kontrolujem nové B-mail notifikácie...
📭 Žiadne nové notifikácie
```

#### Test 2: Simulácia B-mail notifikácie
1. Pošlite si test email na `vasemeno.finance@gmail.com`
2. V predmete: `B-mail notifikácia - Platba kartou`
3. V tele emailu:
```
Transakcia: Platba kartou
Dátum: 02.11.2025 15:30
Suma: -25,50 EUR
Obchodník: TESCO STORES SK
Účet: SK3112000000198742637541
Variable symbol: 1234567890
CO2 footprint: 3.2 kg
```

4. Spustite receiver:
```bash
python3 email_receiver.py
```

Očakávaný výstup:
```
📨 Našiel som 1 nových notifikácií

--- Email 1/1 ---
Predmet: B-mail notifikácia - Platba kartou
💰 Suma: -25.5 EUR
🏪 Obchodník: TESCO STORES SK
📅 Dátum: 2025-11-02 15:30:00
✅ Transakcia uložená: TESCO STORES SK - -25.5 EUR

==================================================
✅ Úspešne spracovaných: 1/1
```

### 5. Overenie v databáze

```bash
turso db shell financa-sprava "SELECT * FROM Transactions ORDER BY TransactionDate DESC LIMIT 5;"
```

## 📋 B-mail formát - Príklady

### Platba kartou
```
Dobrý deň,

informujeme Vás o pohybe na Vašom účte.

Transakcia: Platba kartou
Dátum: 02.11.2025 15:30:45
Suma: -15,50 EUR
Obchodník: TESCO STORES SK
Karta: **** **** **** 1234
Zostatok: 1 234,56 EUR
CO2 footprint: 2.5 kg

S pozdravom,
Tatra banka
```

### Prevod
```
Dobrý deň,

informujeme Vás o pohybe na Vašom účte.

Transakcia: Odoslaný prevod
Dátum: 01.11.2025 10:15:00
Suma: -150,00 EUR
Príjemca: Slovenský plynárenský priemysel
Účet: SK3112000000198742637541
Variable symbol: 1234567890
Constant symbol: 0308
Specific symbol: 9876543210
Správa pre príjemcu: Faktúra č. 2025001
Zostatok: 1 084,56 EUR

S pozdravom,
Tatra banka
```

## 🔄 Automatizácia (Cron Job)

Pre pravidelné spúšťanie každých 5 minút:

1. **Otvorte crontab:**
```bash
crontab -e
```

2. **Pridajte riadok:**
```bash
*/5 * * * * cd /Users/polepime.sk/Documents/cursor_workspace/Sprava\ financii && /usr/local/bin/python3 email_receiver.py >> logs/email_receiver.log 2>&1
```

3. **Vytvorte log priečinok:**
```bash
mkdir -p logs
```

## ⚠️ Bezpečnosť

1. **Nikdy nezdieľajte App Password**
2. **Použite `.env` súbor pre credentials** (už máte nastavený)
3. **Pravidelne kontrolujte logy**
4. **Nastavte Gmail filtrovanie** - iba B-mail od `bmail@tatrabanka.sk`

## 🐛 Riešenie problémov

### "Authentication failed"
- Skontrolujte App Password
- Overte že 2FA je zapnuté
- Skúste vygenerovať nový App Password

### "No module named 'imaplib'"
- Imaplib je súčasť Python štandardnej knižnice
- Skúste: `python3 -m pip install --upgrade setuptools`

### "SSL: CERTIFICATE_VERIFY_FAILED"
- Gmail IMAP by mal fungovať (na rozdiel od libsql)
- Ak nie, skúste: `pip3 install --upgrade certifi`

## 📞 Kontakt na podporu

- Tatra banka B-mail: https://www.tatrabanka.sk/sk/business/e-banking/b-mail/
- Gmail podpora: https://support.google.com/mail/

## ✅ Checklist

- [ ] Gmail účet vytvorený
- [ ] 2FA zapnuté
- [ ] App Password vygenerované
- [ ] B-mail aktivovaný v Tatra banke
- [ ] `email_receiver.py` nakonfigurovaný
- [ ] Test email odoslaný a spracovaný
- [ ] Transakcia viditeľná v databáze
- [ ] (Voliteľné) Cron job nastavený

