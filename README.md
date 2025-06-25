# Automated Sales Analysis

This project automates login and navigation for the BGF Retail store site using Selenium.

## Setup

1. Install dependencies (Selenium, python-dotenv, requests and BeautifulSoup):
   ```bash
   pip install -r requirements.txt
   ```
2. Create a `.env` file with your credentials:
   ```
   LOGIN_ID=your_username
   LOGIN_PW=your_password
   ```
3. Run the script:
   ```bash
   python main.py
   ```

`crawl/login_structure.py` refreshes `structure/login_structure.json` every time the
script runs by parsing the login page. Generic selectors are used if the page
cannot be fetched, ensuring the login process always starts with an up‑to‑date
structure file.

On Mondays the script navigates to **매출분석 > 중분류별 매출 구성비** using `navigate_sales_ratio.py` after closing any login pop‑ups.
Data extracted by future features will be stored under the `sales_analysis` directory.
