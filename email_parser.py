"""
Email parser pre B-mail notifikácie o pohyboch na účte
"""
import re
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
import html2text
from bs4 import BeautifulSoup


@dataclass
class TransactionData:
    """Dáta z transakcie parsované z emailu"""
    merchant_name: str
    amount: float
    currency: str
    transaction_date: datetime
    account_number: Optional[str] = None
    iban: Optional[str] = None
    payment_method: Optional[str] = None
    co2_footprint: Optional[float] = None
    description: Optional[str] = None
    variable_symbol: Optional[str] = None
    constant_symbol: Optional[str] = None
    specific_symbol: Optional[str] = None


class EmailParser:
    """Parser pre B-mail notifikácie"""
    
    def __init__(self):
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        
    def parse_email(self, email_body: str, is_html: bool = True) -> Optional[TransactionData]:
        """
        Parsuje email telo a extrahuje transakčné dáta
        
        Args:
            email_body: Telo emailu (HTML alebo plain text)
            is_html: Či je email v HTML formáte
            
        Returns:
            TransactionData alebo None ak sa nepodarilo parsovať
        """
        if is_html:
            text = self._html_to_text(email_body)
            soup = BeautifulSoup(email_body, 'html.parser')
        else:
            text = email_body
            soup = None
            
        # Extrahuj základné informácie
        merchant_name = self._extract_merchant_name(text, soup)
        amount = self._extract_amount(text)
        currency = self._extract_currency(text)
        transaction_date = self._extract_date(text)
        account_number = self._extract_account_number(text)
        iban = self._extract_iban(text)
        payment_method = self._extract_payment_method(text)
        co2_footprint = self._extract_co2(text)
        
        # Extrahuj symboly
        variable_symbol = self._extract_symbol(text, 'variabilný')
        constant_symbol = self._extract_symbol(text, 'konštantný')
        specific_symbol = self._extract_symbol(text, 'špecifický')
        
        if not merchant_name or amount is None:
            return None
            
        return TransactionData(
            merchant_name=merchant_name,
            amount=amount,
            currency=currency or 'EUR',
            transaction_date=transaction_date or datetime.now(),
            account_number=account_number,
            iban=iban,
            payment_method=payment_method,
            co2_footprint=co2_footprint,
            variable_symbol=variable_symbol,
            constant_symbol=constant_symbol,
            specific_symbol=specific_symbol
        )
    
    def _html_to_text(self, html: str) -> str:
        """Konvertuje HTML na plain text"""
        return self.html_converter.handle(html)
    
    def _extract_merchant_name(self, text: str, soup: Optional[BeautifulSoup]) -> Optional[str]:
        """
        Extrahuje názov obchodníka
        
        Patterns:
        - "ROXOR S R O"
        - "Dr.Max 039, PO Levocska"
        - "KAUFLAND 1120, PO, LEVO"
        - "U Kocmundu Biely kríz"
        """
        # Hľadaj pattern s názvom obchodníka
        patterns = [
            r'(?:^|\n)([A-ZČĎŽŠŤŇ][A-ZČĎŽŠŤŇa-zčďžšťň\s\.,&\-]+?)(?:\s+\d+,?\s*EUR|\n|$)',
            r'Platba kartou[:\s]+([^\n]+)',
            r'Obchodník[:\s]+([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Vyčisti názov
                name = re.sub(r'\s+', ' ', name)
                name = name.rstrip(',')
                return name
                
        return None
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """
        Extrahuje sumu
        
        Patterns:
        - "23,00 EUR"
        - "12,48 EUR"
        - "0,70 EUR"
        """
        pattern = r'(\d+,\d{2})\s*EUR'
        match = re.search(pattern, text)
        if match:
            amount_str = match.group(1).replace(',', '.')
            return float(amount_str)
        return None
    
    def _extract_currency(self, text: str) -> Optional[str]:
        """Extrahuje menu"""
        match = re.search(r'(\d+,\d{2})\s*([A-Z]{3})', text)
        if match:
            return match.group(2)
        return 'EUR'
    
    def _extract_date(self, text: str) -> Optional[datetime]:
        """
        Extrahuje dátum transakcie
        
        Patterns:
        - "3. novembra 2025"
        - "03.11.2025"
        """
        # Slovenské mesiace
        months_sk = {
            'januára': 1, 'februára': 2, 'marca': 3, 'apríla': 4,
            'mája': 5, 'júna': 6, 'júla': 7, 'augusta': 8,
            'septembra': 9, 'októbra': 10, 'novembra': 11, 'decembra': 12
        }
        
        # Pattern: "3. novembra 2025"
        pattern = r'(\d{1,2})\.\s*(\w+)\s+(\d{4})'
        match = re.search(pattern, text)
        if match:
            day = int(match.group(1))
            month_name = match.group(2).lower()
            year = int(match.group(3))
            
            if month_name in months_sk:
                month = months_sk[month_name]
                return datetime(year, month, day)
        
        # Pattern: "03.11.2025"
        pattern = r'(\d{2})\.(\d{2})\.(\d{4})'
        match = re.search(pattern, text)
        if match:
            day = int(match.group(1))
            month = int(match.group(2))
            year = int(match.group(3))
            return datetime(year, month, day)
            
        return None
    
    def _extract_account_number(self, text: str) -> Optional[str]:
        """
        Extrahuje číslo účtu
        
        Pattern: "4405**9645"
        """
        pattern = r'(\d{4}\*+\d{4})'
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        return None
    
    def _extract_iban(self, text: str) -> Optional[str]:
        """
        Extrahuje IBAN
        
        Pattern: SK89 1200 0000 1987 4263 7541
        """
        pattern = r'(SK\d{2}\s?(?:\d{4}\s?){5})'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            iban = match.group(1).replace(' ', '')
            return iban.upper()
        return None
    
    def _extract_payment_method(self, text: str) -> Optional[str]:
        """Určí spôsob platby"""
        text_lower = text.lower()
        
        if 'platba kartou' in text_lower or 'kart' in text_lower:
            return 'Card'
        elif 'prevod' in text_lower or 'transakcia' in text_lower:
            return 'Transfer'
        elif 'hotovosť' in text_lower:
            return 'Cash'
        elif 'inkaso' in text_lower:
            return 'Direct Debit'
            
        return None
    
    def _extract_co2(self, text: str) -> Optional[float]:
        """
        Extrahuje CO2 stopu
        
        Pattern: "27,21 kg CO2e"
        """
        pattern = r'(\d+,\d{2})\s*kg\s*CO2'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            co2_str = match.group(1).replace(',', '.')
            return float(co2_str)
        return None
    
    def _extract_symbol(self, text: str, symbol_type: str) -> Optional[str]:
        """
        Extrahuje variabilný/konštantný/špecifický symbol
        
        Args:
            symbol_type: 'variabilný', 'konštantný', alebo 'špecifický'
        """
        pattern = f'{symbol_type}[\\s:]+([\\d]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None


def parse_bmail_notification(email_html: str) -> Optional[Dict[str, Any]]:
    """
    Hlavná funkcia pre parsovanie B-mail notifikácie
    
    Args:
        email_html: HTML telo emailu
        
    Returns:
        Dictionary s transakčnými dátami alebo None
    """
    parser = EmailParser()
    transaction = parser.parse_email(email_html, is_html=True)
    
    if not transaction:
        return None
        
    return {
        'merchant_name': transaction.merchant_name,
        'amount': transaction.amount,
        'currency': transaction.currency,
        'transaction_date': transaction.transaction_date.isoformat(),
        'account_number': transaction.account_number,
        'iban': transaction.iban,
        'payment_method': transaction.payment_method,
        'co2_footprint': transaction.co2_footprint,
        'variable_symbol': transaction.variable_symbol,
        'constant_symbol': transaction.constant_symbol,
        'specific_symbol': transaction.specific_symbol,
    }

