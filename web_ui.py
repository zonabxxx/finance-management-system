#!/usr/bin/env python3
"""
Flask Web UI - Dashboard pre správu financií (Railway compatible - HTTP API)
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import requests
import json
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from smart_categorizer import SmartCategorizer

load_dotenv()

app = Flask(__name__)
CORS(app)

# Povoľ všetky Content-Types pre webhooky
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Inicializuj Smart Categorizer
smart_categorizer = None

def get_smart_categorizer():
    """Lazy init Smart Categorizer"""
    global smart_categorizer
    if smart_categorizer is None:
        smart_categorizer = SmartCategorizer(turso_query)
    return smart_categorizer

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
                response_obj = result['results'][0]['response']
                
                # Check for errors
                if response_obj.get('type') == 'error':
                    error_msg = response_obj.get('error', {}).get('message', 'Unknown error')
                    print(f"❌ Turso error: {error_msg}")
                    return {"success": False, "error": error_msg, "data": []}
                
                query_result = response_obj.get('result', {})
                
                # Extract columns and rows
                columns = [col['name'] for col in query_result.get('cols', [])]
                rows = query_result.get('rows', [])
                
                # For UPDATE/INSERT/DELETE, check affected_row_count
                affected_rows = query_result.get('affected_row_count', 0)
                
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
                
                return {
                    "success": True, 
                    "data": data,
                    "affected_rows": affected_rows
                }
            else:
                return {"success": True, "data": [], "affected_rows": 0}
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
        # Learn from manual assignment (if category was set, not removed)
        if category_id is not None:
            try:
                categorizer = get_smart_categorizer()
                categorizer.learn_from_manual_assignment(transaction_id, category_id)
            except Exception as e:
                print(f"Learning failed: {e}")
        
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
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    
    # Základný SQL
    where_conditions = []
    
    if search:
        where_conditions.append(f"t.MerchantName LIKE '%{search}%'")
    
    if category:
        where_conditions.append(f"c.Name = '{category}'")
    
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)
    
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
    {where_clause}
    ORDER BY t.TransactionDate DESC
    LIMIT {limit} OFFSET {offset};
    """
    
    result = turso_query(sql)
    
    # Debug: log first transaction if any
    if result["success"] and result["data"]:
        print(f"📊 Transactions API: Returning {len(result['data'])} transactions")
        if len(result["data"]) > 0:
            first = result["data"][0]
            print(f"   First transaction keys: {list(first.keys())[:5]}")
            print(f"   TransactionID: {first.get('TransactionID')} / {first.get('transactionid')}")
    
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
        Color
    FROM Categories
    ORDER BY Name;
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({
            "categories": result["data"]
        })
    else:
        return jsonify({"error": result.get("error", "Query failed")}), 500


@app.route('/api/gpt/transactions/by-category', methods=['GET'])
def gpt_get_transactions_by_category():
    """Výdavky podľa kategórií pre GPT"""
    
    if not verify_gpt_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    days = request.args.get('days', '30')
    
    sql = f"""
    SELECT 
        c.Name as categoryname,
        c.Icon as categoryicon,
        COUNT(t.TransactionID) as transactioncount,
        SUM(t.Amount) as totalamount,
        AVG(t.Amount) as avgamount
    FROM Transactions t
    LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
    WHERE t.TransactionDate >= datetime('now', '-{days} days')
        AND t.Amount < 0
    GROUP BY c.CategoryID, c.Name, c.Icon
    ORDER BY totalamount ASC;
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({
            "period_days": int(days),
            "categories": result["data"]
        })
    else:
        return jsonify({"error": result.get("error", "Query failed")}), 500


@app.route('/api/gpt/transactions/top-merchants', methods=['GET'])
def gpt_get_top_merchants():
    """Top obchodníci pre GPT"""
    
    if not verify_gpt_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    limit = request.args.get('limit', '10')
    days = request.args.get('days', '30')
    
    sql = f"""
    SELECT 
        MerchantName as merchantname,
        COUNT(*) as transactioncount,
        SUM(Amount) as totalspent,
        AVG(Amount) as avgspent
    FROM Transactions
    WHERE TransactionDate >= datetime('now', '-{days} days')
        AND Amount < 0
        AND MerchantName IS NOT NULL
    GROUP BY MerchantName
    ORDER BY totalspent ASC
    LIMIT {limit};
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({
            "period_days": int(days),
            "top_merchants": result["data"]
        })
    else:
        return jsonify({"error": result.get("error", "Query failed")}), 500


