import os
import json
from typing import Optional

import requests
from bs4 import BeautifulSoup


URL = "https://store.bgfretail.com/websrc/deploy/index.html"


def _detect_selector(soup: BeautifulSoup, query: str, fallback: str) -> str:
    """Return a CSS selector for the first element matching ``query``."""
    element = soup.select_one(query)
    if not element:
        return fallback
    if element.get("id"):
        return f"#{element['id']}"
    if element.get("name"):
        return f"{element.name}[name='{element['name']}']"
    if element.get("class"):
        return f".{element.get('class')[0]}"
    return fallback


def create_login_structure() -> None:
    """Create ``login_structure.json`` by parsing the login page."""
    os.makedirs("structure", exist_ok=True)
    id_selector: str = "input[type='text']"
    password_selector: str = "input[type='password']"
    submit_selector: str = "button"

    try:
        resp = requests.get(URL, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        id_selector = _detect_selector(soup, id_selector, id_selector)
        password_selector = _detect_selector(soup, password_selector, password_selector)
        submit_selector = _detect_selector(soup, submit_selector, submit_selector)
    except Exception:
        # Fallback to generic selectors when the page cannot be fetched
        pass

    cfg = {
        "url": URL,
        "id_selector": id_selector,
        "password_selector": password_selector,
        "submit_selector": submit_selector,
    }
    with open(os.path.join("structure", "login_structure.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    create_login_structure()
