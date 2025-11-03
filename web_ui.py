#!/usr/bin/env python3
"""
Flask Web UI - Dashboard pre správu financií (Railway compatible - HTTP API)
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Turso database connection via HTTP API
TURSO_DATABASE_URL = os.getenv('TURSO_DATABASE_URL', '')
TURSO_AUTH_TOKEN = os.getenv('TURSO_AUTH_TOKEN', '')

# Convert libsql:// URL to https://
if TURSO_DATABASE_URL.startswith('libsql://'):
    TURSO_HTTP_URL = TURSO_DATABASE_URL.replace('libsql://', 'https://')
else:
    TURSO_HTTP_URL = TURSO_DATABASE_URL

def turso_query(sql: str):
    """Vykonanie SQL query v Turso databáze cez HTTP API"""
    try:
        response = requests.post(
            f"{TURSO_HTTP_URL}/v2/pipeline",
            headers={
                "Authorization": f"Bearer {TURSO_AUTH_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "requests": [
                    {"type": "execute", "stmt": {"sql": sql}}
                ]
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Parse response
            if result.get('results') and len(result['results']) > 0:
                query_result = result['results'][0]['response']['result']
                
                # Extract columns and rows
                columns = [col['name'] for col in query_result.get('cols', [])]
                rows = query_result.get('rows', [])
                
                # Convert to dict format
                data = []
                for row in rows:
                    row_dict = {}
                    for i, col_name in enumerate(columns):
                        # Handle Turso's value format: {"type": "integer", "value": "123"}
                        cell = row[i]
                        if isinstance(cell, dict) and 'value' in cell:
                            # Extract value from dict
                            value = cell['value']
                            # Convert string numbers to actual numbers
                            if cell.get('type') == 'integer':
                                row_dict[col_name] = int(value) if value is not None else None
                            elif cell.get('type') == 'real':
                                row_dict[col_name] = float(value) if value is not None else None
                            else:
                                row_dict[col_name] = value
                        else:
                            # Direct value
                            row_dict[col_name] = cell
                        
                        # Also add lowercase version for compatibility
                        row_dict[col_name.lower()] = row_dict[col_name]
                    data.append(row_dict)
                
                return {"success": True, "data": data}
            else:
                return {"success": True, "data": []}
        else:
            print(f"❌ Database error: {response.status_code} - {response.text}")
            return {"success": False, "error": f"HTTP {response.status_code}", "data": []}
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return {"success": False, "error": str(e), "data": []}


@app.route('/')
def index():
    """Hlavná stránka s dashboardom"""
    return render_template('index.html')


@app.route('/transactions')
def transactions_page():
    """Stránka so zoznamom transakcií"""
    return render_template('transactions.html')


@app.route('/categories')
def categories_page():
    """Stránka so správou kategórií"""
    return render_template('categories.html')


@app.route('/settings')
def settings_page():
    """Stránka s nastaveniami"""
    return render_template('settings.html')


@app.route('/api/accounts/list', methods=['GET'])
def accounts_list():
    """Zoznam všetkých účtov"""
    sql = """
    SELECT 
        AccountID,
        IBAN,
        AccountName,
        BankName,
        AccountType,
        Currency,
        Color,
        IsActive
    FROM Accounts
    WHERE IsActive = 1
    ORDER BY AccountName;
    """
    
    result = turso_query(sql)
    
    return jsonify({
        "accounts": result["data"] if result["success"] else []
    })


@app.route('/api/accounts/create', methods=['POST'])
def create_account():
    """Vytvorenie nového účtu"""
    data = request.json
    iban = data.get('iban', '').upper().replace(' ', '')
    name = data.get('name', '').replace("'", "''")
    bank = data.get('bank', 'Tatra banka').replace("'", "''")
    acc_type = data.get('type', 'Osobný účet').replace("'", "''")
    
    if not iban or not name:
        return jsonify({"error": "IBAN a názov sú povinné"}), 400
    
    # Validácia IBAN
    if not iban.startswith('SK') or len(iban) != 24:
        return jsonify({"error": "Neplatný slovenský IBAN (musí začínať SK a mať 24 znakov)"}), 400
    
    sql = f"""
    INSERT INTO Accounts (IBAN, AccountName, BankName, AccountType)
    VALUES ('{iban}', '{name}', '{bank}', '{acc_type}');
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({"success": True, "message": "Účet vytvorený"})
    else:
        return jsonify({"error": result.get("error", "Chyba pri vytváraní účtu")}), 500