@app.route('/api/gpt/transactions/monthly', methods=['GET'])
def gpt_get_monthly_stats():
    """Mesačné štatistiky pre GPT"""
    
    if not verify_gpt_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    months = request.args.get('months', '6')
    
    sql = f"""
    SELECT 
        strftime('%Y-%m', TransactionDate) as month,
        COUNT(*) as transactioncount,
        SUM(CASE WHEN Amount < 0 THEN Amount ELSE 0 END) as expenses,
        SUM(CASE WHEN Amount > 0 THEN Amount ELSE 0 END) as income
    FROM Transactions
    WHERE TransactionDate >= datetime('now', '-{months} months')
    GROUP BY month
    ORDER BY month DESC;
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({
            "period_months": int(months),
            "monthly_data": result["data"]
        })
    else:
        return jsonify({"error": result.get("error", "Query failed")}), 500


@app.route('/api/gpt/transactions/search', methods=['GET'])
def gpt_search_transactions():
    """Vyhľadávanie transakcií pre GPT"""
    
    if not verify_gpt_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    merchant = request.args.get('merchant', '')
    min_amount = request.args.get('min_amount', '')
    max_amount = request.args.get('max_amount', '')
    account_id = request.args.get('account_id', '')
    category = request.args.get('category', '')
    limit = request.args.get('limit', '50')  # Pridaný limit parameter
    
    conditions = []
    if merchant:
        conditions.append(f"t.MerchantName LIKE '%{merchant}%'")
    if min_amount:
        conditions.append(f"t.Amount >= {min_amount}")
    if max_amount:
        conditions.append(f"t.Amount <= {max_amount}")
    if account_id:
        conditions.append(f"t.AccountID = {account_id}")
    if category:
        # Handle "Nezaradené" (NULL CategoryID) specifically
        if 'nezaradene' in category.lower() or 'nezaradené' in category.lower():
            conditions.append("(t.CategoryID IS NULL OR COALESCE(c.Name, 'Nezaradené') = 'Nezaradené')")
        else:
            conditions.append(f"c.Name LIKE '%{category}%'")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    sql = f"""
    SELECT 
        t.TransactionID,
        t.TransactionDate,
        t.Amount,
        t.Currency,
        t.MerchantName,
        t.Description,
        t.RecipientInfo,
        t.CounterpartyPurpose,
        COALESCE(c.Name, 'Nezaradené') as CategoryName,
        COALESCE(c.Icon, '📦') as CategoryIcon,
        COALESCE(a.AccountName, 'Nepriradený') as AccountName
    FROM Transactions t
    LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
    LEFT JOIN Accounts a ON t.AccountID = a.AccountID
    WHERE {where_clause}
    ORDER BY t.TransactionDate DESC
    LIMIT {limit};
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        # Debug: log search results
        print(f"🔍 GPT Search: Found {len(result['data'])} transactions")
        
        # Format results to make TransactionID more explicit
        formatted_results = []
        for i, tx in enumerate(result["data"]):
            tx_id = tx.get('TransactionID') or tx.get('transactionid')
            merchant = tx.get('MerchantName') or tx.get('merchantname')
            
            # Create clean object with explicit ID
            formatted_tx = {
                "transaction_id": tx_id,  # Use snake_case to match bulk-categorize input!
                "TransactionID": tx_id,   # Also keep original
                "TransactionDate": tx.get('TransactionDate') or tx.get('transactiondate'),
                "Amount": tx.get('Amount') or tx.get('amount'),
                "Currency": tx.get('Currency') or tx.get('currency'),
                "MerchantName": merchant,
                "Description": tx.get('Description') or tx.get('description'),
                "RecipientInfo": tx.get('RecipientInfo') or tx.get('recipientinfo'),
                "CounterpartyPurpose": tx.get('CounterpartyPurpose') or tx.get('counterpartypurpose'),
                "CategoryName": tx.get('CategoryName') or tx.get('categoryname'),
                "CategoryIcon": tx.get('CategoryIcon') or tx.get('categoryicon'),
                "AccountName": tx.get('AccountName') or tx.get('accountname')
            }
            formatted_results.append(formatted_tx)
            
            if i < 3:  # Log first 3
                print(f"   [{i}] transaction_id={tx_id}, TransactionID={tx_id}, Merchant={merchant}")
        
        return jsonify({
            "results": formatted_results,
            "count": len(formatted_results)
        })
    else:
        return jsonify({"error": result.get("error", "Query failed")}), 500


