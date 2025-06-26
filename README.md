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


The structure files in the `structure` directory describe the XPath selectors
used for automation. If the login page changes, regenerate these JSON files to
keep the stored selectors valid.

`wait_click_login.json` provides a minimal example showing how to wait up to
ten seconds for the login button to appear before clicking it. The snippet can
be adapted to other actions that require an explicit wait-and-click sequence.

`login_sequence.json` defines the basic login automation. It loads the
credentials from `.env` and sends the Enter key three times after typing the
password. `nexacro_idpw_input_physical.json` performs a similar sequence but
includes explicit clicks on each field before typing.
