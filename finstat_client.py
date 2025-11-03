"""
Finstat API integrácia pre získanie informácií o firmách
"""
import requests
from typing import Optional, Dict, Any
import logging
from dataclasses import dataclass
import re
import hashlib

from config import settings


logger = logging.getLogger(__name__)


@dataclass
class CompanyInfo:
    """Informácie o firme z Finstat"""
    ico: str
    name: str
    legal_form: Optional[str] = None
    activity: Optional[str] = None
    activity_code: Optional[str] = None
    address: Optional[str] = None
    iban: Optional[str] = None
    suggested_category: Optional[str] = None
    is_active: bool = True


class FinstatClient:
    """Klient pre Finstat API"""
    
    def __init__(
        self, 
        api_key: str = None, 
        private_key: str = None,
        api_url: str = None,
        station_id: str = None,
        station_name: str = None
    ):
        self.api_key = api_key or settings.finstat_api_key
        self.private_key = private_key or settings.finstat_private_key
        self.api_url = api_url or settings.finstat_api_url
        self.station_id = station_id or settings.finstat_station_id
        self.station_name = station_name or settings.finstat_station_name
        self.session = requests.Session()
    
    def _generate_hash(self, *params: str) -> str:
        """
        Generuje SHA256 hash pre Finstat API autentifikáciu
        
        Args:
            *params: Parametre pre hash (napr. ico, private_key)
            
        Returns:
            SHA256 hash string
        """
        # Spojí všetky parametre a private key
        hash_string = ''.join(str(p) for p in params) + self.private_key
        return hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
    
    def get_company_by_ico(self, ico: str) -> Optional[CompanyInfo]:
        """
        Získa informácie o firme podľa IČO
        
        Args:
            ico: IČO firmy
            
        Returns:
            CompanyInfo alebo None
        """
        try:
            # Vyčisti IČO (odstráň medzery a iné znaky)
            ico_clean = re.sub(r'\D', '', ico)
            
            # Vygeneruj hash (ico + private_key)
            hash_value = self._generate_hash(ico_clean)
            
            # Priprav URL a parametre
            url = f"{self.api_url}/detail"
            params = {
                'ico': ico_clean,
                'apikey': self.api_key,
                'hash': hash_value,
                'StationId': self.station_id,
                'StationName': self.station_name
            }
            
            logger.info(f"Calling Finstat API for IČO: {ico_clean}")
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # Parse XML response
            data = self._parse_xml_response(response.text)
            
            if not data:
                logger.warning(f"No data returned from Finstat for IČO: {ico_clean}")
                return None
            
            return self._parse_company_data(data)
            
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"Company not found in Finstat for IČO: {ico}")
            elif e.response.status_code == 403:
                logger.error(f"Unauthorized access to Finstat API - check API key and hash")
            elif e.response.status_code == 402:
                logger.error(f"Finstat API limit exceeded")
            else:
                logger.error(f"HTTP error from Finstat API: {e}")
            return None
        except requests.RequestException as e:
            logger.error(f"Chyba pri volaní Finstat API pre IČO {ico}: {e}")
            return None
    
    def _parse_xml_response(self, xml_text: str) -> Optional[Dict[str, Any]]:
        """
        Parsuje XML odpoveď z Finstat API
        
        Args:
            xml_text: XML string
            
        Returns:
            Dictionary s dátami alebo None
        """
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(xml_text)
            
            # Remove namespace if present
            namespace = ''
            if root.tag.startswith('{'):
                namespace = root.tag.split('}')[0] + '}'
            
            def get_text(element_name: str) -> Optional[str]:
                elem = root.find(f'{namespace}{element_name}')
                if elem is not None and elem.text:
                    return elem.text
                return None
            
            data = {
                'ICO': get_text('Ico'),
                'Name': get_text('Name'),
                'Street': get_text('Street'),
                'StreetNumber': get_text('StreetNumber'),
                'ZipCode': get_text('ZipCode'),
                'City': get_text('City'),
                'District': get_text('District'),
                'Region': get_text('Region'),
                'Activity': get_text('Activity'),
                'LegalFormText': get_text('LegalFormText'),
                'SkNaceText': get_text('SkNaceText'),
                'SkNaceCode': get_text('SkNaceCode'),
                'Anonymized': get_text('Anonymized') == 'true'
            }
            
            return data
            
        except Exception as e:
            logger.error(f"Error parsing Finstat XML response: {e}")
            return None
    
    def get_company_by_iban(self, iban: str) -> Optional[CompanyInfo]:
        """
        Získa informácie o firme podľa IBAN
        
        POZNÁMKA: Finstat API nepodporuje priame vyhľadávanie podľa IBAN.
        Táto metóda vráti None. Pre identifikáciu firmy použite IČO alebo názov.
        
        Args:
            iban: IBAN účtu firmy
            
        Returns:
            None (nepodporované Finstat API)
        """
        logger.warning("Finstat API nepodporuje vyhľadávanie podľa IBAN")
        return None
    
    def search_company_by_name(self, name: str) -> Optional[CompanyInfo]:
        """
        Vyhľadá firmu podľa názvu
        
        POZNÁMKA: Pre vyhľadávanie podľa názvu by bolo potrebné použiť
        Finstat vyhľadávacie API (nie detail API). Táto implementácia
        je zjednodušená a môže byť rozšírená podľa potreby.
        
        Args:
            name: Názov firmy
            
        Returns:
            CompanyInfo alebo None
        """
        logger.warning("Vyhľadávanie podľa názvu v Finstat API nie je plne implementované")
        return None
    
    def _parse_company_data(self, data: Dict[str, Any]) -> CompanyInfo:
        """
        Parsuje dáta z Finstat API odpovede
        
        Args:
            data: Dictionary s dátami z API
            
        Returns:
            CompanyInfo objekt
        """
        # Mapovanie aktivít na kategórie
        activity = data.get('Activity')
        suggested_category = self._suggest_category_from_activity(activity)
        
        # Vytvor adresu
        address_parts = []
        if data.get('Street'):
            address_parts.append(data['Street'])
        if data.get('StreetNumber'):
            address_parts.append(data['StreetNumber'])
        if data.get('ZipCode'):
            address_parts.append(data['ZipCode'])
        if data.get('City'):
            address_parts.append(data['City'])
        
        address = ', '.join(address_parts) if address_parts else None
        
        return CompanyInfo(
            ico=data.get('ICO', ''),
            name=data.get('Name', ''),
            legal_form=data.get('LegalFormText'),
            activity=activity,
            activity_code=data.get('SkNaceCode'),
            address=address,
            iban=None,  # IBAN nie je v detail API response
            suggested_category=suggested_category,
            is_active=not data.get('Anonymized', False)
        )
    
    def _suggest_category_from_activity(self, activity: Optional[str]) -> Optional[str]:
        """
        Navrhne kategóriu na základe činnosti firmy
        
        Args:
            activity: Popis činnosti firmy
            
        Returns:
            Názov kategórie alebo None
        """
        if not activity:
            return None
            
        activity_lower = activity.lower()
        
        # Mapovanie kľúčových slov na kategórie
        category_keywords = {
            'Potraviny': [
                'maloobchod', 'potraviny', 'supermarket', 'hypermarket',
                'obchod s potravinami', 'retail', 'predaj potravín'
            ],
            'Drogéria': [
                'drogéria', 'kozmetika', 'lekáreň', 'farmácia',
                'predaj liekov', 'zdravotnícke potreby'
            ],
            'Reštaurácie a Kaviarne': [
                'reštaurácia', 'kaviareň', 'pohostinstvo', 'gastronómia',
                'stravovanie', 'bar', 'pub', 'bistro', 'pizzeria'
            ],
            'Donáška jedla': [
                'donáška jedla', 'rozvoz jedla', 'food delivery'
            ],
            'Doprava': [
                'doprava', 'taxi', 'autobus', 'vlak', 'letecká doprava',
                'preprava', 'car sharing', 'zdieľanie vozidiel', 'parkovanie'
            ],
            'Bývanie': [
                'nehnuteľnosti', 'prenájom', 'bývanie', 'reality',
                'správa bytov', 'energie', 'elektrina', 'plyn', 'voda'
            ],
            'Zdravie': [
                'zdravotníctvo', 'lekár', 'ambulancia', 'nemocnica',
                'zdravotná poisťovňa', 'fitness', 'wellness'
            ],
            'Zábava': [
                'zábava', 'kino', 'divadlo', 'koncert', 'festival',
                'kultúra', 'múzeum', 'galéria', 'streaming'
            ],
            'Oblečenie': [
                'oblečenie', 'odev', 'móda', 'textil', 'obuv',
                'predaj oblečenia', 'fashion'
            ],
            'Telefón a Internet': [
                'telekomunikácie', 'internet', 'telefón', 'mobilný operátor',
                'telekom', 'dáta', 'broadband'
            ],
            'Vzdelávanie': [
                'vzdelávanie', 'škola', 'kurz', 'školenie', 'univerzita',
                'jazykové kurzy', 'education'
            ],
            'Šport': [
                'šport', 'športové potreby', 'telocvičňa', 'gym',
                'fitnes', 'športové centrum'
            ]
        }
        
        # Hľadaj zhody
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in activity_lower:
                    return category
                    
        return None


# Singleton inštancia
finstat_client = FinstatClient()


def get_company_info(
    ico: Optional[str] = None,
    iban: Optional[str] = None,
    name: Optional[str] = None
) -> Optional[CompanyInfo]:
    """
    Získa informácie o firme z Finstat
    
    Args:
        ico: IČO firmy
        iban: IBAN účtu
        name: Názov firmy
        
    Returns:
        CompanyInfo alebo None
    """
    # Priorita: IČO > IBAN > Názov
    if ico:
        return finstat_client.get_company_by_ico(ico)
    elif iban:
        return finstat_client.get_company_by_iban(iban)
    elif name:
        return finstat_client.search_company_by_name(name)
    
    return None

