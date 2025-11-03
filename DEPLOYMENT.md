# Deployment Guide - Finance Tracker

Tento guide vás prevedie procesom nasadenia Finance Tracker systému do Azure.

## Predpoklady

### Účty a prístupy
- [x] Azure účet s aktívnou subscripciou
- [x] OpenAI API kľúč ([platform.openai.com](https://platform.openai.com))
- [x] Finstat API kľúč ([finstat.sk/api](https://www.finstat.sk/api))
- [x] Azure CLI nainštalované ([install guide](https://docs.microsoft.com/cli/azure/install-azure-cli))
- [x] Python 3.9+ nainštalovaný
- [x] Azure Functions Core Tools ([install guide](https://docs.microsoft.com/azure/azure-functions/functions-run-local))

### Lokálne nástroje
```bash
# Azure CLI
az --version

# Python
python --version  # >= 3.9

# Azure Functions Core Tools
func --version    # >= 4.0
```

## Krok za krokom

### 1. Vytvorenie Azure zdrojov

#### 1.1 Resource Group
```bash
# Vytvorte resource group
az group create \
  --name finance-tracker-rg \
  --location westeurope
```

#### 1.2 Azure SQL Database
```bash
# SQL Server
az sql server create \
  --name finance-tracker-sql \
  --resource-group finance-tracker-rg \
  --location westeurope \
  --admin-user sqladmin \
  --admin-password "YourStrongPassword123!"

# Firewall pravidlo pre Azure services
az sql server firewall-rule create \
  --resource-group finance-tracker-rg \
  --server finance-tracker-sql \
  --name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# Firewall pravidlo pre vašu IP (pre setup)
MY_IP=$(curl -s ifconfig.me)
az sql server firewall-rule create \
  --resource-group finance-tracker-rg \
  --server finance-tracker-sql \
  --name AllowMyIP \
  --start-ip-address $MY_IP \
  --end-ip-address $MY_IP

# Database
az sql db create \
  --resource-group finance-tracker-rg \
  --server finance-tracker-sql \
  --name finance_tracker \
  --service-objective S0 \
  --backup-storage-redundancy Local
```

#### 1.3 Storage Account
```bash
az storage account create \
  --name financetrackerstore \
  --resource-group finance-tracker-rg \
  --location westeurope \
  --sku Standard_LRS
```

#### 1.4 Application Insights
```bash
az monitor app-insights component create \
  --app finance-tracker-insights \
  --location westeurope \
  --resource-group finance-tracker-rg
```

#### 1.5 Function App
```bash
az functionapp create \
  --resource-group finance-tracker-rg \
  --consumption-plan-location westeurope \
  --runtime python \
  --runtime-version 3.9 \
  --functions-version 4 \
  --name finance-tracker-func \
  --storage-account financetrackerstore \
  --app-insights finance-tracker-insights \
  --os-type Linux
```

### 2. Konfigurácia databázy

#### 2.1 Spustite SQL schema
```bash
# Stiahnite SQL tools
# Windows: https://aka.ms/sqlcmd
# Linux: apt-get install sqlcmd
# Mac: brew install sqlcmd

# Spustite schema
sqlcmd \
  -S finance-tracker-sql.database.windows.net \
  -d finance_tracker \
  -U sqladmin \
  -P "YourStrongPassword123!" \
  -i database_schema.sql
```

Alebo použite Azure Data Studio / SQL Server Management Studio:
1. Pripojte sa na `finance-tracker-sql.database.windows.net`
2. Otvorte `database_schema.sql`
3. Spustite skript

### 3. Konfigurácia Function App

#### 3.1 Nastavte environment variables
```bash
# Získajte connection string
SQL_CONNECTION=$(az sql db show-connection-string \
  --client ado.net \
  --server finance-tracker-sql \
  --name finance_tracker \
  | sed "s/<username>/sqladmin/g" \
  | sed "s/<password>/YourStrongPassword123!/g")

# Nastavte app settings
az functionapp config appsettings set \
  --name finance-tracker-func \
  --resource-group finance-tracker-rg \
  --settings \
    AZURE_SQL_SERVER=finance-tracker-sql.database.windows.net \
    AZURE_SQL_DATABASE=finance_tracker \
    AZURE_SQL_USERNAME=sqladmin \
    AZURE_SQL_PASSWORD="YourStrongPassword123!" \
    OPENAI_API_KEY="sk-your-openai-api-key" \
    OPENAI_MODEL="gpt-4-turbo-preview" \
    OPENAI_ASSISTANT_ID="" \
    FINSTAT_API_KEY="your-finstat-api-key" \
    FINSTAT_API_URL="https://www.finstat.sk/api" \
    AI_CONFIDENCE_THRESHOLD=0.7 \
    USE_FINSTAT_FOR_UNKNOWN=true \
    ENABLE_WEB_SCRAPING=true
```

#### 3.2 Nasaďte kód
```bash
# Prihláste sa do Azure
az login

# Nasaďte Function App
func azure functionapp publish finance-tracker-func --python
```

#### 3.3 Získajte Function URL a kľúč
```bash
# Získajte Function App URL
FUNC_URL=$(az functionapp show \
  --name finance-tracker-func \
  --resource-group finance-tracker-rg \
  --query defaultHostName -o tsv)

echo "Function App URL: https://$FUNC_URL"

# Získajte Function Key
FUNC_KEY=$(az functionapp keys list \
  --name finance-tracker-func \
  --resource-group finance-tracker-rg \
  --query functionKeys.default -o tsv)

echo "Function Key: $FUNC_KEY"
```

### 4. Vytvorenie Logic App

#### 4.1 Cez Azure Portal

1. Prejdite na Azure Portal → Create Resource → Logic App
2. **Základné nastavenia:**
   - Name: `finance-tracker-logic`
   - Resource Group: `finance-tracker-rg`
   - Location: `West Europe`
   - Plan Type: `Consumption`

3. **Workflow Designer:**
   - Trigger: `When a new email arrives (V3)` (Office 365 Outlook)
   - Filter:
     - Folder: `Inbox`
     - Subject Filter: `Pohyby na účte`
     - Include Attachments: `No`
   
4. **Pridajte akciu:**
   - Action: `HTTP`
   - Method: `POST`
   - URI: `https://finance-tracker-func.azurewebsites.net/api/process-email?code=FUNC_KEY`
   - Headers:
     ```json
     {
       "Content-Type": "application/json"
     }
     ```
   - Body:
     ```json
     {
       "body": "@{triggerBody()?['body']}",
       "subject": "@{triggerBody()?['subject']}",
       "from": "@{triggerBody()?['from']}",
       "receivedDateTime": "@{triggerBody()?['receivedDateTime']}"
     }
     ```

5. **Pridajte podmienku (voliteľné):**
   - Condition: `@equals(body('HTTP')?['success'], true)`
   - If true: Log success
   - If false: Send alert email

6. **Uložte a aktivujte**

#### 4.2 Importovanie šablóny (alternatíva)

```bash
# Stiahnite šablónu
wget https://github.com/your-repo/azure_logic_app.json

# Nasaďte cez Azure CLI
az logic workflow create \
  --resource-group finance-tracker-rg \
  --name finance-tracker-logic \
  --definition @azure_logic_app.json \
  --location westeurope
```

### 5. Nastavenie B-mail

1. **Prihláste sa do internetbankingu**

2. **Prejdite do Nastavenia → B-mail / Notifikácie**

3. **Vytvorte B-mail:**
   - Typ: Pohyby na účte
   - Email: `your-email@yourdomain.com` (musí byť pripojený na Logic App)
   - Jazyk: Slovenčina

4. **Aktivujte notifikácie:**
   - ✅ Kredit od zvolenej sumy: `0,01 EUR`
   - ✅ Debet od zvolenej sumy: `0,01 EUR`
   - ✅ Avízo o nezrealizovanej platbe
   - ❌ Pozdržať nočné správy (vypnite pre okamžité spracovanie)
   - ✅ Denné zostatky na účte (voliteľné)

5. **Uložte nastavenie**

### 6. Testovanie

#### 6.1 Test Function App lokálne
```bash
# Aktivujte virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# alebo
venv\Scripts\activate     # Windows

# Nainštalujte závislosti
pip install -r requirements.txt

# Spustite lokálne
func start

# Testujte endpoint
curl -X POST http://localhost:7071/api/process-email \
  -H "Content-Type: application/json" \
  -d '{
    "body": "3. novembra 2025\n\nKAUFLAND 1120\nPlatba kartou 4405**9645\n\n23,00 EUR\n4,80 kg CO₂e",
    "subject": "Pohyby na účte"
  }'
```

#### 6.2 Test Azure Function
```bash
curl -X POST https://finance-tracker-func.azurewebsites.net/api/process-email?code=$FUNC_KEY \
  -H "Content-Type: application/json" \
  -d '{
    "body": "3. novembra 2025\n\nKAUFLAND 1120\nPlatba kartou 4405**9645\n\n23,00 EUR\n4,80 kg CO₂e",
    "subject": "Pohyby na účte"
  }'
```

#### 6.3 Test Logic App
1. Pošlite si testovací email s predmetom "Pohyby na účte"
2. Prejdite do Logic App → Run History
3. Skontrolujte, či sa spustil trigger
4. Overte výsledok v databáze

#### 6.4 Test databázy
```sql
-- Pripojte sa na SQL database a spustite:

-- Počet transakcií
SELECT COUNT(*) FROM Transactions;

-- Posledné transakcie
SELECT TOP 10 
    TransactionDate,
    MerchantName,
    Amount,
    CategorySource
FROM Transactions
ORDER BY TransactionDate DESC;

-- Kategórie
SELECT 
    c.Name,
    COUNT(*) as Count,
    SUM(t.Amount) as Total
FROM Transactions t
JOIN Categories c ON t.CategoryID = c.CategoryID
GROUP BY c.Name
ORDER BY Total DESC;
```

### 7. ChatGPT Agent setup

#### 7.1 Vytvorte OpenAI Assistanta

Prejdite na [platform.openai.com/assistants](https://platform.openai.com/assistants):

1. Kliknite **Create Assistant**
2. **Name:** Finance Assistant SK
3. **Instructions:**
```
Si AI finančný asistent pre slovenského používateľa. 
Pomáhaš analyzovať výdavky a príjmy, odpovedáš na otázky 
o finančných transakciách a poskytuje insights o útrateach.
Vždy odpovedáš v slovenčine.
```
4. **Model:** gpt-4-turbo-preview
5. **Tools:** Pridajte Functions (z `chatgpt_agent.py`)
6. **Uložte a skopírujte Assistant ID**

#### 7.2 Aktualizujte Function App settings
```bash
az functionapp config appsettings set \
  --name finance-tracker-func \
  --resource-group finance-tracker-rg \
  --settings \
    OPENAI_ASSISTANT_ID="asst_xxxxxxxxxxxxx"
```

#### 7.3 Test agenta
```python
from chatgpt_agent import ask_finance_question

response = ask_finance_question("Koľko som minul tento mesiac?")
print(response['response'])
```

## 8. Monitoring a údržba

### Application Insights
```bash
# Otvorte Application Insights
az monitor app-insights component show \
  --app finance-tracker-insights \
  --resource-group finance-tracker-rg
```

### Logy
```bash
# Function App logy
az functionapp log tail \
  --name finance-tracker-func \
  --resource-group finance-tracker-rg
```

### Metriky
- Azure Portal → Function App → Metrics
  - Execution Count
  - Execution Duration
  - Errors

## 9. Bezpečnosť

### Odporúčania:
1. ✅ Použite Azure Key Vault pre secrets
2. ✅ Nastavte Managed Identity pre Function App
3. ✅ Obmedzte SQL firewall len na Azure services
4. ✅ Aktivujte Azure AD authentication
5. ✅ Pravidelne rotujte API kľúče

## 10. Troubleshooting

### Function nezbeha
```bash
# Skontrolujte logy
az functionapp log tail --name finance-tracker-func --resource-group finance-tracker-rg

# Reštartujte
az functionapp restart --name finance-tracker-func --resource-group finance-tracker-rg
```

### SQL connection errors
- Skontrolujte firewall rules
- Overte connection string
- Testujte pripojenie cez sqlcmd

### Logic App sa nespúšťa
- Overte Office 365 connector permissions
- Skontrolujte email filter
- Pozrite Run History pre errors

## 11. Náklady optimalizácia

### Consumption Plan náklady:
- Function App: prvých 1M execution zadarmo
- SQL Database S0: ~€15/mesiac
- Logic App: prvých 4000 actions zadarmo
- OpenAI API: ~$0.01/transakcia

### Tips:
- Použite S0 tier pre SQL (nie vyššie)
- Consumption plan pre Functions
- Cachujte Finstat results
- Batch processing pre AI calls

---

## ✅ Checklist

- [ ] Azure resource group vytvorený
- [ ] SQL Database vytvorená a schema nainštalovaná
- [ ] Function App nasadená
- [ ] Environment variables nastavené
- [ ] Logic App nakonfigurovaná
- [ ] B-mail nastavený
- [ ] OpenAI Assistant vytvorený
- [ ] Otestované end-to-end
- [ ] Monitoring aktivovaný
- [ ] Bezpečnosť nastavená

## 🎉 Hotovo!

Váš Finance Tracker systém je teraz online a automaticky spracúva transakcie!

**Next steps:**
- Sledujte prvé transakcie v databáze
- Testujte ChatGPT agenta
- Nastavte dashboardy a upozornenia
- Enjoy automatizovanú správu financií! 🚀

