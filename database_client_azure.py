"""
Azure SQL Database klient pre prácu s transakciami
"""
import pyodbc
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import json

from config import settings


logger = logging.getLogger(__name__)


class DatabaseClient:
    """Klient pre prácu s Azure SQL Database"""
    
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or settings.sql_connection_string
    
    def _get_connection(self) -> pyodbc.Connection:
        """Vytvorí databázové spojenie"""
        return pyodbc.connect(self.connection_string)
    
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
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            query = """
                INSERT INTO Transactions (
                    TransactionDate, Amount, Currency, MerchantID, MerchantName,
                    AccountNumber, IBAN, CategoryID, Description,
                    VariableSymbol, ConstantSymbol, SpecificSymbol,
                    TransactionType, PaymentMethod, CO2Footprint,
                    RawEmailData, AIConfidence, CategorySource
                )
                OUTPUT INSERTED.TransactionID
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(query, (
                transaction_date, amount, currency, merchant_id, merchant_name,
                account_number, iban, category_id, description,
                variable_symbol, constant_symbol, specific_symbol,
                transaction_type, payment_method, co2_footprint,
                raw_email_data, ai_confidence, category_source
            ))
            
            transaction_id = cursor.fetchone()[0]
            conn.commit()
            
            logger.info(f"Vložená transakcia ID: {transaction_id}")
            return transaction_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Chyba pri vkladaní transakcie: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
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
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Skús najprv nájsť existujúceho
            if iban:
                cursor.execute(
                    "SELECT MerchantID FROM Merchants WHERE IBAN = ?",
                    (iban,)
                )
            elif ico:
                cursor.execute(
                    "SELECT MerchantID FROM Merchants WHERE ICO = ?",
                    (ico,)
                )
            else:
                cursor.execute(
                    "SELECT MerchantID FROM Merchants WHERE Name = ?",
                    (name,)
                )
            
            row = cursor.fetchone()
            if row:
                merchant_id = row[0]
                logger.info(f"Nájdený existujúci obchodník ID: {merchant_id}")
                return merchant_id
            
            # Vytvor nového
            finstat_json = json.dumps(finstat_data) if finstat_data else None
            
            cursor.execute("""
                INSERT INTO Merchants (
                    Name, IBAN, AccountNumber, ICO, FinstatData, DefaultCategoryID
                )
                OUTPUT INSERTED.MerchantID
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, iban, account_number, ico, finstat_json, default_category_id))
            
            merchant_id = cursor.fetchone()[0]
            conn.commit()
            
            logger.info(f"Vytvorený nový obchodník ID: {merchant_id}")
            return merchant_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Chyba pri práci s obchodníkom: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_category_id_by_name(self, category_name: str) -> Optional[int]:
        """Získa ID kategórie podľa názvu"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT CategoryID FROM Categories WHERE Name = ?",
                (category_name,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            cursor.close()
            conn.close()
    
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
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT TOP (?)
                    t.TransactionID, t.TransactionDate, t.Amount, t.Currency,
                    t.MerchantName, c.Name as CategoryName, t.Description,
                    t.TransactionType, t.PaymentMethod, t.CO2Footprint
                FROM Transactions t
                LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
                WHERE 1=1
            """
            params = [limit]
            
            if start_date:
                query += " AND t.TransactionDate >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND t.TransactionDate <= ?"
                params.append(end_date)
            
            if category_id:
                query += " AND t.CategoryID = ?"
                params.append(category_id)
            
            query += " ORDER BY t.TransactionDate DESC"
            
            cursor.execute(query, params)
            
            columns = [column[0] for column in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
            
        finally:
            cursor.close()
            conn.close()
    
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
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Celkové výdavky
            cursor.execute("""
                SELECT 
                    COUNT(*) as TransactionCount,
                    SUM(Amount) as TotalAmount,
                    AVG(Amount) as AvgAmount
                FROM Transactions
                WHERE YEAR(TransactionDate) = ? 
                    AND MONTH(TransactionDate) = ?
                    AND TransactionType = 'Debit'
            """, (year, month))
            
            row = cursor.fetchone()
            summary = {
                'transaction_count': row[0] or 0,
                'total_amount': float(row[1] or 0),
                'avg_amount': float(row[2] or 0)
            }
            
            # Výdavky podľa kategórií
            cursor.execute("""
                SELECT 
                    c.Name as Category,
                    COUNT(*) as Count,
                    SUM(t.Amount) as Total
                FROM Transactions t
                LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
                WHERE YEAR(t.TransactionDate) = ? 
                    AND MONTH(t.TransactionDate) = ?
                    AND t.TransactionType = 'Debit'
                GROUP BY c.Name
                ORDER BY Total DESC
            """, (year, month))
            
            categories = []
            for row in cursor.fetchall():
                categories.append({
                    'category': row[0] or 'Iné',
                    'count': row[1],
                    'total': float(row[2])
                })
            
            summary['by_category'] = categories
            
            return summary
            
        finally:
            cursor.close()
            conn.close()


# Singleton inštancia
db_client = DatabaseClient()

