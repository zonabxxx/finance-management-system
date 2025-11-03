#!/usr/bin/env python3
"""
Email Receiver - Prijímanie a spracovanie B-mail notifikácií
"""

import imaplib
import email
from email.header import decode_header
import re
from datetime import datetime
from typing import Dict, Optional
import subprocess
import json

class EmailReceiver:
    def __init__(self, email_address: str, password: str, imap_server: str = "imap.gmail.com"):
        """
        Inicializácia email prijímača
        
        Args:
            email_address: Email adresa
            password: Heslo (pre Gmail použite App Password)
            imap_server: IMAP server (default: Gmail)
        """
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server
        self.mail = None
    
    def connect(self):
        """Pripojenie k email serveru"""
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server)
            self.mail.login(self.email_address, self.password)
            print(f"✅ Pripojený k {self.email_address}")
            return True
        except Exception as e:
            print(f"❌ Chyba pri pripojení: {e}")
            return False
    
    def disconnect(self):
        """Odpojenie od email serveru"""
        if self.mail:
            self.mail.close()
            self.mail.logout()
    
    def get_unread_emails(self, folder: str = "INBOX") -> list:
        """
        Získanie neprečítaných emailov
        
        Args:
            folder: Priečinok (default: INBOX)
            
        Returns:
            List emailov
        """
        if not self.mail:
            self.connect()
        
        self.mail.select(folder)
        
        # Hľadáme VŠETKY emaily od B-mail (aj prečítané)
        status, messages = self.mail.search(None, '(FROM "b-mail@tatrabanka.sk")')
        
        if status != "OK":
            print(f"❌ Status nie je OK: {status}")
            return []
        
        email_ids = messages[0].split()
        print(f"🔍 Nájdených emailov: {len(email_ids)}")
        
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
                print(f"❌ Chyba pri spracovaní emailu {email_id}: {e}")
        
        return emails
    
    def _parse_email(self, msg) -> Dict:
        """Parsovanie email správy"""
        # Dekódovanie predmetu
        subject = ""
        if msg["Subject"]:
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")
        
        # Získanie dátumu
        date = msg["Date"]
        
        # Získanie tela emailu
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
    """Parser pre B-mail notifikácie z Tatra banky"""
    
    @staticmethod
    def parse_transaction(email_body: str) -> Optional[Dict]:
        """
        Parsovanie B-mail notifikácie z Tatra banky
        
        Príklad skutočného B-mail formátu:
        -------------------------
        3.11.2025 13:01 bol zostatok Vasho uctu SK8911000000002933213912 znizeny o 10,18 EUR.
        uctovny zostatok:                               878,06 EUR
        Popis transakcie: Platba kartou 4405**9645, BOLT.EUD2511031201.
        -------------------------
        """
        transaction = {}
        
        try:
            # Extrahovanie dátumu a sumy z prvého riadku
            # Formát: "3.11.2025 13:01 bol zostatok Vasho uctu SKXXXX znizeny o 10,18 EUR"
            main_match = re.search(
                r'(\d{1,2}\.\d{1,2}\.\d{4})\s+(\d{1,2}:\d{2})\s+bol zostatok.*?'
                r'(SK\d+)\s+(znizeny|zvyseny)\s+o\s+([\d,]+)\s*EUR',
                email_body
            )
            
            if main_match:
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
            else:
                print("⚠️  Nepodarilo sa extrahovať základné údaje")
                return None
            
            # Extrahovanie popisu transakcie
            desc_match = re.search(r'Popis transakcie:\s*(.+?)(?:\n|$)', email_body)
            if desc_match:
                description = desc_match.group(1).strip()
                transaction['description'] = description
                
                # Extrakcia obchodníka z popisu
                # Formát: "Platba kartou 4405**9645, BOLT.EUD2511031201."
                if 'Platba kartou' in description:
                    transaction['payment_method'] = 'Card'
                    # Extrakcia obchodníka (časť po čiarke)
                    merchant_match = re.search(r',\s*([A-Z0-9\.\-]+)', description)
                    if merchant_match:
                        merchant_raw = merchant_match.group(1).strip('.')
                        # Očistíme referenčné čísla
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
            
            # Typ transakcie
            transaction['transaction_type'] = 'Debit' if transaction['amount'] < 0 else 'Credit'
            
            # Celý email ako raw data
            transaction['raw_email'] = email_body
            
            return transaction
            
        except Exception as e:
            print(f"❌ Chyba pri parsovaní: {e}")
            return None