@app.route('/api/gpt/accounts/<int:account_id>/summary', methods=['GET'])
def gpt_get_account_summary(account_id):
    """Detailný prehľad účtu pre GPT"""
    
    if not verify_gpt_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    days = request.args.get('days', '30')
    
    # Info o účte
    account_sql = f"""
    SELECT 
        AccountID,
        IBAN,
        AccountName,
        BankName,
        AccountType,
        Currency
    FROM Accounts
    WHERE AccountID = {account_id};
    """
    
    account_result = turso_query(account_sql)
    
    if not account_result["success"] or not account_result["data"]:
        return jsonify({"error": "Account not found"}), 404
    
    # Štatistiky transakcií
    stats_sql = f"""
    SELECT 
        COUNT(*) as totalcount,
        SUM(CASE WHEN Amount < 0 THEN Amount ELSE 0 END) as totalexpenses,
        SUM(CASE WHEN Amount > 0 THEN Amount ELSE 0 END) as totalincome,
        AVG(CASE WHEN Amount < 0 THEN Amount ELSE NULL END) as avgexpense,
        MIN(TransactionDate) as firsttransaction,
        MAX(TransactionDate) as lasttransaction
    FROM Transactions
    WHERE AccountID = {account_id}
        AND TransactionDate >= datetime('now', '-{days} days');
    """
    
    stats_result = turso_query(stats_sql)
    
    # Top kategórie
    categories_sql = f"""
    SELECT 
        c.Name as categoryname,
        c.Icon as categoryicon,
        COUNT(t.TransactionID) as transactioncount,
        SUM(t.Amount) as totalamount
    FROM Transactions t
    LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
    WHERE t.AccountID = {account_id}
        AND t.TransactionDate >= datetime('now', '-{days} days')
        AND t.Amount < 0
    GROUP BY c.CategoryID
    ORDER BY totalamount ASC
    LIMIT 5;
    """
    
    categories_result = turso_query(categories_sql)
    
    return jsonify({
        "account": account_result["data"][0] if account_result["data"] else {},
        "statistics": stats_result["data"][0] if stats_result["success"] and stats_result["data"] else {},
        "top_categories": categories_result["data"] if categories_result["success"] else [],
        "period_days": int(days)
    })


# ============================================================================
# GPT BULK CATEGORIZATION - ChatGPT agent môže kategorizovať hromadne
# ============================================================================

