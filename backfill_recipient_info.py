#!/usr/bin/env python3
"""
Backfill RecipientInfo and CounterpartyPurpose for old transactions
Extract from RawEmailData
"""

import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

TURSO_DATABASE_URL = os.getenv('TURSO_DATABASE_URL', '')
TURSO_AUTH_TOKEN = os.getenv('TURSO_AUTH_TOKEN', '')

if TURSO_DATABASE_URL.startswith('libsql://'):
    TURSO_HTTP_URL = TURSO_DATABASE_URL.replace('libsql://', 'https://')
else:
    TURSO_HTTP_URL = TURSO_DATABASE_URL

def turso_query(sql: str):
    """Execute SQL query in Turso"""
    response = requests.post(
        f"{TURSO_HTTP_URL}/v2/pipeline",
        headers={
            "Authorization": f"Bearer {TURSO_AUTH_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "requests": [{"type": "execute", "stmt": {"sql": sql}}]
        },
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('results') and len(result['results']) > 0:
            response_obj = result['results'][0]['response']
            if response_obj.get('type') == 'error':
                print(f"❌ Error: {response_obj.get('error', {}).get('message')}")
                return None
            
            query_result = response_obj.get('result', {})
            columns = [col['name'] for col in query_result.get('cols', [])]
            rows = query_result.get('rows', [])
            
            data = []
            for row in rows:
                row_dict = {}
                for i, col_name in enumerate(columns):
                    cell = row[i]
                    if isinstance(cell, dict) and 'value' in cell:
                        value = cell['value']
                        if cell.get('type') == 'integer':
                            row_dict[col_name] = int(value) if value is not None else None
                        elif cell.get('type') == 'real':
                            row_dict[col_name] = float(value) if value is not None else None
                        else:
                            row_dict[col_name] = value
                    else:
                        row_dict[col_name] = cell
                data.append(row_dict)
            
            return data
    return None

def extract_from_email(email_body: str):
    """Extract RecipientInfo and CounterpartyPurpose from B-mail"""
    if not email_body:
        return None, None
    
    # Extract "Informacia pre prijemcu:"
    recipient_info = None
    recipient_match = re.search(r'Informacia pre prijemcu:\s*(.+?)(?:\n|$)', email_body, re.IGNORECASE)
    if recipient_match:
        recipient_info = recipient_match.group(1).strip()
    
    # Extract "Ucel protistrany:"
    counterparty_purpose = None
    purpose_match = re.search(r'Ucel protistrany:\s*(.+?)(?:\n|$)', email_body, re.IGNORECASE)
    if purpose_match:
        counterparty_purpose = purpose_match.group(1).strip()
    
    return recipient_info, counterparty_purpose

def main():
    print("🔧 Backfilling RecipientInfo and CounterpartyPurpose...")
    print("=" * 60)
    
    # Get all transactions with RawEmailData but missing RecipientInfo
    sql = """
    SELECT TransactionID, RawEmailData 
    FROM Transactions 
    WHERE RawEmailData IS NOT NULL 
      AND RawEmailData != ''
      AND (RecipientInfo IS NULL OR RecipientInfo = '')
    ORDER BY TransactionID DESC
    LIMIT 100;
    """
    
    transactions = turso_query(sql)
    
    if not transactions:
        print("✅ No transactions to update (all already have recipient info)")
        return
    
    print(f"📊 Found {len(transactions)} transactions to update\n")
    
    updated = 0
    skipped = 0
    
    for tx in transactions:
        tx_id = tx.get('TransactionID')
        raw_email = tx.get('RawEmailData')
        
        # Extract info from email
        recipient_info, counterparty_purpose = extract_from_email(raw_email)
        
        if not recipient_info and not counterparty_purpose:
            print(f"⚠️  ID={tx_id}: No recipient info found in email")
            skipped += 1
            continue
        
        # Build update query
        updates = []
        if recipient_info:
            escaped_info = recipient_info.replace("'", "''")
            updates.append(f"RecipientInfo = '{escaped_info}'")
        if counterparty_purpose:
            escaped_purpose = counterparty_purpose.replace("'", "''")
            updates.append(f"CounterpartyPurpose = '{escaped_purpose}'")
        
        if not updates:
            skipped += 1
            continue
        
        update_sql = f"""
        UPDATE Transactions 
        SET {', '.join(updates)}
        WHERE TransactionID = {tx_id};
        """
        
        result = turso_query(update_sql)
        
        if result is not None:
            print(f"✅ ID={tx_id}: Updated")
            if recipient_info:
                print(f"   📝 RecipientInfo: {recipient_info}")
            if counterparty_purpose:
                print(f"   🎯 CounterpartyPurpose: {counterparty_purpose}")
            updated += 1
        else:
            print(f"❌ ID={tx_id}: Update failed")
    
    print("\n" + "=" * 60)
    print(f"✅ Updated: {updated}")
    print(f"⚠️  Skipped: {skipped}")
    print(f"📊 Total: {len(transactions)}")

if __name__ == '__main__':
    main()

