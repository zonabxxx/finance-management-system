"""
AI kategorizácia transakcií pomocou OpenAI
"""
from openai import OpenAI
from typing import Optional, Dict, List, Any
import logging
import json
from dataclasses import dataclass

from config import settings
from finstat_client import CompanyInfo


logger = logging.getLogger(__name__)


@dataclass
class CategoryPrediction:
    """Výsledok kategorizácie"""
    category: str
    confidence: float
    reasoning: str
    source: str  # 'AI', 'Rule', 'Finstat', 'Manual'


class AICategorizationService:
    """Služba pre AI kategorizáciu transakcií"""
    
    # Zoznam dostupných kategórií
    CATEGORIES = [
        'Potraviny',
        'Drogéria',
        'Reštaurácie a Kaviarne',
        'Donáška jedla',
        'Doprava',
        'Bývanie',
        'Zdravie',
        'Zábava',
        'Oblečenie',
        'Telefón a Internet',
        'Vzdelávanie',
        'Šport',
        'Iné'
    ]
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        
        # Pravidlová kategorizácia (rýchla, bez AI)
        self.rule_patterns = {
            'Potraviny': [
                'KAUFLAND', 'TESCO', 'LIDL', 'BILLA', 'COOP', 'Fresh',
                'KRAJ', 'POTRAVINY', 'SUPERMARKET', 'HYPERMARKET'
            ],
            'Drogéria': [
                'DR.MAX', 'DR MAX', 'DRMAX', 'ROSSMANN', 'DM DROGERIE',
                'LEKAREN', 'PHARMACY'
            ],
            'Reštaurácie a Kaviarne': [
                'RESTAURANT', 'RESTAURACIA', 'KAVIAREN', 'CAFE', 'COFFEE',
                'PUB', 'BAR', 'BISTRO', 'PIZZERIA', 'U KOCMUNDU',
                'ROXOR', 'STARBUCKS', 'MCDONALD', 'KFC'
            ],
            'Donáška jedla': [
                'WOLT', 'BOLT FOOD', 'FOODORA', 'DELIVEROO', 'DONASKA',
                'FOOD DELIVERY'
            ],
            'Doprava': [
                'SHELL', 'OMV', 'MOL', 'SLOVNAFT', 'BENZINA', 'PARKING',
                'DOPRAVNY PODNIK', 'SLOVENSKA POSTA', 'TOLL', 'DIALNICA',
                'TAXI', 'UBER', 'BOLT'
            ],
            'Bývanie': [
                'VSE', 'ZSE', 'SPP', 'ENERGIA', 'BVS', 'NAKLADY',
                'ELECTRIC', 'GAS', 'WATER', 'VODA', 'TEPLO'
            ],
            'Zdravie': [
                'POLIKLINIKA', 'NEMOCNICA', 'AMBULANCIA', 'DOVERA',
                'UNION', 'ZDRAVOTNA POISTOVNA', 'FITNES', 'GYM'
            ],
            'Zábava': [
                'KINO', 'CINEMA', 'NETFLIX', 'HBO', 'SPOTIFY', 'APPLE MUSIC',
                'GOOGLE PLAY', 'STEAM', 'PLAYSTATION', 'XBOX', 'MARKIZA'
            ],
            'Oblečenie': [
                'H&M', 'ZARA', 'C&A', 'RESERVED', 'MOHITO', 'CROPP',
                'SPORTISIMO', 'HERVIS', 'DECATHLON'
            ],
            'Telefón a Internet': [
                'ORANGE', 'TELEKOM', 'O2', 'SWAN', '4KA', 'INTERNET',
                'MOBIL'
            ],
            'Vzdelávanie': [
                'SKOLA', 'UNIVERZITA', 'KURZ', 'SKOLNE', 'EDUCATION'
            ],
            'Šport': [
                'SPORT', 'FITNESS', 'TELOCVICNA', 'STADION', 'PLAVALISKO'
            ]
        }
    
    def categorize_transaction(
        self,
        merchant_name: str,
        amount: float,
        description: Optional[str] = None,
        company_info: Optional[CompanyInfo] = None,
        iban: Optional[str] = None
    ) -> CategoryPrediction:
        """
        Kategorizuje transakciu
        
        Args:
            merchant_name: Názov obchodníka
            amount: Suma transakcie
            description: Popis transakcie
            company_info: Informácie o firme z Finstat
            iban: IBAN účtu
            
        Returns:
            CategoryPrediction s kategóriou a istotou
        """
        # 1. Skús pravidlovú kategorizáciu (najrýchlejšie)
        rule_category = self._categorize_by_rules(merchant_name)
        if rule_category:
            return CategoryPrediction(
                category=rule_category,
                confidence=0.95,
                reasoning=f"Pravidlová zhoda pre '{merchant_name}'",
                source='Rule'
            )
        
        # 2. Skús Finstat kategóriu
        if company_info and company_info.suggested_category:
            return CategoryPrediction(
                category=company_info.suggested_category,
                confidence=0.85,
                reasoning=f"Kategorizované na základe činnosti: {company_info.activity}",
                source='Finstat'
            )
        
        # 3. Použi AI kategorizáciu
        return self._categorize_with_ai(
            merchant_name=merchant_name,
            amount=amount,
            description=description,
            company_activity=company_info.activity if company_info else None
        )
    
    def _categorize_by_rules(self, merchant_name: str) -> Optional[str]:
        """
        Kategorizuje podľa pravidiel
        
        Args:
            merchant_name: Názov obchodníka
            
        Returns:
            Názov kategórie alebo None
        """
        merchant_upper = merchant_name.upper()
        
        for category, patterns in self.rule_patterns.items():
            for pattern in patterns:
                if pattern in merchant_upper:
                    logger.info(f"Pravidlová kategorizácia: '{merchant_name}' -> {category}")
                    return category
        
        return None
    
    def _categorize_with_ai(
        self,
        merchant_name: str,
        amount: float,
        description: Optional[str] = None,
        company_activity: Optional[str] = None
    ) -> CategoryPrediction:
        """
        Kategorizuje pomocou OpenAI API
        
        Args:
            merchant_name: Názov obchodníka
            amount: Suma transakcie
            description: Popis transakcie
            company_activity: Činnosť firmy z Finstat
            
        Returns:
            CategoryPrediction
        """
        try:
            # Priprav kontext pre AI
            context_parts = [f"Názov obchodníka: {merchant_name}"]
            
            if amount:
                context_parts.append(f"Suma: {amount:.2f} EUR")
            
            if description:
                context_parts.append(f"Popis: {description}")
            
            if company_activity:
                context_parts.append(f"Činnosť firmy: {company_activity}")
            
            context = "\n".join(context_parts)
            
            # Priprav prompt
            prompt = f"""Analyzuj túto transakciu a priraď ju do jednej z nasledujúcich kategórií:

{', '.join(self.CATEGORIES)}

Transakcia:
{context}

Vráť odpoveď vo formáte JSON s týmito poľami:
- category: názov kategórie (presne ako je uvedený v zozname)
- confidence: číslo medzi 0 a 1 vyjadrujúce istotu (napr. 0.9)
- reasoning: krátke odôvodnenie (1-2 vety)

Príklad odpovede:
{{
  "category": "Potraviny",
  "confidence": 0.95,
  "reasoning": "KAUFLAND je známy supermarket predávajúci potraviny."
}}
"""
            
            # Volaj OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Si AI asistent na kategorizáciu bankových transakcií. Odpovedáš vždy vo formáte JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Parsuj odpoveď
            result = json.loads(response.choices[0].message.content)
            
            category = result.get('category', 'Iné')
            confidence = float(result.get('confidence', 0.5))
            reasoning = result.get('reasoning', 'AI kategorizácia')
            
            # Validuj kategóriu
            if category not in self.CATEGORIES:
                category = 'Iné'
                confidence = 0.3
            
            logger.info(f"AI kategorizácia: '{merchant_name}' -> {category} ({confidence:.2f})")
            
            return CategoryPrediction(
                category=category,
                confidence=confidence,
                reasoning=reasoning,
                source='AI'
            )
            
        except Exception as e:
            logger.error(f"Chyba pri AI kategorizácii: {e}")
            return CategoryPrediction(
                category='Iné',
                confidence=0.0,
                reasoning=f"Chyba pri kategorizácii: {str(e)}",
                source='AI'
            )
    
    def batch_categorize(
        self,
        transactions: List[Dict[str, Any]]
    ) -> List[CategoryPrediction]:
        """
        Kategorizuje viacero transakcií naraz
        
        Args:
            transactions: Zoznam transakcií (dict s merchant_name, amount, atď.)
            
        Returns:
            Zoznam CategoryPrediction
        """
        results = []
        
        for transaction in transactions:
            prediction = self.categorize_transaction(
                merchant_name=transaction.get('merchant_name', ''),
                amount=transaction.get('amount', 0),
                description=transaction.get('description'),
                company_info=transaction.get('company_info'),
                iban=transaction.get('iban')
            )
            results.append(prediction)
        
        return results


# Singleton inštancia
ai_categorization_service = AICategorizationService()


def categorize_transaction(
    merchant_name: str,
    amount: float,
    description: Optional[str] = None,
    company_info: Optional[CompanyInfo] = None,
    iban: Optional[str] = None
) -> CategoryPrediction:
    """
    Hlavná funkcia pre kategorizáciu transakcie
    
    Args:
        merchant_name: Názov obchodníka
        amount: Suma transakcie
        description: Popis transakcie
        company_info: Informácie o firme z Finstat
        iban: IBAN účtu
        
    Returns:
        CategoryPrediction
    """
    return ai_categorization_service.categorize_transaction(
        merchant_name=merchant_name,
        amount=amount,
        description=description,
        company_info=company_info,
        iban=iban
    )

