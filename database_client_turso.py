"""
Turso Database klient pre prácu s transakciami
"""
from libsql_client import create_client_sync
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import json

from config import settings


logger = logging.getLogger(__name__)


class DatabaseClient:
    """Klient pre prácu s Turso Database (LibSQL)"""
    
    def __init__(self, database_url: str = None, auth_token: str = None):
        self.database_url = database_url or settings.turso_database_url
        self.auth_token = auth_token or settings.turso_auth_token
        self._client = None
    
    def _get_client(self):
        """Vytvorí alebo vráti existujúci Turso klient"""
        if self._client is None:
            self._client = create_client_sync(
                url=self.database_url,
                auth_token=self.auth_token
            )
        return self._client
    
    def execute(self, query: str, params: tuple = ()):
        """
        Vykoná SQL query s parametrami
        
        Args:
            query: SQL query string
            params: Tuple parametrov
            
        Returns:
            Result set
        """
        client = self._get_client()
        return client.execute(query, params)
    
    def insert_transaction(
        self,
        transaction_date: datetime,
        amount: float,
        merchant_name: str,
        category_id: Optional[int] = None,
        merchant_id: Optional[int] = None,
        account_number: Optional[str] = None,
        iban: Optional[str] = None,
        description: Optional[str] = None,
        variable_symbol: Optional[str] = None,
        constant_symbol: Optional[str] = None,
        specific_symbol: Optional[str] = None,
        transaction_type: str = 'Debit',
        payment_method: Optional[str] = None,
        co2_footprint: Optional[float] = None,
        raw_email_data: Optional[str] = None,
        ai_confidence: Optional[float] = None,
        category_source: Optional[str] = None,
        currency: str = 'EUR'
    ) -> int:
        """
        Vloží novú transakciu do databázy
        
        Returns:
            ID vloženej transakcie
        """
        try:
            query = """
                INSERT INTO Transactions (
                    TransactionDate, Amount, Currency, MerchantID, MerchantName,
                    AccountNumber, IBAN, CategoryID, Description,
                    VariableSymbol, ConstantSymbol, SpecificSymbol,
                    TransactionType, PaymentMethod, CO2Footprint,
                    RawEmailData, AIConfidence, CategorySource
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            result = self.execute(query, (
                transaction_date.isoformat(),
                amount,
                currency,
                merchant_id,
                merchant_name,
                account_number,
                iban,
                category_id,
                description,
                variable_symbol,
                constant_symbol,
                specific_symbol,
                transaction_type,
                payment_method,
                co2_footprint,
                raw_email_data,
                ai_confidence,
                category_source
            ))
            
            # Get last inserted ID
            last_id_result = self.execute("SELECT last_insert_rowid()")
            transaction_id = last_id_result.rows[0][0]
            
            logger.info(f"Vložená transakcia ID: {transaction_id}")
            return transaction_id
            
        except Exception as e:
            logger.error(f"Chyba pri vkladaní transakcie: {e}")
            raise
    
    def get_or_create_merchant(
        self,
        name: str,
        iban: Optional[str] = None,
        account_number: Optional[str] = None,
        ico: Optional[str] = None,
        finstat_data: Optional[Dict] = None,
        default_category_id: Optional[int] = None
    ) -> int:
        """
        Získa alebo vytvorí obchodníka v databáze
        
        Returns:
            ID obchodníka
        """
        try:
            # Skús najprv nájsť existujúceho
            if iban:
                result = self.execute(
                    "SELECT MerchantID FROM Merchants WHERE IBAN = ?",
                    (iban,)
                )
                if result.rows:
                    merchant_id = result.rows[0][0]
                    logger.info(f"Nájdený existujúci obchodník ID: {merchant_id}")
                    return merchant_id
            elif ico:
                result = self.execute(
                    "SELECT MerchantID FROM Merchants WHERE ICO = ?",
                    (ico,)
                )
                if result.rows:
                    merchant_id = result.rows[0][0]
                    logger.info(f"Nájdený existujúci obchodník ID: {merchant_id}")
                    return merchant_id
            else:
                result = self.execute(
                    "SELECT MerchantID FROM Merchants WHERE Name = ?",
                    (name,)
                )
                if result.rows:
                    merchant_id = result.rows[0][0]
                    logger.info(f"Nájdený existujúci obchodník ID: {merchant_id}")
                    return merchant_id
            
            # Vytvor nového
            finstat_json = json.dumps(finstat_data) if finstat_data else None
            
            self.execute("""
                INSERT INTO Merchants (
                    Name, IBAN, AccountNumber, ICO, FinstatData, DefaultCategoryID
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, iban, account_number, ico, finstat_json, default_category_id))
            
            # Get last inserted ID
            result = self.execute("SELECT last_insert_rowid()")
            merchant_id = result.rows[0][0]
            
            logger.info(f"Vytvorený nový obchodník ID: {merchant_id}")
            return merchant_id
            
        except Exception as e:
            logger.error(f"Chyba pri práci s obchodníkom: {e}")
            raise
    
    def get_category_id_by_name(self, category_name: str) -> Optional[int]:
        """Získa ID kategórie podľa názvu"""
        try:
            result = self.execute(
                "SELECT CategoryID FROM Categories WHERE Name = ?",
                (category_name,)
            )
            if result.rows:
                return result.rows[0][0]
            return None
        except Exception as e:
            logger.error(f"Chyba pri získavaní kategórie: {e}")
            return None
    
    def get_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Získa zoznam transakcií
        
        Args:
            start_date: Od dátumu
            end_date: Do dátumu
            category_id: Filter podľa kategórie
            limit: Max počet záznamov
            
        Returns:
            Zoznam transakcií
        """
        try:
            query = """
                SELECT 
                    t.TransactionID, t.TransactionDate, t.Amount, t.Currency,
                    t.MerchantName, c.Name as CategoryName, t.Description,
                    t.TransactionType, t.PaymentMethod, t.CO2Footprint
                FROM Transactions t
                LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
                WHERE 1=1
            """
            params = []
            
            if start_date:
                query += " AND t.TransactionDate >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND t.TransactionDate <= ?"
                params.append(end_date.isoformat())
            
            if category_id:
                query += " AND t.CategoryID = ?"
                params.append(category_id)
            
            query += " ORDER BY t.TransactionDate DESC LIMIT ?"
            params.append(limit)
            
            result = self.execute(query, tuple(params))
            
            # Convert rows to dictionaries
            columns = ['TransactionID', 'TransactionDate', 'Amount', 'Currency',
                      'MerchantName', 'CategoryName', 'Description',
                      'TransactionType', 'PaymentMethod', 'CO2Footprint']
            
            transactions = []
            for row in result.rows:
                transactions.append(dict(zip(columns, row)))
            
            return transactions
            
        except Exception as e:
            logger.error(f"Chyba pri získavaní transakcií: {e}")
            return []
    
    def get_monthly_summary(
        self,
        year: int,
        month: int
    ) -> Dict[str, Any]:
        """
        Získa mesačný prehľad výdavkov
        
        Args:
            year: Rok
            month: Mesiac (1-12)
            
        Returns:
            Dictionary s prehľadom
        """
        try:
            # Celkové výdavky
            result = self.execute("""
                SELECT 
                    COUNT(*) as TransactionCount,
                    SUM(Amount) as TotalAmount,
                    AVG(Amount) as AvgAmount
                FROM Transactions
                WHERE strftime('%Y', TransactionDate) = ? 
                    AND strftime('%m', TransactionDate) = ?
                    AND TransactionType = 'Debit'
            """, (str(year), f"{month:02d}"))
            
            row = result.rows[0] if result.rows else (0, 0, 0)
            summary = {
                'transaction_count': row[0] or 0,
                'total_amount': float(row[1] or 0),
                'avg_amount': float(row[2] or 0)
            }
            
            # Výdavky podľa kategórií
            result = self.execute("""
                SELECT 
                    c.Name as Category,
                    COUNT(*) as Count,
                    SUM(t.Amount) as Total
                FROM Transactions t
                LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
                WHERE strftime('%Y', t.TransactionDate) = ? 
                    AND strftime('%m', t.TransactionDate) = ?
                    AND t.TransactionType = 'Debit'
                GROUP BY c.Name
                ORDER BY Total DESC
            """, (str(year), f"{month:02d}"))
            
            categories = []
            for row in result.rows:
                categories.append({
                    'category': row[0] or 'Iné',
                    'count': row[1],
                    'total': float(row[2])
                })
            
            summary['by_category'] = categories
            
            return summary
            
        except Exception as e:
            logger.error(f"Chyba pri získavaní prehľadu: {e}")
            return {
                'transaction_count': 0,
                'total_amount': 0,
                'avg_amount': 0,
                'by_category': []
            }


# Singleton inštancia
db_client = DatabaseClient()

