"""
Príklady použitia Finance Tracker systému
"""
from datetime import datetime, timedelta
from email_parser import parse_bmail_notification
from finstat_client import get_company_info
from ai_categorization import categorize_transaction
from database_client import db_client
from chatgpt_agent import ask_finance_question


def example_1_parse_email():
    """Príklad: Parsovanie B-mail notifikácie"""
    print("\n" + "="*60)
    print("PRÍKLAD 1: Parsovanie B-mail emailu")
    print("="*60)
    
    # Simulovaný B-mail email
    sample_email = """
    3. novembra 2025
    
    KAUFLAND 1120, PO, LEVO
    Platba kartou 4405**9645
    
    23,00 EUR
    4,80 kg CO₂e
    """
    
    result = parse_bmail_notification(sample_email)
    
    if result:
        print("\n✅ Email úspešne parsovaný:")
        print(f"  • Obchodník: {result['merchant_name']}")
        print(f"  • Suma: {result['amount']} {result['currency']}")
        print(f"  • Dátum: {result['transaction_date']}")
        print(f"  • CO2 stopa: {result['co2_footprint']} kg")
    else:
        print("\n❌ Parsovanie zlyhalo")


def example_2_finstat_lookup():
    """Príklad: Vyhľadanie firmy cez Finstat"""
    print("\n" + "="*60)
    print("PRÍKLAD 2: Finstat API - identifikácia firmy")
    print("="*60)
    
    # Vyhľadaj firmu podľa IČO
    print("\n📞 Vyhľadávam firmu s IČO 31333532...")
    company = get_company_info(ico="31333532")
    
    if company:
        print(f"\n✅ Firma nájdená:")
        print(f"  • Názov: {company.name}")
        print(f"  • IČO: {company.ico}")
        print(f"  • Činnosť: {company.activity}")
        print(f"  • Navrhovaná kategória: {company.suggested_category}")
    else:
        print("\n❌ Firma nenájdená")


def example_3_ai_categorization():
    """Príklad: AI kategorizácia transakcie"""
    print("\n" + "="*60)
    print("PRÍKLAD 3: AI Kategorizácia")
    print("="*60)
    
    test_transactions = [
        ("KAUFLAND 1120", 23.00),
        ("DR.MAX 039, PO Levocska", 12.48),
        ("U Kocmundu Biely kríz", 8.00),
        ("NETFLIX", 9.99),
        ("Neznámy obchod XYZ", 50.00)
    ]
    
    for merchant, amount in test_transactions:
        print(f"\n🔍 Kategorizujem: {merchant} ({amount} EUR)")
        
        result = categorize_transaction(
            merchant_name=merchant,
            amount=amount
        )
        
        print(f"  ✓ Kategória: {result.category}")
        print(f"  ✓ Istota: {result.confidence:.0%}")
        print(f"  ✓ Zdroj: {result.source}")
        print(f"  ✓ Odôvodnenie: {result.reasoning}")


def example_4_save_transaction():
    """Príklad: Uloženie transakcie do databázy"""
    print("\n" + "="*60)
    print("PRÍKLAD 4: Uloženie transakcie do Azure SQL")
    print("="*60)
    
    try:
        # Vytvor obchodníka
        merchant_id = db_client.get_or_create_merchant(
            name="KAUFLAND 1120",
            iban="SK8911200000198742637541"
        )
        print(f"\n✅ Obchodník ID: {merchant_id}")
        
        # Získaj kategóriu
        category_id = db_client.get_category_id_by_name("Potraviny")
        print(f"✅ Kategória ID: {category_id}")
        
        # Ulož transakciu
        transaction_id = db_client.insert_transaction(
            transaction_date=datetime.now(),
            amount=23.00,
            merchant_name="KAUFLAND 1120",
            merchant_id=merchant_id,
            category_id=category_id,
            payment_method="Card",
            co2_footprint=4.80,
            ai_confidence=0.95,
            category_source="Rule"
        )
        
        print(f"✅ Transakcia uložená s ID: {transaction_id}")
        
    except Exception as e:
        print(f"❌ Chyba: {e}")


def example_5_get_transactions():
    """Príklad: Získanie transakcií z databázy"""
    print("\n" + "="*60)
    print("PRÍKLAD 5: Získanie transakcií")
    print("="*60)
    
    try:
        # Transakcie za posledných 30 dní
        start_date = datetime.now() - timedelta(days=30)
        
        transactions = db_client.get_transactions(
            start_date=start_date,
            limit=10
        )
        
        print(f"\n📊 Nájdených transakcií: {len(transactions)}")
        
        for t in transactions[:5]:
            print(f"\n  {t['TransactionDate'].strftime('%d.%m.%Y')}")
            print(f"  {t['MerchantName']}: {t['Amount']:.2f} {t['Currency']}")
            print(f"  Kategória: {t['CategoryName']}")
        
    except Exception as e:
        print(f"❌ Chyba: {e}")


