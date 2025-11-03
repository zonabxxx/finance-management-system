#!/usr/bin/env python3
"""
B-mail Monitor - Automatické sledovanie a spracovanie B-mail notifikácií
Beží v pozadí a kontroluje nové emaily každých 30 sekúnd
"""

import time
from email_receiver import EmailReceiver, BMailParser, save_transaction_to_db
from dotenv import load_dotenv
import os
from datetime import datetime

def monitor_bmails(check_interval: int = 30):
    """
    Monitorovanie B-mail notifikácií
    
    Args:
        check_interval: Interval kontroly v sekundách (default: 30s)
    """
    print("🚀 B-mail Monitor spustený")
    print("=" * 60)
    print(f"⏱️  Kontrolujem nové B-maily každých {check_interval} sekúnd")
    print("⌨️  Pre ukončenie stlačte Ctrl+C")
    print("=" * 60)
    print()
    
    load_dotenv()
    
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    IMAP_SERVER = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
    
    receiver = EmailReceiver(EMAIL_ADDRESS, EMAIL_PASSWORD, IMAP_SERVER)
    parser = BMailParser()
    
    check_count = 0
    processed_count = 0
    
    try:
        while True:
            check_count += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            
            print(f"[{current_time}] 🔍 Kontrola #{check_count}...", end=" ")
            
            try:
                # Pripojenie a získanie nových emailov
                if not receiver.connect():
                    print("❌ Chyba pripojenia")
                    time.sleep(check_interval)
                    continue
                
                emails = receiver.get_unread_emails()
                
                if not emails:
                    print("📭 Žiadne nové")
                else:
                    print(f"\n📨 Nájdených {len(emails)} nových B-mailov!")
                    print("-" * 60)
                    
                    for i, email_data in enumerate(emails, 1):
                        print(f"\n📧 Email {i}/{len(emails)}")
                        print(f"   Predmet: {email_data['subject']}")
                        
                        # Parsovanie transakcie
                        transaction = parser.parse_transaction(email_data['body'])
                        
                        if transaction:
                            print(f"   💰 Suma: {transaction['amount']} EUR")
                            print(f"   🏪 Obchodník: {transaction.get('merchant', 'N/A')}")
                            print(f"   📅 Dátum: {transaction['date']}")
                            
                            # Uloženie do databázy
                            if save_transaction_to_db(transaction):
                                processed_count += 1
                                print(f"   ✅ Uložené do databázy")
                            else:
                                print(f"   ❌ Nepodarilo sa uložiť")
                        else:
                            print("   ⚠️  Nepodarilo sa extrahovať údaje")
                    
                    print("-" * 60)
                    print(f"✅ Celkom spracovaných: {processed_count}")
                    print()
                
                receiver.disconnect()
                
            except Exception as e:
                print(f"❌ Chyba: {e}")
            
            # Počkaj pred ďalšou kontrolou
            time.sleep(check_interval)
    
    except KeyboardInterrupt:
        print("\n")
        print("=" * 60)
        print("🛑 Monitor zastavený")
        print(f"📊 Štatistika:")
        print(f"   - Celkovo kontrol: {check_count}")
        print(f"   - Spracovaných transakcií: {processed_count}")
        print("=" * 60)
        receiver.disconnect()


if __name__ == "__main__":
    # Môžeš zmeniť interval (v sekundách)
    # Pre rýchlejšie testovanie: monitor_bmails(10)
    # Pre normálne používanie: monitor_bmails(60)
    monitor_bmails(check_interval=30)

