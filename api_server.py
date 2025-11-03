#!/usr/bin/env python3
"""
Flask API Server pre ChatGPT GPT integráciu
Tento server poskytuje endpointy pre ChatGPT GPT aby mohol čítať finančné dáta
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import subprocess
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(app)  # Povoliť CORS pre OpenAI GPT

# API kľúč pre autentifikáciu (vygeneruj si vlastný)
API_KEY = os.getenv("API_KEY", "tvoj-tajny-api-key-123456")


def turso_query(sql: str):
    """Vykonanie SQL query v Turso databáze"""
    try:
        result = subprocess.run(
            ['turso', 'db', 'shell', 'financa-sprava', sql],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Parsovanie výstupu
            lines = result.stdout.strip().split('\n')
            return {"success": True, "data": lines}
        else:
            return {"success": False, "error": result.stderr}
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
    
    sql = f"""
    SELECT 
        COUNT(*) as total_count,
        SUM(CASE WHEN Amount < 0 THEN Amount ELSE 0 END) as total_expenses,
        SUM(CASE WHEN Amount > 0 THEN Amount ELSE 0 END) as total_income,
        AVG(CASE WHEN Amount < 0 THEN Amount ELSE NULL END) as avg_expense
    FROM Transactions
    WHERE TransactionDate >= datetime('now', '-{days} days');
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({
            "period_days": int(days),
            "data": result["data"]
        })
    else:
        return jsonify({"error": result["error"]}), 500


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
    
    conditions = []
    if merchant:
        conditions.append(f"MerchantName LIKE '%{merchant}%'")
    if min_amount:
        conditions.append(f"Amount >= {min_amount}")
    if max_amount:
        conditions.append(f"Amount <= {max_amount}")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    sql = f"""
    SELECT 
        TransactionDate,
        Amount,
        Currency,
        MerchantName,
        Description
    FROM Transactions
    WHERE {where_clause}
    ORDER BY TransactionDate DESC
    LIMIT 50;
    """
    
    result = turso_query(sql)
    
    if result["success"]:
        return jsonify({
            "results": result["data"]
        })
    else:
        return jsonify({"error": result["error"]}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Finance API Server")
    print("=" * 60)
    print(f"📡 Server beží na: http://localhost:8080")
    print(f"🔑 API Key: {API_KEY}")
    print()
    print("📚 Dostupné endpointy:")
    print("  GET /api/health - Health check")
    print("  GET /api/transactions/summary?days=30")
    print("  GET /api/transactions/recent?limit=10")
    print("  GET /api/transactions/by-category?days=30")
    print("  GET /api/transactions/top-merchants?limit=10")
    print("  GET /api/transactions/monthly?months=6")
    print("  GET /api/transactions/search?merchant=TESCO")
    print()
    print("⚠️  Pre použitie pridaj hlavičku: Authorization: Bearer <API_KEY>")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=8080, debug=True)

