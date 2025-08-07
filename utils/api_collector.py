import requests
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

LOGIN_URL = "https://www.bgfretail.com/bgf/login/login.do"
API_URL = "https://www.bgfretail.com/st/STMB011_M0_SELECT.do"

def get_session(credentials: Dict[str, str]) -> Optional[requests.Session]:
    """Logs in and returns a session object."""
    session = requests.Session()
    try:
        login_data = {
            'user_id': credentials.get('id'),
            'user_pwd': credentials.get('password'),
        }
        response = session.post(LOGIN_URL, data=login_data, timeout=10)
        response.raise_for_status()

        if "login_fail" in response.text:
            logger.error("Login failed. Please check credentials.")
            return None
        
        logger.info("Login successful. Session created.")
        return session
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create session: {e}", exc_info=True)
        return None

def fetch_sales_data(session: requests.Session, store_code: str, date_str: str) -> Optional[pd.DataFrame]:
    """Fetches sales data for a given store and date using the API."""
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0",
    }
    # Correctly formatted f-string with double curly braces for literal JSON braces
    payload = {
        '_dataSet_': f'{{ "_id_":"ds_cond", "_state_":1, "_rowidx_":0, "_rows_":[{{ "_state_":2, "send_date":"{date_str}", "store_code":"{store_code}" }}] }}'
    }

    try:
        response = session.post(API_URL, headers=headers, data=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        records = data.get('ds_list', [])
        
        if not records:
            logger.warning(f"No sales data found for {store_code} on {date_str}.")
            return None

        df = pd.DataFrame(records)
        logger.info(f"Successfully fetched {len(df)} records for {store_code} on {date_str}.")
        return df

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for {store_code} on {date_str}: {e}", exc_info=True)
        return None
    except (ValueError, KeyError) as e:
        logger.error(f"Failed to parse JSON response for {store_code} on {date_str}: {e}", exc_info=True)
        return None