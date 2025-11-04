#!/usr/bin/env python3
"""
Railway Background Worker - Automatické spracovanie B-mail notifikácií
Beží na Railway 24/7 a kontroluje Gmail každých 60 sekúnd
"""

import time
import imaplib
import email
from email.header import decode_header
import re
from datetime import datetime
from typing import Dict, Optional
import os
import requests
import json

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configuration
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_IMAP_SERVER = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
CHECK_INTERVAL = int(os.getenv("EMAIL_CHECK_INTERVAL", "60"))  # default 60s


class EmailReceiver:
    """Gmail IMAP receiver pre Railway"""
    
    def __init__(self, email_address: str, password: str, imap_server: str):
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server
        self.mail = None
    
    def connect(self):
        """Pripojenie k Gmail"""
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server)
            self.mail.login(self.email_address, self.password)
            print(f"✅ Pripojený k {self.email_address}")
            return True
        except Exception as e:
            print(f"❌ Chyba pri pripojení: {e}")
            return False
    
    def disconnect(self):
        """Odpojenie od Gmail"""
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
            except:
                pass
    
    def get_bmails(self):
        """Získanie B-mail notifikácií"""
        if not self.mail:
            if not self.connect():
                return []
        
        try:
            self.mail.select("INBOX")
            status, messages = self.mail.search(None, '(FROM "b-mail@tatrabanka.sk")')
            
            if status != "OK":
                return []
            
            email_ids = messages[0].split()
            
            emails = []
            for email_id in email_ids:
                try:
                    status, msg_data = self.mail.fetch(email_id, "(RFC822)")
                    if status != "OK":
                        continue
                    
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            emails.append(self._parse_email(msg))
                except Exception as e:
                    print(f"⚠️  Chyba pri spracovaní emailu: {e}")
            
            return emails
        except Exception as e:
            print(f"❌ Chyba pri získavaní emailov: {e}")
            return []
    
    def _parse_email(self, msg) -> Dict:
        """Parsovanie email správy"""
        subject = ""
        if msg["Subject"]:
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")
        
        date = msg["Date"]
        
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
        
        return {
            "subject": subject,
            "date": date,
            "body": body,
            "from": msg["From"]
        }


class BMailParser:
    """Parser pre B-mail z Tatra banky"""
    
    @staticmethod
    def parse_transaction(email_body: str) -> Optional[Dict]:
        """Parsovanie B-mail transakcie"""
        transaction = {}
        
        try:
            # Extrahovanie dátumu, IBAN a sumy
            main_match = re.search(
                r'(\d{1,2}\.\d{1,2}\.\d{4})\s+(\d{1,2}:\d{2})\s+bol zostatok.*?'
                r'(SK\d+)\s+(znizeny|zvyseny)\s+o\s+([\d,]+)\s*EUR',
                email_body
            )
            
            if not main_match:
                return None
            
            # Dátum a čas
            date_str = f"{main_match.group(1)} {main_match.group(2)}"
            transaction['date'] = datetime.strptime(date_str, "%d.%m.%Y %H:%M")
            
            # IBAN
            transaction['iban'] = main_match.group(3)
            
            # Suma (znizeny = mínus, zvyseny = plus)
            amount_str = main_match.group(5).replace(',', '.')
            amount = float(amount_str)
            if main_match.group(4) == 'znizeny':
                amount = -amount
            transaction['amount'] = amount
            
            # Popis transakcie
            desc_match = re.search(r'Popis transakcie:\s*(.+?)(?:\n|$)', email_body)
            if desc_match:
                description = desc_match.group(1).strip()
                transaction['description'] = description
                
                # Extrakcia obchodníka
                if 'Platba kartou' in description:
                    transaction['payment_method'] = 'Card'
                    merchant_match = re.search(r',\s*([A-Z0-9\.\-]+)', description)
                    if merchant_match:
                        merchant_raw = merchant_match.group(1).strip('.')
                        merchant = re.sub(r'\.?[A-Z]{3}\d+$', '', merchant_raw)
                        transaction['merchant'] = merchant if merchant else merchant_raw
                    else:
                        transaction['merchant'] = 'Unknown'
                elif 'Prevod' in description or 'Prikaz' in description:
                    transaction['payment_method'] = 'Transfer'
                    transaction['merchant'] = description
                else:
                    transaction['payment_method'] = 'Other'
                    transaction['merchant'] = description
            
            transaction['transaction_type'] = 'Debit' if transaction['amount'] < 0 else 'Credit'
            transaction['raw_email'] = email_body
            
            return transaction
            
        except Exception as e:
            print(f"❌ Chyba pri parsovaní: {e}")
            return None


