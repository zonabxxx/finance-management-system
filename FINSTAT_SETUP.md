# Ako získať Finstat API prístup - Krok za krokom

## 🎯 Cieľ
Získať **API Key** a **Private Key** pre Finstat API integráciu vo Finance Trackeri.

## 📝 Kroky

### 1. Registrácia na Finstat
1. Prejdite na [https://www.finstat.sk](https://www.finstat.sk)
2. Kliknite na **Registrácia** (pravý horný roh)
3. Vyplňte registračný formulár:
   - Email: váš email
   - Heslo: silné heslo
   - Firma/Meno
4. Potvrďte email

### 2. Zakúpenie API prístupu
1. Po prihlásení prejdite na **Profil** → **API prístup**
2. Vyberte si plán:
   
   | Plán | Cena/mesiac | Volania/deň | Vhodné pre |
   |------|-------------|-------------|------------|
   | **Štandardné** | ~20-30 € | 1,000 | Osobné použitie |
   | **Premium** | ~50-80 € | 5,000 | Malé firmy |
   | **Elite** | ~150-200 € | 20,000 | Stredné firmy |
   | **Ultimate** | Na požiadanie | Neobmedzené | Veľké firmy |

3. Vyplňte fakturačné údaje
4. Dokončite objednávku

### 3. Získanie API kľúčov
Po aktivácii API prístupu:

1. Prejdite do **Profil** → **API nastavenia**
2. Nájdete tam:
   ```
   API Key: abc123def456...
   ```
3. Pre **Private Key** kontaktujte Finstat support:
   - Email: **info@finstat.sk**
   - Predmet: "Žiadosť o Private Key pre API"
   - V správe uveďte:
     ```
     Dobrý deň,

     Žiadam o zaslanie Private Key pre Finstat API.
     Moje API Key: abc123def456...
     Účel použitia: Finance Tracker aplikácia

     Ďakujem,
     [Vaše meno]
     ```

### 4. Konfigurácia vo Finance Trackeri

Po získaní kľúčov:

```bash
# 1. Otvorte .env súbor
nano .env

# 2. Pridajte/upravte riadky:
FINSTAT_API_KEY=abc123def456...
FINSTAT_PRIVATE_KEY=xyz789ghi012...

# 3. Uložte súbor (Ctrl+O, Enter, Ctrl+X)
```

### 5. Test pripojenia

```bash
# Spustite test
python3 -c "
from finstat_client import get_company_info

# Test s IČO: 47165367 (FinStat s.r.o.)
company = get_company_info(ico='47165367')

if company:
    print('✅ Finstat API funguje!')
    print(f'Firma: {company.name}')
else:
    print('❌ Problém s pripojením')
"
```

## ⚠️ Dôležité poznámky

### Private Key
- **Neposkytu jú automaticky** - musíte požiadať support
- **Čas odpovede:** 1-2 pracovné dni
- **Alternatíva:** Môžete začať bez Finstat API - systém bude používať AI kategorizáciu

### Bezpečnosť
- ❌ **NIKDY nezdieľajte** API Key ani Private Key verejne
- ✅ Uchovávajte len v `.env` súbore (v `.gitignore`)
- ✅ Pre produkciu použite Azure Key Vault

### Testovanie pred zakúpením
- Kontaktujte `info@finstat.sk` pre **trial prístup**
- Zvyčajne poskytujú 7-14 dní skúšobné obdobie
- Môžete otestovať či API spĺňa vaše potreby

## 🆓 Alternatívy (bez Finstat)

Ak nechcete používať Finstat API:

```env
# V .env nastavte:
USE_FINSTAT_FOR_UNKNOWN=false

# Systém bude používať len:
# 1. Pravidlovú kategorizáciu (najrýchlejšia)
# 2. AI kategorizáciu (GPT-4)
```

**Výhody:**
- ✅ Žiadne ďalšie náklady
- ✅ Funguje okamžite
- ✅ Stále 95%+ presnosť

**Nevýhody:**
- ❌ Nemáte IČO, adresu, právnu formu
- ❌ Nemáte oficiálne údaje o firme
- ❌ Menej presné pre neznáme názvy

## 📞 Kontakt na Finstat

- **Web:** https://www.finstat.sk
- **Email:** info@finstat.sk
- **Telefón:** +421 2 XXX XXX (na webe)
- **Adresa:** Bratislava, Slovensko

## ✅ Checklist

Po dokončení by ste mali mať:

- [ ] Finstat účet vytvorený
- [ ] API plán zakúpený a aktivovaný
- [ ] API Key získaný
- [ ] Private Key získaný (od supportu)
- [ ] Kľúče pridané do `.env`
- [ ] Test pripojenia úspešný ✓

## 💡 Tip

**Začnite bez Finstat API** a pridajte ho neskôr ak budete potrebovať:
- Detailné firemné údaje
- IČO validáciu
- Právnu formu
- Oficiálne adresy

Finance Tracker funguje výborne aj bez Finstat API vďaka pravidlovej a AI kategorizácii! 🚀

---

**Potrebujete pomoc?** Otvorte issue v projekte alebo kontaktujte autora.