@app.route('/api/gpt/transactions/bulk-categorize', methods=['POST'])
def gpt_bulk_categorize():
    """
    GPT: Hromadná kategorizácia transakcií
    
    Body:
    {
      "updates": [
        {"transaction_id": 123, "category_name": "Potraviny"},
        {"transaction_id": 124, "category_name": "Zdravie a lieky"}
      ]
    }
    """
    if not verify_gpt_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.json
        updates = data.get('updates', [])
        
        if not updates:
            return jsonify({"error": "No updates provided"}), 400
        
        # Načítaj kategórie
        categories_query = "SELECT CategoryID, Name FROM Categories;"
        categories_result = turso_query(categories_query)
        
        if not categories_result or not categories_result.get('success') or not categories_result.get('data'):
            return jsonify({"error": "Failed to load categories", "debug": str(categories_result)}), 500
        
        # Mapuj názvy kategórií na ID
        category_map = {}
        for row in categories_result['data']:
            # turso_query vracia 'data' array s row_dict objektami
            cat_id = row.get('CategoryID') or row.get('categoryid')
            cat_name = (row.get('Name') or row.get('name', '')).lower()
            if cat_id and cat_name:
                category_map[cat_name] = int(cat_id)
        
        updated_count = 0
        learned_rules = 0
        errors = []
        
        for update in updates:
            transaction_id = update.get('transaction_id')
            category_name = update.get('category_name', '').lower().strip()
            
            # Odstráň emoji z názvu kategórie
            import re
            category_name_clean = re.sub(r'[^\w\s\-áäčďéíĺľňóôŕšťúýžÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ]', '', category_name).strip()
            
            if not transaction_id or not category_name_clean:
                errors.append(f"Invalid update: {update}")
                continue
            
            # Nájdi CategoryID (flexible matching)
            category_id = None
            for cat_name_lower, cat_id in category_map.items():
                if cat_name_lower in category_name_clean or category_name_clean in cat_name_lower:
                    category_id = cat_id
                    break
            
            if not category_id:
                errors.append(f"Category not found: {category_name}")
                continue
            
            # Updatuj transakciu
            update_query = f"""
            UPDATE Transactions 
            SET CategoryID = {category_id}, 
                CategorySource = 'GPT',
                UpdatedAt = datetime('now')
            WHERE TransactionID = {transaction_id};
            """
            
            result = turso_query(update_query)
            
            if result and result.get('success'):
                affected = result.get('affected_rows', 0)
                if affected > 0:
                    updated_count += 1
                    print(f"   ✅ Updated transaction {transaction_id} → CategoryID={category_id}")
                    
                    # Learn from this assignment
                    try:
                        categorizer = get_smart_categorizer()
                        categorizer.learn_from_manual_assignment(transaction_id, category_id)
                        learned_rules += 1
                    except Exception as e:
                        print(f"Learning failed for transaction {transaction_id}: {e}")
                else:
                    errors.append(f"Transaction {transaction_id} not found or not updated")
                    print(f"   ⚠️  Transaction {transaction_id} not updated (affected_rows=0)")
            else:
                errors.append(f"Failed to update transaction {transaction_id}")
                print(f"   ❌ Failed to update transaction {transaction_id}: {result.get('error', 'Unknown')}")
        
        return jsonify({
            "success": True,
            "updated": updated_count,
            "learned_rules": learned_rules,
            "total_requested": len(updates),
            "errors": errors if errors else None
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    
    print("=" * 60)
    print("🎨 Finance Dashboard UI")
    print("=" * 60)
    print(f"🌐 Dashboard: http://0.0.0.0:{port}")
    print(f"📊 Transakcie: http://0.0.0.0:{port}/transactions")
    print(f"📧 Sync Emails: POST http://0.0.0.0:{port}/api/sync-emails")
    print("=" * 60)
    
    # Use gunicorn in production, Flask dev server locally
    app.run(host='0.0.0.0', port=port, debug=False)


# ============================================================================
# WEBHOOK ENDPOINT - Manuálna synchronizácia Gmail B-mailov
# ============================================================================

@app.route('/api/sync-emails', methods=['POST', 'GET'])
def sync_emails():
    """
    Webhook endpoint pre manuálnu synchronizáciu Gmail B-mailov
    Použitie: POST /api/sync-emails?secret=API_SECRET_KEY
    """
    # Jednoduchá autentifikácia
    api_secret = os.getenv('API_SECRET_KEY', 'change-me-in-production')
    provided_secret = request.args.get('secret') or request.headers.get('X-API-Secret')
    
    if provided_secret != api_secret:
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Invalid API secret'
        }), 401
    
    try:
        import imaplib
        import email
        from email.header import decode_header
        import re
        
        EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
        EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
        EMAIL_IMAP_SERVER = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
        
        if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
            return jsonify({
                'error': 'Configuration error',
                'message': 'EMAIL_ADDRESS or EMAIL_PASSWORD not set'
            }), 500
        
        # Pripojenie na Gmail
        mail = imaplib.IMAP4_SSL(EMAIL_IMAP_SERVER)
        mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        mail.select("INBOX")
        
        # Hľadanie B-mailov
        status, messages = mail.search(None, '(FROM "b-mail@tatrabanka.sk")')
        
        if status != "OK":
            mail.logout()
            return jsonify({
                'error': 'Search failed',
                'message': f'Gmail search status: {status}'
            }), 500
        
        email_ids = messages[0].split()
        processed = 0
        errors = 0
        
        # Spracovanie emailov
        for email_id in email_ids[-10:]:  # Posledných 10 B-mailov
            try:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    continue
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Získanie body
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    try:
                                        body = part.get_payload(decode=True).decode()
                                    except:
                                        pass
                        else:
                            try:
                                body = msg.get_payload(decode=True).decode()
                            except:
                                pass
                        
                        # Parsovanie transakcie
                        main_match = re.search(
                            r'(\d{1,2}\.\d{1,2}\.\d{4})\s+(\d{1,2}:\d{2})\s+bol zostatok.*?'
                            r'(SK\d+)\s+(znizeny|zvyseny)\s+o\s+([\d,]+)\s*EUR',
                            body
                        )
                        
                        if main_match:
                            date_str = f"{main_match.group(1)} {main_match.group(2)}"
                            trans_date = datetime.strptime(date_str, "%d.%m.%Y %H:%M")
                            iban = main_match.group(3)
                            amount_str = main_match.group(5).replace(',', '.')
                            amount = float(amount_str)
                            if main_match.group(4) == 'znizeny':
                                amount = -amount
                            
                            # Popis
                            desc_match = re.search(r'Popis transakcie:\s*(.+?)(?:\n|$)', body)
                            description = desc_match.group(1).strip() if desc_match else ''
                            
                            # Merchant
                            merchant = 'Unknown'
                            if 'Platba kartou' in description:
                                merchant_match = re.search(r',\s*([A-Z0-9\.\-]+)', description)
                                if merchant_match:
                                    merchant_raw = merchant_match.group(1).strip('.')
                                    merchant = re.sub(r'\.?[A-Z]{3}\d+$', '', merchant_raw) or merchant_raw
                            
                            # Nájdenie AccountID
                            account_query = f"SELECT AccountID FROM Accounts WHERE IBAN = '{iban}' AND IsActive = 1 LIMIT 1;"
                            account_result = turso_query(account_query)
                            account_id = None
                            if account_result and 'rows' in account_result and len(account_result['rows']) > 0:
                                account_id = int(account_result['rows'][0][0]['value'])
                            
                            account_id_sql = str(account_id) if account_id else 'NULL'
                            
                            # Insert transakcie
                            insert_query = f"""
                            INSERT INTO Transactions (
                                TransactionDate, Amount, Currency, MerchantName, Description,
                                IBAN, TransactionType, PaymentMethod, RawEmailData,
                                CategorySource, AccountID, CreatedAt
                            ) VALUES (
                                '{trans_date.isoformat()}', {amount}, 'EUR',
                                '{merchant.replace("'", "''")}', '{description.replace("'", "''")}',
                                '{iban}', '{'Debit' if amount < 0 else 'Credit'}', 'Card',
                                '{body.replace("'", "''")}', 'Email', {account_id_sql},
                                '{datetime.now().isoformat()}'
                            );
                            """
                            
                            result = turso_query(insert_query)
                            if result:
                                processed += 1
                            else:
                                errors += 1
            
            except Exception as e:
                print(f"Error processing email: {e}")
                errors += 1
        
        mail.logout()
        
        return jsonify({
            'success': True,
            'message': 'Email sync completed',
            'checked': len(email_ids),
            'processed': processed,
            'errors': errors
        })
    
    except Exception as e:
        return jsonify({
            'error': 'Sync failed',
            'message': str(e)
        }), 500


