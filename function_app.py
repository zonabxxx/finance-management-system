"""
Azure Function pre spracovanie B-mail notifikácií
"""
import azure.functions as func
import logging
import json
from datetime import datetime

from email_parser import parse_bmail_notification
from finstat_client import get_company_info
from ai_categorization import categorize_transaction
from database_client import db_client


# Vytvor Azure Function App
app = func.FunctionApp()


@app.function_name(name="ProcessEmailNotification")
@app.route(route="process-email", auth_level=func.AuthLevel.FUNCTION)
def process_email_notification(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function endpoint pre spracovanie B-mail notifikácií
    
    Tento endpoint prijíma email z Azure Logic App a:
    1. Parsuje email a extrahuje transakčné dáta
    2. Identifikuje obchodníka pomocou Finstat API
    3. Kategorizuje transakciu pomocou AI
    4. Uloží do Azure SQL Database
    """
    logging.info('Processing email notification...')
    
    try:
        # Získaj email z requestu
        req_body = req.get_json()
        
        email_body = req_body.get('body')
        email_subject = req_body.get('subject', '')
        
        if not email_body:
            return func.HttpResponse(
                json.dumps({'error': 'Missing email body'}),
                status_code=400,
                mimetype='application/json'
            )
        
        # 1. Parsuj email
        logging.info('Parsing email...')
        transaction_data = parse_bmail_notification(email_body)
        
        if not transaction_data:
            return func.HttpResponse(
                json.dumps({'error': 'Failed to parse email'}),
                status_code=400,
                mimetype='application/json'
            )
        
        logging.info(f"Parsed transaction: {transaction_data['merchant_name']} - {transaction_data['amount']} EUR")
        
        # 2. Získaj informácie o firme z Finstat
        logging.info('Fetching company info from Finstat...')
        company_info = None
        
        if transaction_data.get('iban'):
            company_info = get_company_info(iban=transaction_data['iban'])
        
        if not company_info and transaction_data.get('merchant_name'):
            company_info = get_company_info(name=transaction_data['merchant_name'])
        
        if company_info:
            logging.info(f"Found company: {company_info.name} (IČO: {company_info.ico})")
        
        # 3. Kategorizuj transakciu
        logging.info('Categorizing transaction...')
        category_prediction = categorize_transaction(
            merchant_name=transaction_data['merchant_name'],
            amount=transaction_data['amount'],
            description=transaction_data.get('description'),
            company_info=company_info,
            iban=transaction_data.get('iban')
        )
        
        logging.info(
            f"Category: {category_prediction.category} "
            f"(confidence: {category_prediction.confidence:.2f}, "
            f"source: {category_prediction.source})"
        )
        
        # 4. Získaj ID kategórie z databázy
        category_id = db_client.get_category_id_by_name(category_prediction.category)
        
        if not category_id:
            logging.warning(f"Category '{category_prediction.category}' not found in database")
            category_id = db_client.get_category_id_by_name('Iné')
        
        # 5. Vytvor alebo získaj obchodníka
        merchant_id = None
        if company_info:
            merchant_id = db_client.get_or_create_merchant(
                name=transaction_data['merchant_name'],
                iban=transaction_data.get('iban'),
                account_number=transaction_data.get('account_number'),
                ico=company_info.ico if company_info else None,
                finstat_data={
                    'name': company_info.name,
                    'activity': company_info.activity,
                    'legal_form': company_info.legal_form
                } if company_info else None,
                default_category_id=category_id
            )
        
        # 6. Ulož transakciu do databázy
        logging.info('Saving transaction to database...')
        transaction_id = db_client.insert_transaction(
            transaction_date=datetime.fromisoformat(transaction_data['transaction_date']),
            amount=transaction_data['amount'],
            currency=transaction_data['currency'],
            merchant_name=transaction_data['merchant_name'],
            merchant_id=merchant_id,
            account_number=transaction_data.get('account_number'),
            iban=transaction_data.get('iban'),
            category_id=category_id,
            description=transaction_data.get('description'),
            variable_symbol=transaction_data.get('variable_symbol'),
            constant_symbol=transaction_data.get('constant_symbol'),
            specific_symbol=transaction_data.get('specific_symbol'),
            transaction_type='Debit',
            payment_method=transaction_data.get('payment_method'),
            co2_footprint=transaction_data.get('co2_footprint'),
            raw_email_data=email_body,
            ai_confidence=category_prediction.confidence,
            category_source=category_prediction.source
        )
        
        logging.info(f'Transaction saved successfully with ID: {transaction_id}')
        
        # Vráť výsledok
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'transaction_id': transaction_id,
                'merchant_name': transaction_data['merchant_name'],
                'amount': transaction_data['amount'],
                'category': category_prediction.category,
                'confidence': category_prediction.confidence,
                'source': category_prediction.source
            }),
            status_code=200,
            mimetype='application/json'
        )
        
    except Exception as e:
        logging.error(f'Error processing email: {str(e)}', exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': str(e)
            }),
            status_code=500,
            mimetype='application/json'
        )


@app.function_name(name="GetTransactions")
@app.route(route="transactions", auth_level=func.AuthLevel.FUNCTION)
def get_transactions(req: func.HttpRequest) -> func.HttpResponse:
    """
    Endpoint pre získanie transakcií
    
    Query params:
    - start_date: Od dátumu (ISO format)
    - end_date: Do dátumu (ISO format)
    - category: Filter podľa kategórie
    - limit: Max počet záznamov (default 100)
    """
    try:
        # Získaj parametre
        start_date_str = req.params.get('start_date')
        end_date_str = req.params.get('end_date')
        category_name = req.params.get('category')
        limit = int(req.params.get('limit', 100))
        
        # Konvertuj dátumy
        start_date = datetime.fromisoformat(start_date_str) if start_date_str else None
        end_date = datetime.fromisoformat(end_date_str) if end_date_str else None
        
        # Získaj ID kategórie
        category_id = None
        if category_name:
            category_id = db_client.get_category_id_by_name(category_name)
        
        # Získaj transakcie
        transactions = db_client.get_transactions(
            start_date=start_date,
            end_date=end_date,
            category_id=category_id,
            limit=limit
        )
        
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'count': len(transactions),
                'transactions': transactions
            }, default=str),
            status_code=200,
            mimetype='application/json'
        )
        
    except Exception as e:
        logging.error(f'Error getting transactions: {str(e)}', exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': str(e)
            }),
            status_code=500,
            mimetype='application/json'
        )


@app.function_name(name="GetMonthlySummary")
@app.route(route="summary/monthly", auth_level=func.AuthLevel.FUNCTION)
def get_monthly_summary(req: func.HttpRequest) -> func.HttpResponse:
    """
    Endpoint pre získanie mesačného prehľadu
    
    Query params:
    - year: Rok (napr. 2025)
    - month: Mesiac (1-12)
    """
    try:
        year = int(req.params.get('year', datetime.now().year))
        month = int(req.params.get('month', datetime.now().month))
        
        summary = db_client.get_monthly_summary(year, month)
        
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'year': year,
                'month': month,
                'summary': summary
            }, default=str),
            status_code=200,
            mimetype='application/json'
        )
        
    except Exception as e:
        logging.error(f'Error getting summary: {str(e)}', exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': str(e)
            }),
            status_code=500,
            mimetype='application/json'
        )

