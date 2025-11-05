#!/usr/bin/env python3
"""
Smart Categorizer - Učiaci sa systém kategorizácie s AI fallback
"""

import os
import re
from typing import Optional, Dict, List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class SmartCategorizer:
    """Inteligentný kategoriz átor s učením a AI fallback"""
    
    def __init__(self, turso_query_func):
        """
        Args:
            turso_query_func: Funkcia na vykonávanie SQL queries
        """
        self.turso_query = turso_query_func
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.use_ai = bool(self.openai_api_key)
        
    def categorize(self, merchant: str, description: str, amount: float, 
                   counterparty_purpose: str = '', recipient_info: str = '') -> Optional[int]:
        """
        Hlavná kategorizačná funkcia
        
        Args:
            merchant: Názov obchodníka
            description: Popis transakcie
            amount: Suma (+ príjem, - výdavok)
            counterparty_purpose: Účel protistrany (napr. "Mestska cast Bratislava - Petrzalka")
            recipient_info: Informácia pre príjemcu (napr. "Martinkovychova Livia, 1. trieda")
            
        Returns:
            CategoryID alebo None
        """
        # 1. Príjmy → automaticky kategória "Príjem"
        if amount > 0:
            return self._get_or_create_income_category()
        
        # 2. Hľadaj v naučených pravidlách
        category_id = self._find_by_rules(merchant)
        if category_id:
            return category_id
        
        # 3. Fallback na OpenAI (ak je enabled)
        if self.use_ai:
            category_id = self._categorize_with_ai(merchant, description, amount, 
                                                   counterparty_purpose, recipient_info)
            if category_id:
                # Ulož ako nové pravidlo
                self._learn_rule(merchant, category_id, 'AI', 0.8)
                return category_id
        
        # 4. Žiadna kategória nenájdená
        return None
    
    def _get_or_create_income_category(self) -> Optional[int]:
        """Získaj alebo vytvor kategóriu Príjem"""
        try:
            # Hľadaj existujúcu
            query = "SELECT CategoryID FROM Categories WHERE Name IN ('Príjem', 'Príjmy') LIMIT 1;"
            result = self.turso_query(query)
            
            if result and 'rows' in result and len(result['rows']) > 0:
                return int(result['rows'][0][0]['value'])
            
            # Vytvor novú
            create_query = """
            INSERT INTO Categories (Name, Icon, Color, CreatedAt)
            VALUES ('Príjem', '💰', '#10b981', datetime('now'));
            """
            self.turso_query(create_query)
            
            # Získaj ID
            result = self.turso_query("SELECT CategoryID FROM Categories WHERE Name = 'Príjem' LIMIT 1;")
            if result and 'rows' in result and len(result['rows']) > 0:
                return int(result['rows'][0][0]['value'])
        except Exception as e:
            print(f"Error getting income category: {e}")
        
        return None
    
    def _find_by_rules(self, merchant: str) -> Optional[int]:
        """Hľadaj kategóriu v naučených pravidlách"""
        try:
            merchant_clean = merchant.strip().upper()
            
            # Hľadaj exact match
            query = f"""
            SELECT CategoryID, RuleID FROM MerchantRules 
            WHERE UPPER(MerchantPattern) = '{merchant_clean}' 
            AND MatchType = 'exact'
            ORDER BY UsageCount DESC, Confidence DESC
            LIMIT 1;
            """
            result = self.turso_query(query)
            
            if result and 'rows' in result and len(result['rows']) > 0:
                category_id = int(result['rows'][0][0]['value'])
                rule_id = int(result['rows'][0][1]['value'])
                self._update_rule_usage(rule_id)
                print(f"   📚 Rule match (exact): {merchant} → CategoryID={category_id}")
                return category_id
            
            # Hľadaj contains match
            query = f"""
            SELECT CategoryID, RuleID, MerchantPattern FROM MerchantRules 
            WHERE MatchType = 'contains'
            ORDER BY LENGTH(MerchantPattern) DESC, UsageCount DESC;
            """
            result = self.turso_query(query)
            
            if result and 'rows' in result:
                for row in result['rows']:
                    pattern = row[2]['value'].upper()
                    if pattern in merchant_clean:
                        category_id = int(row[0]['value'])
                        rule_id = int(row[1]['value'])
                        self._update_rule_usage(rule_id)
                        print(f"   📚 Rule match (contains '{pattern}'): {merchant} → CategoryID={category_id}")
                        return category_id
        
        except Exception as e:
            print(f"Error finding rules: {e}")
        
        return None
    
    def _update_rule_usage(self, rule_id: int):
        """Aktualizuj počet použití pravidla"""
        try:
            query = f"""
            UPDATE MerchantRules 
            SET UsageCount = UsageCount + 1,
                LastUsed = datetime('now')
            WHERE RuleID = {rule_id};
            """
            self.turso_query(query)
        except Exception as e:
            print(f"Error updating rule usage: {e}")
    
    def _categorize_with_ai(self, merchant: str, description: str, amount: float,
                           counterparty_purpose: str = '', recipient_info: str = '') -> Optional[int]:
        """Kategorizuj pomocou OpenAI"""
        try:
            import openai
            openai.api_key = self.openai_api_key
            
            # Načítaj dostupné kategórie
            categories_query = "SELECT CategoryID, Name, Icon FROM Categories WHERE Name != 'Príjem' AND Name != 'Nezaradené';"
            categories_result = self.turso_query(categories_query)
            
            if not categories_result or 'rows' not in categories_result:
                return None
            
            categories_list = []
            categories_map = {}
            for row in categories_result['rows']:
                cat_id = int(row[0]['value'])
                cat_name = row[1]['value']
                cat_icon = row[2]['value'] if len(row) > 2 and row[2].get('value') else ''
                categories_list.append(f"{cat_icon} {cat_name}")
                categories_map[cat_name.lower()] = cat_id
            
            # Zostav AI prompt s extra kontextom
            transaction_info = f"""Transakcia:
- Obchodník: {merchant}
- Popis: {description}
- Suma: {amount} EUR (výdavok)"""

            # Pridaj extra kontextové polia ak existujú
            if counterparty_purpose:
                transaction_info += f"\n- Účel protistrany: {counterparty_purpose}"
            if recipient_info:
                transaction_info += f"\n- Info pre príjemcu: {recipient_info}"
            
            # OpenAI prompt
            prompt = f"""Analyzuj túto transakciu a vyber najpravdepodobnejšiu kategóriu.

{transaction_info}

Dostupné kategórie:
{chr(10).join(f"- {cat}" for cat in categories_list)}

DÔLEŽITÉ:
- "Účel protistrany" často obsahuje kľúčové info o type platby
- Napr. "Mestska cast..." → Dane/Verejné služby
- "Škola", "trieda" → Vzdelávanie/Školné
- Využi všetky dostupné informácie!

Odpoveď PRESNE v tomto formáte (iba názov kategórie, bez ikony):
Kategória: [názov]"""

            response = openai.ChatCompletion.create(
                model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                messages=[
                    {"role": "system", "content": "Si expert na kategorizáciu finančných transakcií. Využívaš všetky dostupné informácie vrátane účelu protistrany a info pre príjemcu. Odpovedaj krátko a presne."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.3
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Parsuj odpoveď
            match = re.search(r'Kategória:\s*(.+)', ai_response, re.IGNORECASE)
            if match:
                category_name = match.group(1).strip().lower()
                
                # Hľadaj v mape
                for cat_name_lower, cat_id in categories_map.items():
                    if cat_name_lower in category_name or category_name in cat_name_lower:
                        print(f"   🤖 AI categorized: {merchant} → {cat_name_lower} (CategoryID={cat_id})")
                        return cat_id
        
        except Exception as e:
            print(f"AI categorization error: {e}")
        
        return None
    
    def _learn_rule(self, merchant: str, category_id: int, source: str = 'Manual', confidence: float = 1.0):
        """Ulož nové pravidlo kategorizácie"""
        try:
            merchant_clean = merchant.strip()
            
            # Skontroluj či už pravidlo neexistuje
            check_query = f"""
            SELECT RuleID FROM MerchantRules 
            WHERE UPPER(MerchantPattern) = '{merchant_clean.upper()}' 
            AND CategoryID = {category_id}
            LIMIT 1;
            """
            result = self.turso_query(check_query)
            
            if result and 'rows' in result and len(result['rows']) > 0:
                # Už existuje, aktualizuj confidence
                rule_id = int(result['rows'][0][0]['value'])
                update_query = f"""
                UPDATE MerchantRules 
                SET Confidence = {confidence},
                    LearnedFrom = '{source}',
                    UsageCount = UsageCount + 1
                WHERE RuleID = {rule_id};
                """
                self.turso_query(update_query)
                print(f"   📝 Updated rule: {merchant_clean} → CategoryID={category_id}")
            else:
                # Vytvor nové pravidlo
                insert_query = f"""
                INSERT INTO MerchantRules 
                (MerchantPattern, CategoryID, MatchType, Confidence, LearnedFrom, UsageCount, CreatedAt)
                VALUES 
                ('{merchant_clean}', {category_id}, 'exact', {confidence}, '{source}', 1, datetime('now'));
                """
                self.turso_query(insert_query)
                print(f"   ✨ Learned new rule: {merchant_clean} → CategoryID={category_id} (from {source})")
        
        except Exception as e:
            print(f"Error learning rule: {e}")
    
    def learn_from_manual_assignment(self, transaction_id: int, category_id: int):
        """
        Nauč sa z manuálneho priradenia kategórie
        Volá sa keď user manuálne zmení kategóriu v UI
        """
        try:
            # Získaj merchant z transakcie
            query = f"""
            SELECT MerchantName, Amount FROM Transactions 
            WHERE TransactionID = {transaction_id};
            """
            result = self.turso_query(query)
            
            if result and 'rows' in result and len(result['rows']) > 0:
                merchant = result['rows'][0][0]['value']
                amount = float(result['rows'][0][1]['value'])
                
                # Príjmy sa neučia (sú automatické)
                if amount > 0:
                    return
                
                # Ulož pravidlo
                self._learn_rule(merchant, category_id, 'Manual', 1.0)
        
        except Exception as e:
            print(f"Error learning from manual assignment: {e}")