# ============================================================================
# CLOUDMAILIN WEBHOOK - Príjem B-mailov priamo z Tatra banky
# ============================================================================

@app.route('/api/receive-email', methods=['POST'])
def receive_email():
    """
    CloudMailin webhook endpoint
    Tatra banka → CloudMailin → Railway
    
    CloudMailin sends data in various formats (multipart, JSON, etc.)
    """
    try:
        # CloudMailin môže posielať rôzne Content-Types
        # Získaj raw data a spracuj podľa formátu
        data = None
        email_body = None
        
        # Debug: loguj čo prišlo
        print(f"📧 Received request")
        print(f"   Content-Type: {request.content_type}")
        print(f"   Method: {request.method}")
        
        # 1. Skús form data (CloudMailin Multipart-Normalized)
        if request.form:
            print("   Format: Form data")
            email_body = request.form.get('plain', '') or request.form.get('html', '')
            data = {
                'envelope': {'from': request.form.get('envelope[from]', 'unknown')},
                'headers': {'Subject': request.form.get('headers[Subject]', 'no subject')}
            }
        
        # 2. Skús JSON
        elif request.is_json or 'json' in request.content_type.lower():
            print("   Format: JSON")
            data = request.get_json(force=True)
            email_body = data.get('plain', '') or data.get('html', '')
        
        # 3. Fallback - skús parsovať ako JSON
        else:
            print("   Format: Unknown, trying to parse...")
            try:
                import json
                data = json.loads(request.get_data(as_text=True))
                email_body = data.get('plain', '') or data.get('html', '')
            except:
                # Možno to je raw text
                email_body = request.get_data(as_text=True)
                data = {'envelope': {}, 'headers': {}}
        
        if not email_body:
            return jsonify({'error': 'Empty email body'}), 400
        
        # Loguj príchod emailu
        print(f"📧 Received email from CloudMailin")
        print(f"   From: {data.get('envelope', {}).get('from', 'unknown')}")
        print(f"   Subject: {data.get('headers', {}).get('Subject', 'no subject')}")
        
        # Parsovanie B-mail transakcie
        main_match = re.search(
            r'(\d{1,2}\.\d{1,2}\.\d{4})\s+(\d{1,2}:\d{2})\s+bol zostatok.*?'
            r'(SK\d+)\s+(znizeny|zvyseny)\s+o\s+([\d\s,]+)\s*EUR',
            email_body
        )
        
        if not main_match:
            print("   ⚠️  Not a B-mail transaction (ignoring)")
            return jsonify({'status': 'ignored', 'message': 'Not a B-mail transaction'}), 200
        
        # Extrahovanie údajov
        date_str = f"{main_match.group(1)} {main_match.group(2)}"
        trans_date = datetime.strptime(date_str, "%d.%m.%Y %H:%M")
        iban = main_match.group(3)
        amount_str = main_match.group(5).replace(',', '.').replace(' ', '')  # Odstráň medzery aj čiarky
        amount = float(amount_str)
        if main_match.group(4) == 'znizeny':
            amount = -amount
        
        # Popis transakcie
        desc_match = re.search(r'Popis transakcie:\s*(.+?)(?:\n|$)', email_body)
        description = desc_match.group(1).strip() if desc_match else ''
        
        # Extrahovanie obchodníka z B-mailu (Tatra banka používa rôzne názvy polí)
        counterparty_name = None
        
        # Variant 1: "Ucet protistrany:" (účet protistrany - názov obchodníka/prijemcu)
        ucet_match = re.search(r'Ucet protistrany:\s*(.+?)(?:\n|$)', email_body, re.IGNORECASE)
        if ucet_match:
            counterparty_name = ucet_match.group(1).strip()
        
        # Variant 2: "Ucel protistrany:" (účel - dôvod platby)
        ucel_match = re.search(r'Ucel protistrany:\s*(.+?)(?:\n|$)', email_body, re.IGNORECASE)
        counterparty_purpose = ucel_match.group(1).strip() if ucel_match else ''
        
        # Variant 3: "Informacia pre prijemcu:" (dodatočné info)
        info_match = re.search(r'Informacia pre prijemcu:\s*(.+?)(?:\n|$)', email_body, re.IGNORECASE)
        recipient_info = info_match.group(1).strip() if info_match else ''
        
        # Obchodník - použiť presné údaje z B-mailu (priorita: názov účtu > účel > description)
        if counterparty_name:
            merchant = counterparty_name
        elif counterparty_purpose:
            merchant = counterparty_purpose
        else:
            merchant = description or 'Unknown'
        
        # Payment method
        if 'Platba kartou' in description:
            payment_method = 'Card'
        elif 'Prevod' in description or 'Prikaz' in description:
            payment_method = 'Transfer'
        else:
            payment_method = 'Other'
        
        print(f"   💰 Amount: {amount} EUR")
        print(f"   🏪 Merchant: {merchant}")
        if counterparty_name:
            print(f"   🏢 Counterparty: {counterparty_name}")
        if counterparty_purpose:
            print(f"   🎯 Purpose: {counterparty_purpose}")
        if recipient_info:
            print(f"   📝 Recipient Info: {recipient_info}")
        
        # Nájdenie AccountID
        account_query = f"SELECT AccountID FROM Accounts WHERE IBAN = '{iban}' AND IsActive = 1 LIMIT 1;"
        account_result = turso_query(account_query)
        account_id = None
        
        if account_result and 'rows' in account_result and len(account_result['rows']) > 0:
            account_id = int(account_result['rows'][0][0]['value'])
            print(f"   🏦 Account: {account_id}")
        else:
            print(f"   ⚠️  Account with IBAN {iban} not found in Settings")
        
        account_id_sql = str(account_id) if account_id else 'NULL'
        
        # Uloženie do databázy
        insert_query = f"""
        INSERT INTO Transactions (
            TransactionDate, Amount, Currency, MerchantName, Description,
            IBAN, TransactionType, PaymentMethod, RawEmailData,
            CategorySource, AccountID, RecipientInfo, CounterpartyPurpose, CreatedAt
        ) VALUES (
            '{trans_date.isoformat()}', {amount}, 'EUR',
            '{merchant.replace("'", "''")}', '{description.replace("'", "''")}',
            '{iban}', '{'Debit' if amount < 0 else 'Credit'}', '{payment_method}',
            '{email_body.replace("'", "''")}', 'Email', {account_id_sql},
            '{recipient_info.replace("'", "''")}', '{counterparty_purpose.replace("'", "''")}',
            '{datetime.now().isoformat()}'
        );
        """
        
        result = turso_query(insert_query)
        
        if result:
            print(f"   ✅ Transaction saved to database")            # 🧠 Smart Categorization with Learning + AI
            try:
                # Získaj ID novo vytvorenej transakcie
                last_id_query = "SELECT TransactionID FROM Transactions ORDER BY TransactionID DESC LIMIT 1;"
                last_id_result = turso_query(last_id_query)
                
                if last_id_result and 'rows' in last_id_result and len(last_id_result['rows']) > 0:
                    transaction_id = int(last_id_result['rows'][0][0]['value'])
                    
                    # Použij Smart Categorizer s extra kontextom
                    categorizer = get_smart_categorizer()
                    category_id = categorizer.categorize(
                        merchant=merchant, 
                        description=description, 
                        amount=amount,
                        counterparty_purpose=counterparty_purpose,
                        recipient_info=recipient_info
                    )
                    
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

            
            return jsonify({
                'status': 'success',
                'message': 'Transaction processed',
                'transaction': {
                    'merchant': merchant,
                    'amount': amount,
                    'date': trans_date.isoformat()
                }
            }), 200
        else:
            print(f"   ❌ Failed to save transaction")
            return jsonify({
                'status': 'error',
                'message': 'Failed to save transaction'
            }), 500
    
    except Exception as e:
        print(f"❌ Error processing email: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