@app.route('/api/accounts/update/<int:account_id>', methods=['PUT'])
def update_account(account_id):
    """Aktualizácia účtu"""
    data = request.json
    name = data.get('name', '').replace("'", "''")
    bank = data.get('bank', '').replace("'", "''")
    acc_type = data.get('type', '').replace("'", "''")
    
    if not name:
        return jsonify({"error": "Názov je povinný"}), 400
    
    # Zostavíme UPDATE query s viacerými poliami
    updates = [f"AccountName = '{name}'"]
    
    if bank:
        updates.append(f"BankName = '{bank}'")
    
    if acc_type:
        updates.append(f"AccountType = '{acc_type}'")
    
    sql = f"""
    UPDATE Accounts 
    SET {', '.join(updates)}
    WHERE AccountID = {account_id};
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({"success": True, "message": "Účet aktualizovaný"})
    else:
        return jsonify({"error": result.get("error", "Chyba")}), 500


@app.route('/api/accounts/delete/<int:account_id>', methods=['DELETE'])
def delete_account(account_id):
    """Vymazanie účtu (soft delete)"""
    sql = f"""
    UPDATE Accounts 
    SET IsActive = 0
    WHERE AccountID = {account_id};
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({"success": True, "message": "Účet vymazaný"})
    else:
        return jsonify({"error": result.get("error", "Chyba")}), 500


@app.route('/api/categories/list', methods=['GET'])
def categories_list():
    """Zoznam všetkých kategórií"""
    sql = """
    SELECT 
        c.CategoryID,
        c.Name,
        c.Icon,
        c.Color,
        c.ParentCategoryID,
        COUNT(t.TransactionID) as transaction_count,
        COALESCE(SUM(ABS(t.Amount)), 0) as total_amount
    FROM Categories c
    LEFT JOIN Transactions t ON c.CategoryID = t.CategoryID AND t.Amount < 0
    GROUP BY c.CategoryID, c.Name, c.Icon, c.Color, c.ParentCategoryID
    ORDER BY c.Name;
    """
    
    result = turso_query(sql)
    
    return jsonify({
        "categories": result["data"] if result["success"] else []
    })


@app.route('/api/categories/create', methods=['POST'])
def create_category():
    """Vytvorenie novej kategórie"""
    data = request.json
    name = data.get('name', '').replace("'", "''")
    icon = data.get('icon', '📦')
    color = data.get('color', '#667eea')
    
    if not name:
        return jsonify({"error": "Názov kategórie je povinný"}), 400
    
    sql = f"""
    INSERT INTO Categories (Name, Icon, Color, CreatedAt)
    VALUES ('{name}', '{icon}', '{color}', datetime('now'));
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({"success": True, "message": "Kategória vytvorená"})
    else:
        return jsonify({"error": result["error"]}), 500


@app.route('/api/categories/update/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    """Aktualizácia kategórie"""
    data = request.json
    name = data.get('name', '').replace("'", "''")
    icon = data.get('icon', '')
    color = data.get('color', '')
    
    if not name:
        return jsonify({"error": "Názov kategórie je povinný"}), 400
    
    sql = f"""
    UPDATE Categories 
    SET Name = '{name}',
        Icon = '{icon}',
        Color = '{color}'
    WHERE CategoryID = {category_id};
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({"success": True, "message": "Kategória aktualizovaná"})
    else:
        return jsonify({"error": result["error"]}), 500


