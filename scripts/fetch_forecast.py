import requests
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging
import sys

# Add the project root to the Python path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.log_util import get_logger

FORECAST_FILE = ROOT_DIR / 'code_outputs' / 'forecast.json'

log = get_logger(__name__, "forecast")

def fetch_and_save_forecast():
    """
    Fetches tomorrow's weather forecast using the 단기예보 API and saves it to a JSON file.
    This script is intended to be run once daily, after 02:00 AM.
    """
    api_key = os.environ.get("KMA_API_KEY")
    if not api_key:
        log.error("KMA_API_KEY environment variable not set. Cannot fetch weather data.")
        return

    nx, ny = 60, 127  # Coordinates for the store location
    today = datetime.now().date()
    tomorrow_str = (today + timedelta(days=1)).strftime('%Y%m%d')

    # 단기예보 API는 보통 02:00에 데이터를 생성하므로 base_time을 0200으로 설정
    base_date_str = today.strftime('%Y%m%d')
    base_time_str = '0200'

    url = (
        "https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0/getVilageFcst"
        f"?pageNo=1&numOfRows=1000&dataType=JSON&base_date={base_date_str}&base_time={base_time_str}"
        f"&nx={nx}&ny={ny}&authKey={api_key}"
    )

    log.info(f"Fetching forecast for {tomorrow_str} from KMA API.")

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        result_code = data.get('response', {}).get('header', {}).get('resultCode')
        if result_code != '00':
            log.error(f"Failed to fetch forecast. API resultCode: {result_code}, Msg: {data.get('response', {}).get('header', {}).get('resultMsg')}")
            return

        items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
        
        temps = [float(item['fcstValue']) for item in items if item['category'] == 'TMP' and item['fcstDate'] == tomorrow_str]
        
        rains = []
        for item in items:
            if item['category'] == 'PCP' and item['fcstDate'] == tomorrow_str:
                value = item['fcstValue']
                if '강수없음' in value:
                    rains.append(0.0)
                else:
                    try:
                        numeric_value = float(value.lower().replace('mm', '').replace('cm', ''))
                        rains.append(numeric_value)
                    except (ValueError, TypeError):
                        log.warning(f"Could not parse PCP value: '{value}'")
                        rains.append(0.0)

        if not temps:
            log.warning("No temperature data found in the forecast response.")
            avg_temp = 0.0
        else:
            avg_temp = sum(temps) / len(temps)

        total_rainfall = sum(rains) if rains else 0.0

        forecast_data = {
            'target_date': (today + timedelta(days=1)).strftime('%Y-%m-%d'),
            'temperature': avg_temp,
            'rainfall': total_rainfall,
            'updated_at': datetime.now().isoformat()
        }

        FORECAST_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(FORECAST_FILE, 'w', encoding='utf-8') as f:
            json.dump(forecast_data, f, ensure_ascii=False, indent=4)
        
        log.info(f"Successfully saved forecast to {FORECAST_FILE}.")
        log.info(f"Data: Temperature={avg_temp:.2f}, Rainfall={total_rainfall:.2f}")

    except requests.exceptions.RequestException as e:
        log.error(f"Error fetching weather data: {e}", exc_info=True)
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    fetch_and_save_forecast()
