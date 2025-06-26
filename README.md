# Automated Sales Analysis

This project opens the BGF Retail store login page using Selenium. It is a simplified version intended for testing.

## Setup

1. Install dependencies (Selenium, python-dotenv, requests and BeautifulSoup):
   ```bash
   pip install -r requirements.txt
   ```
2. Run the script:
   ```bash
   python main.py
   ```

`crawl/login_structure.py` and `crawl/login_structure_xpath.py` can regenerate
the structure files under the `structure` directory if the login page changes.
These helpers ensure the stored selectors remain valid.

`wait_click_login.json` provides a minimal example showing how to wait up to
ten seconds for the login button to appear before clicking it. The snippet can
be adapted to other actions that require an explicit wait-and-click sequence.
