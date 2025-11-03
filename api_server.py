#!/usr/bin/env python3
"""
Flask API Server pre ChatGPT GPT integráciu
Tento server poskytuje endpointy pre ChatGPT GPT aby mohol čítať finančné dáta
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(app)  # Povoliť CORS pre OpenAI GPT

# API kľúč pre autentifikáciu (vygeneruj si vlastný)
API_KEY = os.getenv("API_KEY", "tvoj-tajny-api-key-123456")

# Turso konfigurácia
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")


def turso_query(sql: str):
    """Vykonanie SQL query v Turso databáze cez HTTP API"""
    try:
        # Extract base URL without protocol prefix
        if not TURSO_DATABASE_URL or not TURSO_AUTH_TOKEN:
            return {"success": False, "error": "Turso configuration missing"}
        
        # Convert libsql:// to https://
        url = TURSO_DATABASE_URL.replace("libsql://", "https://")
        
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {TURSO_AUTH_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "statements": [sql]
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data and len(data) > 0:
                result = data[0]
                
                if "results" in result and "rows" in result["results"]:
                    rows = result["results"]["rows"]
                    columns = result["results"]["columns"]
                    
                    # Convert rows to list of dictionaries
                    parsed_data = []
                    for row in rows:
                        row_dict = {}
                        for i, col_name in enumerate(columns):
                            # Handle nested value structure
                            if isinstance(row[i], dict) and "value" in row[i]:
                                value = row[i]["value"]
                                # Convert string numbers to actual numbers
                                if isinstance(value, str) and value.replace('.', '', 1).replace('-', '', 1).isdigit():
                                    value = float(value) if '.' in value else int(value)
                                row_dict[col_name] = value
                                # Also add lowercase version for compatibility
                                row_dict[col_name.lower()] = value
                            else:
                                row_dict[col_name] = row[i]
                                row_dict[col_name.lower()] = row[i]
                        parsed_data.append(row_dict)
                    
                    return {"success": True, "data": parsed_data}
                else:
                    return {"success": True, "data": []}
            else:
                return {"success": False, "error": "Invalid response format"}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def verify_api_key():
    """Overenie API kľúča"""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        return token == API_KEY
    return False


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/transactions/summary', methods=['GET'])
def get_transactions_summary():
    """Zhrnutie transakcií - celkové výdavky, príjmy, počet transakcií"""
    
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    # Získanie parametrov
    days = request.args.get('days', '30')
    account_id = request.args.get('account_id', '')
    
    account_filter = f"AND AccountID = {account_id}" if account_id else ""
    
    sql = f"""
    SELECT 
        COUNT(*) as total_count,
        SUM(CASE WHEN Amount < 0 THEN Amount ELSE 0 END) as total_expenses,
        SUM(CASE WHEN Amount > 0 THEN Amount ELSE 0 END) as total_income,
        AVG(CASE WHEN Amount < 0 THEN Amount ELSE NULL END) as avg_expense
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


@app.route('/api/transactions/recent', methods=['GET'])
def get_recent_transactions():
    """Posledné transakcie"""
    
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    limit = request.args.get('limit', '10')
    
    sql = f"""
    SELECT 
        TransactionDate,
        Amount,
        Currency,
        MerchantName,
        Description,
        PaymentMethod
    FROM Transactions
    ORDER BY TransactionDate DESC
    LIMIT {limit};
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({
            "transactions": result["data"]
        })
    else:
        return jsonify({"error": result["error"]}), 500


@app.route('/api/transactions/by-category', methods=['GET'])
def get_transactions_by_category():
    """Výdavky podľa kategórií"""
    
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    days = request.args.get('days', '30')
    
    sql = f"""
    SELECT 
        c.CategoryName,
        COUNT(t.TransactionID) as transaction_count,
        SUM(t.Amount) as total_amount,
        AVG(t.Amount) as avg_amount
    FROM Transactions t
    LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
    WHERE t.TransactionDate >= datetime('now', '-{days} days')
        AND t.Amount < 0
    GROUP BY c.CategoryName
    ORDER BY total_amount ASC;
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({
            "period_days": int(days),
            "categories": result["data"]
        })
    else:
        return jsonify({"error": result["error"]}), 500


@app.route('/api/transactions/top-merchants', methods=['GET'])
def get_top_merchants():
    """Top obchodníci kde míňaš najviac"""
    
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    limit = request.args.get('limit', '10')
    days = request.args.get('days', '30')
    
    sql = f"""
    SELECT 
        MerchantName,
        COUNT(*) as transaction_count,
        SUM(Amount) as total_spent,
        AVG(Amount) as avg_spent
    FROM Transactions
    WHERE TransactionDate >= datetime('now', '-{days} days')
        AND Amount < 0
        AND MerchantName IS NOT NULL
    GROUP BY MerchantName
    ORDER BY total_spent ASC
    LIMIT {limit};
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({
            "period_days": int(days),
            "top_merchants": result["data"]
        })
    else:
        return jsonify({"error": result["error"]}), 500


@app.route('/api/transactions/monthly', methods=['GET'])
def get_monthly_stats():
    """Mesačné štatistiky"""
    
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    months = request.args.get('months', '6')
    
    sql = f"""
    SELECT 
        strftime('%Y-%m', TransactionDate) as month,
        COUNT(*) as transaction_count,
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
        return jsonify({"error": result["error"]}), 500


