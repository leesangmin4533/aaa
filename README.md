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

`crawl/login_structure.py` refreshes `structure/login_structure.json` on every
run by opening the login page with Selenium and locating the input fields. When
any of the required elements cannot be found the script raises an error so the
process stops immediately. This guarantees that the login structure in use is
always valid and up to date.

For environments that require XPath selectors, `crawl/login_structure_xpath.py`
performs the same validation and writes `structure/login_structure_xpath.json`.
The script waits for the XPath elements to appear using `WebDriverWait` before
recording them. Both files are recreated each run so the automation always uses
the latest page structure.

During normal execution the login credentials are entered using the sequence
"ID → Enter → Password → Enter". A final button click is attempted only as a
fallback if the Enter key does not submit the form.

After logging in, the script loops through multiple heuristic selectors to close
any pop‑ups. At least two passes are made so sequential pop‑ups are also
captured before moving on to menu navigation. The routine checks for remaining
close buttons after the loops and will abort if a pop‑up cannot be dismissed.

On Mondays the script navigates to **매출분석 > 중분류별 매출 구성비** using `navigate_sales_ratio.py` after closing any login pop‑ups.
Data extracted by future features will be stored under the `sales_analysis` directory.

`wait_click_login.json` provides a minimal example showing how to wait up to
ten seconds for the login button to appear before clicking it. The snippet can
be adapted to other actions that require an explicit wait-and-click sequence.