def save_transaction_to_db(transaction: Dict) -> bool:
    """
    Uloženie transakcie do Turso databázy cez CLI
    
    Args:
        transaction: Dictionary s údajmi transakcie
        
    Returns:
        True ak úspešné, False inak
    """
    try:
        # Pripravíme SQL query
        query = f"""
        INSERT INTO Transactions (
            TransactionDate,
            Amount,
            Currency,
            MerchantName,
            Description,
            IBAN,
            VariableSymbol,
            TransactionType,
            PaymentMethod,
            CO2Footprint,
            RawEmailData,
            CategorySource,
            CreatedAt
        ) VALUES (
            '{transaction['date'].isoformat()}',
            {transaction['amount']},
            'EUR',
            '{transaction.get('merchant', 'Unknown').replace("'", "''")}',
            '{transaction.get('description', '').replace("'", "''")}',
            '{transaction.get('iban', '')}',
            '{transaction.get('variable_symbol', '')}',
            '{transaction.get('transaction_type', 'Debit')}',
            '{transaction.get('payment_method', 'Other')}',
            {transaction.get('co2_footprint', 0)},
            '{transaction.get('raw_email', '').replace("'", "''")}',
            'Email',
            '{datetime.now().isoformat()}'
        );
        """
        
        # Vykonáme cez Turso CLI
        result = subprocess.run(
            ['turso', 'db', 'shell', 'financa-sprava', query],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Transakcia uložená: {transaction['merchant']} - {transaction['amount']} EUR")
            return True
        else:
            print(f"❌ Chyba pri ukladaní: {result.stderr}")
            return False
    
    except Exception as e:
        print(f"❌ Chyba: {e}")
        return False


def main():
    """Hlavná funkcia - spracovanie B-mail notifikácií"""
    
    print("📧 B-mail Email Receiver")
    print("=" * 50)
    
    # Načítanie z .env súboru
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "vas.email@gmail.com")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "vase-app-heslo")
    IMAP_SERVER = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
    
    if EMAIL_ADDRESS == "vas.email@gmail.com" or EMAIL_PASSWORD == "vase-app-heslo":
        print("\n⚠️  UPOZORNENIE: Musíte nastaviť email prihlasovacie údaje!")
        print("1. Vytvorte Gmail účet pre B-mail notifikácie")
        print("2. Povoľte 2FA a vytvorte App Password")
        print("3. Pridajte do .env súboru:")
        print("   EMAIL_ADDRESS=vas.email@gmail.com")
        print("   EMAIL_PASSWORD=your-app-password")
        print("\n📖 Podrobný návod: EMAIL_SETUP.md")
        return
    
    # Pripojenie k email serveru
    receiver = EmailReceiver(EMAIL_ADDRESS, EMAIL_PASSWORD, IMAP_SERVER)
    
    if not receiver.connect():
        return
    
    # Získanie emailov
    print("\n📬 Kontrolujem B-mail notifikácie...")
    emails = receiver.get_unread_emails()
    
    if not emails:
        print("📭 Žiadne B-mail notifikácie")
        receiver.disconnect()
        return
    
    print(f"\n📨 Našiel som {len(emails)} B-mail notifikácií\n")
    
    # Spracovanie každého emailu
    parser = BMailParser()
    success_count = 0
    
    for i, email_data in enumerate(emails, 1):
        print(f"\n--- Email {i}/{len(emails)} ---")
        print(f"Predmet: {email_data['subject']}")
        
        # Parsovanie transakcie
        transaction = parser.parse_transaction(email_data['body'])
        
        if transaction:
            print(f"💰 Suma: {transaction['amount']} EUR")
            print(f"🏪 Obchodník: {transaction.get('merchant', 'N/A')}")
            print(f"📅 Dátum: {transaction['date']}")
            
            # Uloženie do databázy
            if save_transaction_to_db(transaction):
                success_count += 1
                
                # Pokúsime sa automaticky kategorizovať
                try:
                    from auto_categorize import AutoCategorizer
                    categorizer = AutoCategorizer()
                    
                    # Získame ID poslednej vloženej transakcie
                    result = subprocess.run(
                        ['turso', 'db', 'shell', 'financa-sprava',
                         'SELECT TransactionID FROM Transactions ORDER BY TransactionID DESC LIMIT 1;'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        if len(lines) > 1:
                            transaction_id = int(lines[1].strip())
                            print(f"\n🤖 Automatická kategorizácia...")
                            categorizer.categorize_transaction(
                                transaction_id,
                                transaction.get('merchant', 'Unknown'),
                                transaction.get('description', ''),
                                transaction['amount']
                            )
                except Exception as e:
                    print(f"⚠️  Auto-kategorizácia zlyhala: {e}")
        else:
            print("❌ Nepodarilo sa extrahovať údaje")
    
    # Odpojenie
    receiver.disconnect()
    
    print("\n" + "=" * 50)
    print(f"✅ Úspešne spracovaných: {success_count}/{len(emails)}")


if __name__ == "__main__":
    main()