@app.route('/api/categories/delete/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """Vymazanie kategórie"""
    # Najprv nastavíme CategoryID na NULL pre všetky transakcie s touto kategóriou
    sql_update = f"""
    UPDATE Transactions 
    SET CategoryID = NULL 
    WHERE CategoryID = {category_id};
    """
    
    turso_query(sql_update)
    
    # Potom vymažeme kategóriu
    sql_delete = f"""
    DELETE FROM Categories 
    WHERE CategoryID = {category_id};
    """
    
    result = turso_query(sql_delete)
    
    if result["success"]:
        return jsonify({"success": True, "message": "Kategória vymazaná"})
    else:
        return jsonify({"error": result["error"]}), 500


@app.route('/api/transactions/update-category/<int:transaction_id>', methods=['PUT'])
def update_transaction_category(transaction_id):
    """Aktualizácia kategórie transakcie"""
    data = request.json
    category_id = data.get('category_id')
    
    if category_id is None:
        sql = f"""
        UPDATE Transactions 
        SET CategoryID = NULL,
            CategorySource = 'Manual',
            UpdatedAt = datetime('now')
        WHERE TransactionID = {transaction_id};
        """
    else:
        sql = f"""
        UPDATE Transactions 
        SET CategoryID = {category_id},
            CategorySource = 'Manual',
            UpdatedAt = datetime('now')
        WHERE TransactionID = {transaction_id};
        """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({"success": True, "message": "Kategória transakcie aktualizovaná"})
    else:
        return jsonify({"error": result["error"]}), 500


@app.route('/api/summary', methods=['GET'])
def get_summary():
    """API endpoint pre zhrnutie štatistík"""
    
    # Celkové štatistiky - používame aliasy BEZ podčiarkovníkov
    summary_sql = """
    SELECT 
        COUNT(*) as totaltransactions,
        SUM(CASE WHEN Amount < 0 THEN ABS(Amount) ELSE 0 END) as totalexpenses,
        SUM(CASE WHEN Amount > 0 THEN Amount ELSE 0 END) as totalincome,
        AVG(CASE WHEN Amount < 0 THEN ABS(Amount) ELSE NULL END) as avgexpense
    FROM Transactions;
    """
    
    summary_result = turso_query(summary_sql)
    
    # Normalize the result
    summary = {}
    if summary_result["success"] and summary_result["data"]:
        raw = summary_result["data"][0]
        summary = {
            "total_transactions": raw.get('totaltransactions') or raw.get('TOTALTRANSACTIONS') or 0,
            "total_expenses": raw.get('totalexpenses') or raw.get('TOTALEXPENSES') or 0,
            "total_income": raw.get('totalincome') or raw.get('TOTALINCOME') or 0,
            "avg_expense": raw.get('avgexpense') or raw.get('AVGEXPENSE') or 0
        }
    
    # Top merchants
    merchants_sql = """
    SELECT 
        MerchantName,
        COUNT(*) as count,
        SUM(ABS(Amount)) as total
    FROM Transactions
    WHERE Amount < 0
    GROUP BY MerchantName
    ORDER BY total DESC
    LIMIT 5;
    """
    
    merchants_result = turso_query(merchants_sql)
    
    # Výdavky podľa kategórií
    category_sql = """
    SELECT 
        c.Name as category,
        SUM(ABS(t.Amount)) as total
    FROM Transactions t
    LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
    WHERE t.Amount < 0
    GROUP BY c.Name
    ORDER BY total DESC;
    """
    
    category_result = turso_query(category_sql)
    
    # Mesačné údaje (posledných 6 mesiacov)
    monthly_sql = """
    SELECT 
        strftime('%Y-%m', TransactionDate) as month,
        SUM(CASE WHEN Amount < 0 THEN ABS(Amount) ELSE 0 END) as expenses,
        SUM(CASE WHEN Amount > 0 THEN Amount ELSE 0 END) as income
    FROM Transactions
    WHERE TransactionDate >= date('now', '-6 months')
    GROUP BY month
    ORDER BY month;
    """
    
    monthly_result = turso_query(monthly_sql)
    
    # Kategórie pre pie chart
    category_pie_sql = """
    SELECT 
        COALESCE(c.Name, 'Nezaradené') as category,
        c.Icon as icon,
        c.Color as color,
        SUM(ABS(t.Amount)) as amount
    FROM Transactions t
    LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
    WHERE t.Amount < 0
    GROUP BY c.CategoryID, c.Name, c.Icon, c.Color
    ORDER BY amount DESC;
    """
    
    category_pie_result = turso_query(category_pie_sql)
    
    return jsonify({
        "summary": summary,
        "top_merchants": merchants_result["data"] if merchants_result["success"] else [],
        "by_category": category_result["data"] if category_result["success"] else [],
        "monthly": monthly_result["data"] if monthly_result["success"] else [],
        "category_pie": category_pie_result["data"] if category_pie_result["success"] else []
    })


@app.route('/api/transactions/list', methods=['GET'])
def transactions_list():
    """Zoznam všetkých transakcií s filtráciou"""
    limit = request.args.get('limit', 50)
    offset = request.args.get('offset', 0)
    
    sql = f"""
    SELECT 
        t.TransactionID,
        t.TransactionDate,
        t.Amount,
        t.Currency,
        t.MerchantName,
        t.Description,
        t.PaymentMethod,
        t.IBAN,
        COALESCE(c.Name, 'Nezaradené') as CategoryName,
        c.Icon as CategoryIcon,
        t.CategorySource,
        COALESCE(a.AccountName, 'Nepriradený') as AccountName,
        a.BankName as BankName
    FROM Transactions t
    LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
    LEFT JOIN Accounts a ON t.AccountID = a.AccountID
    ORDER BY t.TransactionDate DESC
    LIMIT {limit} OFFSET {offset};
    """
    
    result = turso_query(sql)
    
    return jsonify({
        "transactions": result["data"] if result["success"] else [],
        "limit": int(limit),
        "offset": int(offset)
    })


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "finance-management"})