def example_6_monthly_summary():
    """Príklad: Mesačný prehľad"""
    print("\n" + "="*60)
    print("PRÍKLAD 6: Mesačný prehľad výdavkov")
    print("="*60)
    
    try:
        now = datetime.now()
        summary = db_client.get_monthly_summary(now.year, now.month)
        
        print(f"\n📈 Prehľad za {now.month}/{now.year}:")
        print(f"\n  Celkové výdavky: {summary['total_amount']:.2f} EUR")
        print(f"  Počet transakcií: {summary['transaction_count']}")
        print(f"  Priemerná transakcia: {summary['avg_amount']:.2f} EUR")
        
        print(f"\n  📊 Rozpad podľa kategórií:")
        for cat in summary['by_category'][:5]:
            percentage = (cat['total'] / summary['total_amount'] * 100) if summary['total_amount'] > 0 else 0
            print(f"    • {cat['category']}: {cat['total']:.2f} EUR ({percentage:.1f}%)")
        
    except Exception as e:
        print(f"❌ Chyba: {e}")


def example_7_chatgpt_agent():
    """Príklad: ChatGPT Agent dotazy"""
    print("\n" + "="*60)
    print("PRÍKLAD 7: ChatGPT Agent - Analýza financií")
    print("="*60)
    
    questions = [
        "Koľko som minul tento mesiac?",
        "Aké sú moje najčastejšie výdavky?",
        "Ukáž mi transakcie za november na potraviny"
    ]
    
    thread_id = None
    
    for question in questions:
        print(f"\n❓ Otázka: {question}")
        print("-" * 60)
        
        try:
            response = ask_finance_question(question, thread_id)
            thread_id = response['thread_id']
            
            print(f"🤖 Odpoveď: {response['response']}\n")
            
        except Exception as e:
            print(f"❌ Chyba: {e}")


def example_8_full_workflow():
    """Príklad: Kompletný workflow od emailu po databázu"""
    print("\n" + "="*60)
    print("PRÍKLAD 8: KOMPLETNÝ WORKFLOW")
    print("="*60)
    
    # 1. Email
    sample_email = """
    3. novembra 2025
    
    TESCO Bratislava
    Platba kartou 4405**9645
    
    7,18 EUR
    8,49 kg CO₂e
    """
    
    print("\n1️⃣ KROK: Parsovanie emailu...")
    transaction_data = parse_bmail_notification(sample_email)
    
    if not transaction_data:
        print("❌ Parsovanie zlyhalo")
        return
    
    print(f"   ✓ {transaction_data['merchant_name']}: {transaction_data['amount']} EUR")
    
    # 2. Finstat lookup
    print("\n2️⃣ KROK: Vyhľadávam firmu cez Finstat...")
    company_info = get_company_info(name=transaction_data['merchant_name'])
    
    if company_info:
        print(f"   ✓ Firma: {company_info.name}")
        print(f"   ✓ Činnosť: {company_info.activity}")
    else:
        print("   ⚠ Firma nenájdená v Finstat")
    
    # 3. Kategorizácia
    print("\n3️⃣ KROK: AI kategorizácia...")
    category_result = categorize_transaction(
        merchant_name=transaction_data['merchant_name'],
        amount=transaction_data['amount'],
        company_info=company_info
    )
    
    print(f"   ✓ Kategória: {category_result.category}")
    print(f"   ✓ Istota: {category_result.confidence:.0%}")
    print(f"   ✓ Zdroj: {category_result.source}")
    
    # 4. Uloženie do DB
    print("\n4️⃣ KROK: Ukladám do databázy...")
    
    try:
        category_id = db_client.get_category_id_by_name(category_result.category)
        
        merchant_id = db_client.get_or_create_merchant(
            name=transaction_data['merchant_name'],
            default_category_id=category_id
        )
        
        transaction_id = db_client.insert_transaction(
            transaction_date=datetime.fromisoformat(transaction_data['transaction_date']),
            amount=transaction_data['amount'],
            merchant_name=transaction_data['merchant_name'],
            merchant_id=merchant_id,
            category_id=category_id,
            payment_method=transaction_data.get('payment_method'),
            co2_footprint=transaction_data.get('co2_footprint'),
            ai_confidence=category_result.confidence,
            category_source=category_result.source
        )
        
        print(f"   ✓ Transakcia uložená s ID: {transaction_id}")
        
    except Exception as e:
        print(f"   ❌ Chyba pri ukladaní: {e}")
    
    print("\n✅ WORKFLOW DOKONČENÝ!")


def main():
    """Spustí všetky príklady"""
    print("\n" + "="*60)
    print("🚀 FINANCE TRACKER - PRÍKLADY POUŽITIA")
    print("="*60)
    
    examples = [
        ("Parsovanie emailu", example_1_parse_email),
        ("Finstat lookup", example_2_finstat_lookup),
        ("AI kategorizácia", example_3_ai_categorization),
        ("Uloženie transakcie", example_4_save_transaction),
        ("Získanie transakcií", example_5_get_transactions),
        ("Mesačný prehľad", example_6_monthly_summary),
        ("ChatGPT Agent", example_7_chatgpt_agent),
        ("Kompletný workflow", example_8_full_workflow),
    ]
    
    print("\nVyberte príklad:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    print(f"  {len(examples)+1}. Spustiť všetky")
    print("  0. Ukončiť")
    
    try:
        choice = int(input("\nVaša voľba: "))
        
        if choice == 0:
            print("\n👋 Dovidenia!")
            return
        elif choice == len(examples) + 1:
            # Spusti všetky
            for name, func in examples:
                func()
        elif 1 <= choice <= len(examples):
            # Spusti vybraný
            examples[choice-1][1]()
        else:
            print("\n❌ Neplatná voľba!")
            
    except ValueError:
        print("\n❌ Zadajte číslo!")
    except KeyboardInterrupt:
        print("\n\n👋 Dovidenia!")


if __name__ == "__main__":
    main()