def turso_query(query: str):
    """Vykonanie SQL query na Turso cez HTTP API"""
    try:
        response = requests.post(
            f"{TURSO_DATABASE_URL}/v2/pipeline",
            headers={
                "Authorization": f"Bearer {TURSO_AUTH_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "requests": [
                    {"type": "execute", "stmt": {"sql": query}},
                    {"type": "close"}
                ]
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "results" in data and len(data["results"]) > 0:
                return data["results"][0]["response"]
        
        return None
    except Exception as e:
        print(f"❌ Turso query error: {e}")
        return None


def get_account_id_by_iban(iban: str) -> Optional[int]:
    """Nájdenie AccountID podľa IBAN"""
    query = f"SELECT AccountID FROM Accounts WHERE IBAN = '{iban}' AND IsActive = 1 LIMIT 1;"
    result = turso_query(query)
    
    if result and "rows" in result and len(result["rows"]) > 0:
        return int(result["rows"][0][0]["value"])
    
    return None


def save_transaction(transaction: Dict) -> bool:
    """Uloženie transakcie do Turso databázy"""
    try:
        # Nájdenie AccountID
        account_id = get_account_id_by_iban(transaction.get('iban', ''))
        account_id_sql = str(account_id) if account_id else 'NULL'
        
        if account_id:
            print(f"  🏦 Účet: AccountID = {account_id}")
        else:
            print(f"  ⚠️  Účet s IBAN {transaction.get('iban')} neexistuje v Settings")
        
        # SQL INSERT
        query = f"""
        INSERT INTO Transactions (
            TransactionDate,
            Amount,
            Currency,
            MerchantName,
            Description,
            IBAN,
            TransactionType,
            PaymentMethod,
            RawEmailData,
            CategorySource,
            AccountID,
            CreatedAt
        ) VALUES (
            '{transaction['date'].isoformat()}',
            {transaction['amount']},
            'EUR',
            '{transaction.get('merchant', 'Unknown').replace("'", "''")}',
            '{transaction.get('description', '').replace("'", "''")}',
            '{transaction.get('iban', '')}',
            '{transaction.get('transaction_type', 'Debit')}',
            '{transaction.get('payment_method', 'Other')}',
            '{transaction.get('raw_email', '').replace("'", "''")}',
            'Email',
            {account_id_sql},
            '{datetime.now().isoformat()}'
        );
        """
        
        result = turso_query(query)
        
        if result:
            print(f"✅ Transakcia uložená: {transaction['merchant']} - {transaction['amount']} EUR")
            return True
        else:
            print(f"❌ Chyba pri ukladaní transakcie")
            return False
    
    except Exception as e:
        print(f"❌ Chyba: {e}")
        return False


def monitor_emails():
    """Hlavná funkcia - kontinuálne monitorovanie"""
    print("=" * 60)
    print("🚀 Railway B-mail Worker STARTED")
    print("=" * 60)
    print(f"📧 Email: {EMAIL_ADDRESS}")
    print(f"⏱️  Interval: {CHECK_INTERVAL}s")
    print(f"🗄️  Database: {TURSO_DATABASE_URL[:50]}...")
    print("=" * 60)
    print()
    
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("❌ EMAIL_ADDRESS alebo EMAIL_PASSWORD nie sú nastavené!")
        return
    
    if not TURSO_DATABASE_URL or not TURSO_AUTH_TOKEN:
        print("❌ TURSO_DATABASE_URL alebo TURSO_AUTH_TOKEN nie sú nastavené!")
        return
    
    receiver = EmailReceiver(EMAIL_ADDRESS, EMAIL_PASSWORD, EMAIL_IMAP_SERVER)
    parser = BMailParser()
    
    check_count = 0
    processed_count = 0
    
    while True:
        try:
            check_count += 1
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"[{current_time}] 🔍 Check #{check_count}...", end=" ", flush=True)
            
            # Kontrola emailov
            emails = receiver.get_bmails()
            
            if not emails:
                print("📭 No new B-mails")
            else:
                print(f"\n📨 Found {len(emails)} B-mails!")
                print("-" * 60)
                
                for i, email_data in enumerate(emails, 1):
                    print(f"\n📧 Email {i}/{len(emails)}")
                    print(f"   Subject: {email_data['subject']}")
                    
                    transaction = parser.parse_transaction(email_data['body'])
                    
                    if transaction:
                        print(f"   💰 Amount: {transaction['amount']} EUR")
                        print(f"   🏪 Merchant: {transaction.get('merchant', 'N/A')}")
                        
                        if save_transaction(transaction):
                            processed_count += 1
                    else:
                        print("   ⚠️  Failed to parse transaction")
                
                print("-" * 60)
                print(f"✅ Total processed: {processed_count}\n")
            
            # Odpojenie (nové spojenie pri každom checku)
            receiver.disconnect()
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Počkaj pred ďalšou kontrolou
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    monitor_emails()

