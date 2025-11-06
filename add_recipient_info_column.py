#!/usr/bin/env python3
"""
Add RecipientInfo column to Transactions table
"""

import os
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
                error_msg = response_obj.get('error', {}).get('message', 'Unknown error')
                return {"success": False, "error": error_msg}
            return {"success": True}
    return {"success": False, "error": "Query failed"}

def main():
    print("🔧 Adding RecipientInfo and CounterpartyPurpose columns to Transactions table...")
    print("=" * 60)
    
    # Add RecipientInfo column
    sql1 = """
    ALTER TABLE Transactions 
    ADD COLUMN RecipientInfo TEXT;
    """
    
    print("Adding RecipientInfo column...")
    result1 = turso_query(sql1)
    
    if result1["success"]:
        print("✅ RecipientInfo column added")
    else:
        if "duplicate column name" in result1.get("error", "").lower():
            print("ℹ️  RecipientInfo column already exists")
        else:
            print(f"❌ Failed to add RecipientInfo: {result1.get('error')}")
    
    # Add CounterpartyPurpose column
    sql2 = """
    ALTER TABLE Transactions 
    ADD COLUMN CounterpartyPurpose TEXT;
    """
    
    print("Adding CounterpartyPurpose column...")
    result2 = turso_query(sql2)
    
    if result2["success"]:
        print("✅ CounterpartyPurpose column added")
    else:
        if "duplicate column name" in result2.get("error", "").lower():
            print("ℹ️  CounterpartyPurpose column already exists")
        else:
            print(f"❌ Failed to add CounterpartyPurpose: {result2.get('error')}")
    
    print("\n" + "=" * 60)
    print("✅ Database schema updated!")
    print("\nTeraz môžeš ukladať:")
    print("  - RecipientInfo: 'Adam Martinkovych 4.A'")
    print("  - CounterpartyPurpose: účel platby")

if __name__ == '__main__':
    main()

