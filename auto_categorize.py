#!/usr/bin/env python3
"""
Automatická kategorizácia transakcií pomocou AI a pravidiel
"""

import os
import subprocess
import json
import re
from typing import Dict, Optional, List
from datetime import datetime
from dotenv import load_dotenv
import openai

load_dotenv()


class AutoCategorizer:
    """Automatická kategorizácia transakcií"""
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
        
        # Načítame kategórie z databázy
        self.categories = self._load_categories()
        
        # Pravidlá pre obchodníkov (learning system)
        self.merchant_rules = self._load_merchant_rules()
    
    def _load_categories(self) -> List[Dict]:
        """Načítanie kategórií z databázy"""
        try:
            result = subprocess.run(
                ['turso', 'db', 'shell', 'financa-sprava', 
                 'SELECT CategoryID, Name, Icon FROM Categories;'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                categories = []
                
                # Preskočíme header
                if len(lines) > 1:
                    for line in lines[1:]:
                        parts = line.split()
                        if len(parts) >= 2:
                            categories.append({
                                'id': parts[0],
                                'name': ' '.join(parts[1:-1]) if len(parts) > 2 else parts[1],
                                'icon': parts[-1] if len(parts) > 2 else ''
                            })
                
                return categories
            
            return []
            
        except Exception as e:
            print(f"⚠️  Chyba pri načítaní kategórií: {e}")
            return []
    
    def _load_merchant_rules(self) -> Dict:
        """Načítanie pravidiel pre obchodníkov z databázy"""
        try:
            # Načítame transakcie, ktoré už majú manuálne priradenú kategóriu
            result = subprocess.run(
                ['turso', 'db', 'shell', 'financa-sprava', 
                 '''SELECT t.MerchantName, c.CategoryID, c.Name, COUNT(*) as cnt 
                    FROM Transactions t 
                    JOIN Categories c ON t.CategoryID = c.CategoryID 
                    WHERE t.CategorySource = 'Manual' 
                    GROUP BY t.MerchantName, c.CategoryID, c.Name;'''],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            rules = {}
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    for line in lines[1:]:
                        parts = line.split()
                        if len(parts) >= 3:
                            merchant = parts[0]
                            category_id = parts[1]
                            rules[merchant] = int(category_id)
            
            return rules
            
        except Exception as e:
            print(f"⚠️  Chyba pri načítaní pravidiel: {e}")
            return {}
    
    def categorize_by_rules(self, merchant: str) -> Optional[int]:
        """Kategorizácia podľa naučených pravidiel"""
        # Presná zhoda
        if merchant in self.merchant_rules:
            return self.merchant_rules[merchant]
        
        # Čiastočná zhoda (napr. "TESCO" v "TESCO STORES")
        for known_merchant, category_id in self.merchant_rules.items():
            if known_merchant.upper() in merchant.upper() or merchant.upper() in known_merchant.upper():
                return category_id
        
        return None
    
    def categorize_by_keywords(self, merchant: str, description: str) -> Optional[int]:
        """Kategorizácia podľa kľúčových slov"""
        merchant_upper = merchant.upper()
        desc_upper = description.upper()
        combined = f"{merchant_upper} {desc_upper}"
        
        # Slovník: kľúčové slová → názov kategórie
        keywords_map = {
            'Doprava': ['BOLT', 'UBER', 'HOPIN', 'TAXI', 'MHD', 'PARKING'],
            'Potraviny': ['TESCO', 'BILLA', 'KAUFLAND', 'LIDL', 'COOP', 'JEDNOTA'],
            'Reštaurácie': ['MCDONALD', 'KFC', 'SUBWAY', 'PIZZA', 'RESTAURANT', 'BISTRO'],
            'Káva': ['STARBUCKS', 'COFFEE', 'CAFE', 'COSTA'],
            'Drogéria': ['DM', 'ROSSMANN', 'TETA'],
            'Pohonné hmoty': ['SHELL', 'OMV', 'SLOVNAFT', 'BENZIN', 'NAFTA', 'MOL']
        }
        
        # Hľadáme kategóriu podľa kľúčových slov
        for category_name, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword in combined:
                    # Nájdeme CategoryID podľa názvu
                    for cat in self.categories:
                        if category_name.upper() in cat['name'].upper():
                            return int(cat['id'])
        
        return None
    
    def categorize_by_ai(self, merchant: str, description: str, amount: float) -> Optional[Dict]:
        """Kategorizácia pomocou OpenAI"""
        if not self.openai_api_key or 'your-' in self.openai_api_key:
            return None
        
        try:
            # Pripravíme zoznam kategórií pre AI
            categories_text = "\n".join([
                f"- {cat['id']}: {cat['icon']} {cat['name']}" 
                for cat in self.categories
            ])
            
            prompt = f"""Analyzuj túto transakciu a priraď jej kategóriu.

**Transakcia:**
- Obchodník: {merchant}
- Popis: {description}
- Suma: {amount} EUR

**Dostupné kategórie:**
{categories_text}

Odpoveď vo formáte JSON:
{{
    "category_id": číslo,
    "confidence": číslo od 0 do 1,
    "reason": "krátke vysvetlenie"
}}

Pravidlá:
- BOLT, Uber, Hopin → Doprava
- TESCO, BILLA, Kaufland, Lidl → Potraviny
- McDonald's, KFC, Subway → Reštaurácie
- Starbucks, Coffee → Káva
- DM, Rossmann → Drogéria
- Shell, OMV, Slovnaft → Pohonné hmoty"""

            response = openai.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "Si expert na kategorizáciu finančných transakcií na Slovensku."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON z odpovede
            # Niekedy AI vráti ```json ... ```, tak to očistíme
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()
            
            result = json.loads(result_text)
            
            return {
                'category_id': int(result.get('category_id')),
                'confidence': float(result.get('confidence', 0)),
                'reason': result.get('reason', '')
            }
            
        except Exception as e:
            print(f"⚠️  AI kategorizácia zlyhala: {e}")
            return None
    
    def categorize_transaction(self, transaction_id: int, merchant: str, 
                              description: str, amount: float) -> bool:
        """
        Automatická kategorizácia transakcie
        
        Priorita:
        1. Pravidlá (naučené z manuálnych priradení)
        2. Kľúčové slová
        3. AI kategorizácia
        4. Default kategória
        """
        category_id = None
        source = None
        confidence = 0
        
        # 1. Skúsime pravidlá
        category_id = self.categorize_by_rules(merchant)
        if category_id:
            source = 'Rule'
            confidence = 1.0
            print(f"  📋 Pravidlo: Kategória {category_id}")
        
        # 2. Skúsime kľúčové slová
        if not category_id:
            category_id = self.categorize_by_keywords(merchant, description)
            if category_id:
                source = 'Keyword'
                confidence = 0.9
                print(f"  🔑 Kľúčové slovo: Kategória {category_id}")
        
        # 3. Skúsime AI
        if not category_id and self.openai_api_key:
            ai_result = self.categorize_by_ai(merchant, description, amount)
            if ai_result and ai_result['confidence'] > 0.6:
                category_id = ai_result['category_id']
                source = 'AI'
                confidence = ai_result['confidence']
                print(f"  🤖 AI: Kategória {category_id} ({ai_result['reason']}, {confidence:.0%})")
        
        # 4. Uložíme kategóriu
        if category_id:
            try:
                query = f"""
                UPDATE Transactions 
                SET CategoryID = {category_id},
                    CategorySource = '{source}',
                    UpdatedAt = '{datetime.now().isoformat()}'
                WHERE TransactionID = {transaction_id};
                """
                
                result = subprocess.run(
                    ['turso', 'db', 'shell', 'financa-sprava', query],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    print(f"  ✅ Kategorizované!")
                    return True
                else:
                    print(f"  ❌ Chyba pri ukladaní: {result.stderr}")
                    return False
                    
            except Exception as e:
                print(f"  ❌ Chyba: {e}")
                return False
        else:
            print(f"  ⚠️  Nepodarilo sa určiť kategóriu")
            return False


def categorize_uncategorized_transactions():
    """Kategorizácia všetkých nekategorizovaných transakcií"""
    print("🤖 Automatická kategorizácia transakcií")
    print("=" * 60)
    
    categorizer = AutoCategorizer()
    
    if not categorizer.categories:
        print("❌ Žiadne kategórie v databáze!")
        return
    
    print(f"📋 Načítaných {len(categorizer.categories)} kategórií")
    print(f"📖 Načítaných {len(categorizer.merchant_rules)} pravidiel\n")
    
    # Načítame nekategorizované transakcie
    try:
        result = subprocess.run(
            ['turso', 'db', 'shell', 'financa-sprava',
             'SELECT TransactionID, MerchantName, Description, Amount FROM Transactions WHERE CategoryID IS NULL;'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print("❌ Chyba pri načítaní transakcií")
            return
        
        lines = result.stdout.strip().split('\n')
        
        if len(lines) <= 1:
            print("✅ Všetky transakcie sú už kategorizované!")
            return
        
        transactions = []
        for line in lines[1:]:
            # Split by whitespace, limit to first 4 columns
            # Format: TransactionID MerchantName Description Amount
            parts = line.strip().split(maxsplit=1)
            if len(parts) >= 2:
                trans_id = int(parts[0])
                rest = parts[1]
                
                # Nájdeme posledné číslo (Amount) v riadku
                amount_match = None
                for match in re.finditer(r'-?\d+\.?\d*\s*$', rest):
                    amount_match = match
                
                if amount_match:
                    amount = float(amount_match.group().strip())
                    before_amount = rest[:amount_match.start()].strip()
                    
                    # Merchant je prvé slovo, Description je zvyšok
                    parts2 = before_amount.split(maxsplit=1)
                    merchant = parts2[0] if len(parts2) > 0 else 'Unknown'
                    description = parts2[1] if len(parts2) > 1 else ''
                    
                    transactions.append({
                        'id': trans_id,
                        'merchant': merchant,
                        'description': description,
                        'amount': amount
                    })
        
        print(f"🔍 Našiel som {len(transactions)} nekategorizovaných transakcií\n")
        
        success_count = 0
        for i, transaction in enumerate(transactions, 1):
            print(f"[{i}/{len(transactions)}] {transaction['merchant']} ({transaction['amount']} EUR)")
            
            if categorizer.categorize_transaction(
                transaction['id'],
                transaction['merchant'],
                transaction['description'],
                transaction['amount']
            ):
                success_count += 1
            
            print()
        
        print("=" * 60)
        print(f"✅ Kategorizovaných: {success_count}/{len(transactions)}")
        
    except Exception as e:
        print(f"❌ Chyba: {e}")


if __name__ == "__main__":
    categorize_uncategorized_transactions()

