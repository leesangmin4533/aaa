import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.sales_analysis.focus_tracker import highlight_active_element


def test_highlight_active_element_logs(tmp_path):
    log_file = tmp_path / "focus_log.txt"
    driver = MagicMock()
    elem = MagicMock()
    elem.get_attribute.return_value = "cell_0_0"
    # first execute_script call returns active element
    # second call sets outline
    driver.execute_script.side_effect = [elem, None]

    result = highlight_active_element(driver, color="blue", log_path=str(log_file))

    assert result == "cell_0_0"
    assert driver.execute_script.call_args_list[0][0][0] == "return document.activeElement"
    assert "style.outline" in driver.execute_script.call_args_list[1][0][0]

    with open(log_file, "r", encoding="utf-8") as f:
        contents = f.read()
    assert "현재 포커스" in contents
    assert "cell_0_0" in contents