@app.route('/api/transactions/search', methods=['GET'])
def search_transactions():
    """Vyhľadávanie transakcií"""
    
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    merchant = request.args.get('merchant', '')
    min_amount = request.args.get('min_amount', '')
    max_amount = request.args.get('max_amount', '')
    account_id = request.args.get('account_id', '')
    
    conditions = []
    if merchant:
        conditions.append(f"MerchantName LIKE '%{merchant}%'")
    if min_amount:
        conditions.append(f"Amount >= {min_amount}")
    if max_amount:
        conditions.append(f"Amount <= {max_amount}")
    if account_id:
        conditions.append(f"AccountID = {account_id}")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
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
    WHERE {where_clause}
    ORDER BY t.TransactionDate DESC
    LIMIT 50;
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({
            "results": result["data"]
        })
    else:
        return jsonify({"error": result.get("error", "Query failed")}), 500


@app.route('/api/accounts/list', methods=['GET'])
def get_accounts():
    """Zoznam všetkých účtov"""
    
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    sql = """
    SELECT 
        AccountID,
        IBAN,
        AccountName,
        BankName,
        AccountType,
        Currency,
        IsActive
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


@app.route('/api/accounts/<int:account_id>/summary', methods=['GET'])
def get_account_summary(account_id):
    """Zhrnutie pre konkrétny účet"""
    
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    days = request.args.get('days', '30')
    
    # Info o účte
    account_sql = f"""
    SELECT 
        AccountID,
        IBAN,
        AccountName,
        BankName,
        AccountType
    FROM Accounts
    WHERE AccountID = {account_id} AND IsActive = 1;
    """
    
    account_result = turso_query(account_sql)
    
    if not account_result["success"] or not account_result["data"]:
        return jsonify({"error": "Account not found"}), 404
    
    # Štatistiky transakcií
    stats_sql = f"""
    SELECT 
        COUNT(*) as total_count,
        SUM(CASE WHEN Amount < 0 THEN Amount ELSE 0 END) as total_expenses,
        SUM(CASE WHEN Amount > 0 THEN Amount ELSE 0 END) as total_income,
        AVG(CASE WHEN Amount < 0 THEN Amount ELSE NULL END) as avg_expense,
        MIN(TransactionDate) as first_transaction,
        MAX(TransactionDate) as last_transaction
    FROM Transactions
    WHERE AccountID = {account_id}
        AND TransactionDate >= datetime('now', '-{days} days');
    """
    
    stats_result = turso_query(stats_sql)
    
    # Top kategórie
    categories_sql = f"""
    SELECT 
        c.Name as category_name,
        c.Icon as category_icon,
        COUNT(t.TransactionID) as transaction_count,
        SUM(t.Amount) as total_amount
    FROM Transactions t
    LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
    WHERE t.AccountID = {account_id}
        AND t.TransactionDate >= datetime('now', '-{days} days')
        AND t.Amount < 0
    GROUP BY c.CategoryID
    ORDER BY total_amount ASC
    LIMIT 5;
    """
    
    categories_result = turso_query(categories_sql)
    
    return jsonify({
        "account": account_result["data"][0] if account_result["data"] else {},
        "statistics": stats_result["data"][0] if stats_result["success"] and stats_result["data"] else {},
        "top_categories": categories_result["data"] if categories_result["success"] else [],
        "period_days": int(days)
    })


@app.route('/api/categories/list', methods=['GET'])
def get_categories():
    """Zoznam všetkých kategórií"""
    
    if not verify_api_key():
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
    print("=" * 60)
    print("🚀 Finance API Server pre ChatGPT GPTs")
    print("=" * 60)
    print(f"📡 Server beží na: http://localhost:8080")
    print(f"🔑 API Key: {API_KEY[:10]}...{API_KEY[-4:]}" if len(API_KEY) > 14 else f"🔑 API Key: {API_KEY}")
    print()
    print("📚 Dostupné endpointy:")
    print("  🏥 GET  /api/health")
    print("  📊 GET  /api/transactions/summary?days=30&account_id=1")
    print("  📋 GET  /api/transactions/recent?limit=10")
    print("  🏷️  GET  /api/transactions/by-category?days=30")
    print("  🏪 GET  /api/transactions/top-merchants?limit=10")
    print("  📅 GET  /api/transactions/monthly?months=6")
    print("  🔍 GET  /api/transactions/search?merchant=BOLT&account_id=1")
    print("  🏦 GET  /api/accounts/list")
    print("  📊 GET  /api/accounts/<id>/summary?days=30")
    print("  🏷️  GET  /api/categories/list")
    print()
    print("⚠️  Authorization: Bearer <API_KEY>")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=8080, debug=False)

