"""
ChatGPT Agent pre analýzu financií
"""
from openai import OpenAI
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime, timedelta

from config import settings
from database_client import db_client


logger = logging.getLogger(__name__)


class FinanceAssistantAgent:
    """ChatGPT Agent pre správu financií"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.assistant_id = settings.openai_assistant_id
        
        # Ak assistant neexistuje, vytvor ho
        if not self.assistant_id or self.assistant_id == 'asst_your_assistant_id':
            self.assistant_id = self._create_assistant()
    
    def _create_assistant(self) -> str:
        """
        Vytvorí nového OpenAI Assistanta
        
        Returns:
            ID assistanta
        """
        try:
            assistant = self.client.beta.assistants.create(
                name=settings.agent_name,
                instructions="""Si AI finančný asistent pre slovenského používateľa. 
                
Pomáhaš analyzovať výdavky a príjmy, odpovedáš na otázky o finančných transakciách 
a poskytuje insights o útrateach.

Máš prístup k nasledujúcim funkciám:
- get_transactions: Získa zoznam transakcií
- get_monthly_summary: Získa mesačný prehľad výdavkov
- get_category_breakdown: Získa rozpad výdavkov podľa kategórií
- find_similar_transactions: Nájde podobné transakcie

Vždy odpovedáš v slovenčine a snažíš sa byť užitočný a priateľský.
Ak používateľ chce vedieť "koľko som minul na X", použi get_category_breakdown.
Ak používateľ chce "ukáž mi transakcie za X", použi get_transactions.
Ak používateľ chce "mesačný prehľad", použi get_monthly_summary.

Pri odpovediach buď konkrétny, používaj čísla a dátumy.
""",
                model=settings.openai_model,
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "get_transactions",
                            "description": "Získa zoznam transakcií za dané obdobie",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "start_date": {
                                        "type": "string",
                                        "description": "Počiatočný dátum (YYYY-MM-DD)"
                                    },
                                    "end_date": {
                                        "type": "string",
                                        "description": "Konečný dátum (YYYY-MM-DD)"
                                    },
                                    "category": {
                                        "type": "string",
                                        "description": "Filter podľa kategórie (voliteľné)"
                                    },
                                    "limit": {
                                        "type": "integer",
                                        "description": "Max počet záznamov (default 50)"
                                    }
                                }
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "get_monthly_summary",
                            "description": "Získa mesačný prehľad výdavkov",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "year": {
                                        "type": "integer",
                                        "description": "Rok (napr. 2025)"
                                    },
                                    "month": {
                                        "type": "integer",
                                        "description": "Mesiac (1-12)"
                                    }
                                },
                                "required": ["year", "month"]
                            }
                        }
                    }
                ]
            )
            
            logger.info(f"Created new assistant: {assistant.id}")
            return assistant.id
            
        except Exception as e:
            logger.error(f"Error creating assistant: {e}")
            raise
    
    def chat(self, user_message: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Pošle správu asistentovi a získa odpoveď
        
        Args:
            user_message: Správa od používateľa
            thread_id: ID existujúcej konverzácie (voliteľné)
            
        Returns:
            Dictionary s odpoveďou a thread_id
        """
        try:
            # Vytvor alebo použi existujúci thread
            if not thread_id:
                thread = self.client.beta.threads.create()
                thread_id = thread.id
                logger.info(f"Created new thread: {thread_id}")
            
            # Pridaj správu používateľa
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_message
            )
            
            # Spusti assistanta
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id
            )
            
            # Čakaj na dokončenie a spracuj function calls
            while True:
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
                
                if run_status.status == 'completed':
                    break
                elif run_status.status == 'requires_action':
                    # Spracuj function calls
                    tool_outputs = self._handle_function_calls(
                        run_status.required_action.submit_tool_outputs.tool_calls
                    )
                    
                    # Odošli výsledky funkcií
                    self.client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread_id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )
                elif run_status.status in ['failed', 'cancelled', 'expired']:
                    logger.error(f"Run failed with status: {run_status.status}")
                    break
            
            # Získaj odpoveď assistanta
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id,
                order='desc',
                limit=1
            )
            
            assistant_message = messages.data[0].content[0].text.value
            
            return {
                'response': assistant_message,
                'thread_id': thread_id
            }
            
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return {
                'response': f"Prepáč, vyskytla sa chyba: {str(e)}",
                'thread_id': thread_id
            }
    
    def _handle_function_calls(self, tool_calls: List[Any]) -> List[Dict[str, str]]:
        """
        Spracuje function calls z assistanta
        
        Args:
            tool_calls: Zoznam function calls
            
        Returns:
            Zoznam výsledkov
        """
        tool_outputs = []
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            logger.info(f"Calling function: {function_name} with args: {function_args}")
            
            # Zavolaj príslušnú funkciu
            if function_name == 'get_transactions':
                result = self._get_transactions(function_args)
            elif function_name == 'get_monthly_summary':
                result = self._get_monthly_summary(function_args)
            else:
                result = {'error': f'Unknown function: {function_name}'}
            
            tool_outputs.append({
                'tool_call_id': tool_call.id,
                'output': json.dumps(result, ensure_ascii=False, default=str)
            })
        
        return tool_outputs
    
    def _get_transactions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Získa transakcie z databázy"""
        try:
            start_date = None
            end_date = None
            
            if 'start_date' in args:
                start_date = datetime.fromisoformat(args['start_date'])
            
            if 'end_date' in args:
                end_date = datetime.fromisoformat(args['end_date'])
            
            category_name = args.get('category')
            category_id = None
            if category_name:
                category_id = db_client.get_category_id_by_name(category_name)
            
            limit = args.get('limit', 50)
            
            transactions = db_client.get_transactions(
                start_date=start_date,
                end_date=end_date,
                category_id=category_id,
                limit=limit
            )
            
            return {
                'count': len(transactions),
                'transactions': transactions
            }
            
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return {'error': str(e)}
    
    def _get_monthly_summary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Získa mesačný prehľad"""
        try:
            year = args.get('year', datetime.now().year)
            month = args.get('month', datetime.now().month)
            
            summary = db_client.get_monthly_summary(year, month)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting summary: {e}")
            return {'error': str(e)}


# Singleton inštancia
finance_assistant = FinanceAssistantAgent()


def ask_finance_question(question: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Hlavná funkcia pre komunikáciu s finančným asistentom
    
    Args:
        question: Otázka od používateľa
        thread_id: ID konverzácie (voliteľné)
        
    Returns:
        Dictionary s odpoveďou a thread_id
    """
    return finance_assistant.chat(question, thread_id)

