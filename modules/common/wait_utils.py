from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def wait_and_click_cell(driver, cell_id: str, timeout: int = 10) -> None:
    """Wait for a grid cell to appear and be clickable, then click it.

    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver instance.
    cell_id : str
        DOM ID of the grid cell to click.
    timeout : int, optional
        Maximum seconds to wait for the cell.
    """
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, f'//*[@id="{cell_id}"]'))
    )
    WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.ID, cell_id))
    )
    driver.find_element(By.ID, cell_id).click()

__all__ = ["wait_and_click_cell"]
