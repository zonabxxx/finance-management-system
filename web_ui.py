#!/usr/bin/env python3
"""
Flask Web UI - Dashboard pre správu financií
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import subprocess
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(app)

def turso_query(sql: str):
    """Vykonanie SQL query v Turso databáze a parsovanie do JSON"""
    try:
        result = subprocess.run(
            ['turso', 'db', 'shell', 'financa-sprava', sql],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) < 2:
                return {"success": True, "data": []}
            
            # Parse header
            header_line = lines[0]
            headers = [h.strip() for h in header_line.split('  ') if h.strip()]
            
            # Parse data rows
            parsed_data = []
            for line in lines[1:]:
                # Skip separator lines
                if not line.strip() or all(c in '-| ' for c in line):
                    continue
                
                # Split by multiple spaces
                values = [v.strip() for v in line.split('  ') if v.strip()]
                if len(values) == len(headers):
                    row_dict = dict(zip(headers, values))
                    parsed_data.append(row_dict)
            
            return {"success": True, "data": parsed_data, "headers": headers}
        else:
            return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.route('/')
def index():
    """Hlavná stránka - Dashboard"""
    return render_template('index.html')


@app.route('/api/dashboard/stats', methods=['GET'])
def dashboard_stats():
    """Získanie štatistík pre dashboard"""
    # Žiadna autentifikácia pre lokálny dashboard
    days = request.args.get('days', '30')
    
    # Celkové výdavky a príjmy
    sql_summary = f"""
    SELECT 
        COUNT(*) as total_transactions,
        COALESCE(SUM(CASE WHEN Amount < 0 THEN Amount ELSE 0 END), 0) as total_expenses,
        COALESCE(SUM(CASE WHEN Amount > 0 THEN Amount ELSE 0 END), 0) as total_income,
        COALESCE(AVG(CASE WHEN Amount < 0 THEN Amount ELSE NULL END), 0) as avg_expense
    FROM Transactions
    WHERE TransactionDate >= datetime('now', '-{days} days');
    """
    
    summary_result = turso_query(sql_summary)
    
    # Top kategórie
    sql_categories = f"""
    SELECT 
        COALESCE(c.Name, 'Nezaradené') as category,
        COUNT(t.TransactionID) as count,
        COALESCE(SUM(t.Amount), 0) as total
    FROM Transactions t
    LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
    WHERE t.TransactionDate >= datetime('now', '-{days} days')
        AND t.Amount < 0
    GROUP BY c.Name
    ORDER BY total ASC
    LIMIT 5;
    """
    
    categories_result = turso_query(sql_categories)
    
    # Posledné transakcie
    sql_recent = """
    SELECT 
        TransactionDate,
        Amount,
        Currency,
        MerchantName,
        PaymentMethod
    FROM Transactions
    ORDER BY TransactionDate DESC
    LIMIT 10;
    """
    
    recent_result = turso_query(sql_recent)
    
    return jsonify({
        "summary": summary_result["data"][0] if summary_result["success"] and summary_result["data"] else {},
        "categories": categories_result["data"] if categories_result["success"] else [],
        "recent_transactions": recent_result["data"] if recent_result["success"] else []
    })


@app.route('/api/dashboard/chart-data', methods=['GET'])
def chart_data():
    """Dáta pre grafy"""
    # Žiadna autentifikácia pre lokálny dashboard
    # Mesačné výdavky
    sql_monthly = """
    SELECT 
        strftime('%Y-%m', TransactionDate) as month,
        COALESCE(SUM(CASE WHEN Amount < 0 THEN ABS(Amount) ELSE 0 END), 0) as expenses,
        COALESCE(SUM(CASE WHEN Amount > 0 THEN Amount ELSE 0 END), 0) as income
    FROM Transactions
    WHERE TransactionDate >= datetime('now', '-6 months')
    GROUP BY month
    ORDER BY month ASC;
    """
    
    monthly_result = turso_query(sql_monthly)
    
    # Výdavky podľa kategórií
    sql_category_pie = """
    SELECT 
        COALESCE(c.Name, 'Nezaradené') as category,
        COALESCE(SUM(ABS(t.Amount)), 0) as total
    FROM Transactions t
    LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
    WHERE t.Amount < 0
        AND t.TransactionDate >= datetime('now', '-30 days')
    GROUP BY c.Name
    ORDER BY total DESC;
    """
    
    category_pie_result = turso_query(sql_category_pie)
    
    return jsonify({
        "monthly": monthly_result["data"] if monthly_result["success"] else [],
        "category_pie": category_pie_result["data"] if category_pie_result["success"] else []
    })


@app.route('/transactions')
def transactions_page():
    """Stránka so zoznamom transakcií"""
    return render_template('transactions.html')


@app.route('/categories')
def categories_page():
    """Stránka so správou kategórií"""
    return render_template('categories.html')


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
    name = data.get('name')
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
    name = data.get('name')
    icon = data.get('icon')
    color = data.get('color')
    
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


@app.route('/api/transactions/list', methods=['GET'])
def transactions_list():
    """Zoznam všetkých transakcií s filtráciou"""
    # Žiadna autentifikácia pre lokálny dashboard
    limit = request.args.get('limit', '50')
    offset = request.args.get('offset', '0')
    
    sql = f"""
    SELECT 
        t.TransactionID,
        t.TransactionDate,
        t.Amount,
        t.Currency,
        t.MerchantName,
        t.Description,
        t.PaymentMethod,
        COALESCE(c.Name, 'Nezaradené') as CategoryName
    FROM Transactions t
    LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
    ORDER BY t.TransactionDate DESC
    LIMIT {limit} OFFSET {offset};
    """
    
    result = turso_query(sql)
    
    return jsonify({
        "transactions": result["data"] if result["success"] else [],
        "limit": int(limit),
        "offset": int(offset)
    })


if __name__ == '__main__':
    print("=" * 60)
    print("🎨 Finance Dashboard UI")
    print("=" * 60)
    print(f"🌐 Dashboard: http://localhost:3000")
    print(f"📊 Transakcie: http://localhost:3000/transactions")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=3000, debug=True)

