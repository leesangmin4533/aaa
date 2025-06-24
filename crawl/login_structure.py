import os
import json


def create_login_structure():
    """Create login structure file with selectors."""
    os.makedirs('structure', exist_ok=True)
    cfg = {
        "url": "https://store.bgfretail.com/websrc/deploy/index.html",
        "id_selector": "#input_id",
        "password_selector": "#input_pw",
        "submit_selector": "button[type=submit]"
    }
    with open(os.path.join('structure', 'login_structure.json'), 'w') as f:
        json.dump(cfg, f, indent=2)


if __name__ == "__main__":
    create_login_structure()
