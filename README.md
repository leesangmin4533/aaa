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
   The script now also generates `module_map_main.json` summarizing the roles of
   key modules whenever it is executed.
   It also detects pop-up dialogs using z-index and size rules and attempts to
   close them automatically. The legacy ``POPUP_CLOSE_SCRIPT`` constant has been
   removed since JavaScript injection is no longer required.

## Logging

`create_logger` now accepts an optional file path so console messages can also
be saved to disk. Example:

```python
from log_util import create_logger
log = create_logger("arrow_fallback", log_file="arrow_fallback.log")
```

Detailed steps inside `scroll_with_arrow_fallback_loop` continue to use the
``log_path`` argument for their own log file.

The mid-category sales automation now relies on the Python functions in
`modules/sales_analysis`. These helpers navigate the grid and click each cell in
order while logging progress. Arrow key input is combined with direct clicks to
ensure the focus moves reliably.

`row_click_by_arrow`는 간단한 조건 검사를 하며 방향키로 행을 이동해
적합한 셀을 클릭하는 보조 함수다. 메인 스크립트에서 메뉴 이동 직후 호출되어
초기 행 선택을 담당한다.

During the grid interaction the script scrolls through all rows, collecting
every visible code cell. Duplicates are removed and the resulting dictionary is
sorted by code number. Each cell is clicked in order with retries if needed.
The loop automatically stops when the same code appears three times or when too
many consecutive cells are missing. Before exit, the function logs the last
code, the last cell ID, recent click counts and the current focused element to
aid debugging.
The helper ``scroll_to_expand_dom`` moves the trackbar to the bottom of the grid
so every code cell is loaded before collection begins.


The structure files in the `structure` directory describe the XPath selectors
used for automation. If the login page changes, regenerate these JSON files to
keep the stored selectors valid.

`wait_click_login.json` provides a minimal example showing how to wait up to
ten seconds for the login button to appear before clicking it. The snippet can
be adapted to other actions that require an explicit wait-and-click sequence.

`login_sequence.json` defines the basic login automation. It loads the
credentials from `.env` and sends the Enter key twice after typing the
password. `nexacro_idpw_input_physical.json` performs a similar sequence but
includes explicit clicks on each field before typing.

## Generating Commands from Snippet Data

Use `modules/common/snippet_utils.py` in **json** mode to convert DOM snippet results into a JSON command sequence. The input file must contain an `id목록` array with element IDs. If a value includes a tag after a colon (e.g. `btn_search:button`), an extra click step is inserted for buttons.

Example:
```json
{"id목록": ["btn_search:button", "edt_id:input", "txt_pw:input"]}
```

Generate the commands:
```bash
python -m modules.common.snippet_utils json sample_snippet.json commands_output.json
```


## Quick Inventory Command Generation

Use the same script in **command** mode when you have a list of element IDs and need to build
an automation sequence quickly. It reads a snippet file containing
`id목록` and creates a command JSON following simple rules:

- IDs starting with `btn_` get a `click` step after locating the element.
- IDs starting with `edt_` or `txt_` include a `send_keys` placeholder.
- All other IDs only generate a `find_element` step.

Example:
```bash
python -m modules.common.snippet_utils command modules/inventory/inventory_list_snippet.json \
    modules/inventory/inventory_list_cmd.json
```
Run the resulting automation:
```bash
python modules/inventory/run_inventory_list.py
```
