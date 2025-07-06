from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

import pandas as pd

from .selector import SELECTORS


def wait_for_page_load(driver, timeout: int = 10) -> None:
    """구성비 화면이 완전히 로드될 때까지 대기한다."""
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState === 'complete'")
    )


def parse_mix_ratio_data(driver) -> pd.DataFrame:
    """그리드 데이터를 Pandas DataFrame으로 변환한다.

    실제 그리드 구조에 맞게 추출 로직을 수정해야 한다.
    """
    wait_for_page_load(driver)

    # TODO: 실제 Nexacro 그리드 구조에 맞추어 데이터 파싱 구현
    # 아래는 개략적인 예시 코드
    data = driver.execute_script(
        """
try {
    var grid = nexacro.getApplication().mainframe.VFrameSet00.WorkFrameSet.form.div_work.form.Grid00;
    var dataset = grid.getBindDataset();
    var rows = dataset.rowcount;
    var cols = dataset.colcount;
    var result = [];
    for (var r = 0; r < rows; r++) {
        var row = {};
        for (var c = 0; c < cols; c++) {
            row[dataset.getColID(c)] = dataset.getColumn(r, c);
        }
        result.push(row);
    }
    return result;
} catch (e) {
    return 'error:' + e.toString();
}
"""
    )

    if isinstance(data, str) and data.startswith("error:"):
        raise RuntimeError(f"데이터 추출 실패: {data}")

    return pd.DataFrame(data)
