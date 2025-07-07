from selenium.webdriver.remote.webdriver import WebDriver


def find_text_cell_by_code(driver: WebDriver, code: str):
    """Return the text cell element matching ``code`` in ``gdList``."""
    script = """
return [...document.querySelectorAll('div[id*="gdList"][id*="cell_"][id$="_0:text"]')]
  .find(el => el.innerText?.trim() === arguments[0]) || null;
"""
    return driver.execute_script(script, code)


def find_clickable_cell_by_code(driver: WebDriver, code: str):
    """Return the clickable cell element inferred from the text cell."""
    text_el = find_text_cell_by_code(driver, code)
    if not text_el:
        return None
    click_id = driver.execute_script("return arguments[0].id.replace(':text', '')", text_el)
    return driver.execute_script("return document.getElementById(arguments[0])", click_id)
