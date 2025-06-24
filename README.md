# Automated Sales Analysis

This project automates login and navigation for the BGF Retail store site using Selenium.

## Setup

1. Install dependencies:
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

The script checks for `structure/login_structure.json`. If it does not exist, it will be created automatically via `crawl/login_structure.py`.

On Mondays the script navigates to **매출분석 > 중분류별 매출 구성비** using `navigate_sales_ratio.py` after closing any login pop‑ups.
Data extracted by future features will be stored under the `sales_analysis` directory.