# ==============================================================================
# GPT API ENDPOINTS (for ChatGPT Actions)
# ==============================================================================

GPT_API_KEY = os.getenv("API_KEY", "tvoj-tajny-api-key-123456")


def verify_gpt_api_key():
    """Overenie API kľúča pre GPT"""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        return token == GPT_API_KEY
    return False


@app.route('/api/health', methods=['GET'])
def gpt_health_check():
    """Health check pre GPT"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "finance-gpt-api"
    })


@app.route('/api/gpt/accounts/list', methods=['GET'])
def gpt_get_accounts():
    """Zoznam všetkých účtov pre GPT"""
    
    if not verify_gpt_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    sql = """
    SELECT 
        AccountID,
        IBAN,
        AccountName,
        BankName,
        AccountType,
        Currency
    FROM Accounts
    WHERE IsActive = 1
    ORDER BY AccountName;
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({
            "accounts": result["data"]
        })
    else:
        return jsonify({"error": result.get("error", "Query failed")}), 500


@app.route('/api/gpt/transactions/summary', methods=['GET'])
def gpt_get_transactions_summary():
    """Zhrnutie transakcií pre GPT"""
    
    if not verify_gpt_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    days = request.args.get('days', '30')
    account_id = request.args.get('account_id', '')
    
    account_filter = f"AND AccountID = {account_id}" if account_id else ""
    
    sql = f"""
    SELECT 
        COUNT(*) as totalcount,
        SUM(CASE WHEN Amount < 0 THEN Amount ELSE 0 END) as totalexpenses,
        SUM(CASE WHEN Amount > 0 THEN Amount ELSE 0 END) as totalincome,
        AVG(CASE WHEN Amount < 0 THEN Amount ELSE NULL END) as avgexpense
    FROM Transactions
    WHERE TransactionDate >= datetime('now', '-{days} days')
    {account_filter};
    """
    
    result = turso_query(sql)
    
    if result["success"] and result["data"]:
        return jsonify({
            "period_days": int(days),
            "summary": result["data"][0] if result["data"] else {}
        })
    else:
        return jsonify({"error": result.get("error", "No data")}), 500


@app.route('/api/gpt/transactions/recent', methods=['GET'])
def gpt_get_recent_transactions():
    """Posledné transakcie pre GPT"""
    
    if not verify_gpt_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    limit = request.args.get('limit', '10')
    
    sql = f"""
    SELECT 
        t.TransactionDate,
        t.Amount,
        t.Currency,
        t.MerchantName,
        t.Description,
        COALESCE(c.Name, 'Nezaradené') as CategoryName,
        COALESCE(a.AccountName, 'Nepriradený') as AccountName
    FROM Transactions t
    LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
    LEFT JOIN Accounts a ON t.AccountID = a.AccountID
    ORDER BY t.TransactionDate DESC
    LIMIT {limit};
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({
            "transactions": result["data"]
        })
    else:
        return jsonify({"error": result.get("error", "Query failed")}), 500


@app.route('/api/gpt/categories/list', methods=['GET'])
def gpt_get_categories():
    """Zoznam kategórií pre GPT"""
    
    if not verify_gpt_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    sql = """
    SELECT 
        CategoryID,
        Name,
        Icon,
        Color,
        Description
    FROM Categories
    WHERE IsActive = 1
    ORDER BY Name;
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({
            "categories": result["data"]
        })
    else:
        return jsonify({"error": result.get("error", "Query failed")}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    
    print("=" * 60)
    print("🎨 Finance Dashboard UI")
    print("=" * 60)
    print(f"🌐 Dashboard: http://0.0.0.0:{port}")
    print(f"📊 Transakcie: http://0.0.0.0:{port}/transactions")
    print("=" * 60)
    
    # Use gunicorn in production, Flask dev server locally
    app.run(host='0.0.0.0', port=port, debug=False)
