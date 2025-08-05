import logging
from prediction.monitor import log_prediction_vs_actual


def test_log_prediction_vs_actual_returns_dict(caplog):
    caplog.set_level(logging.INFO)
    result = log_prediction_vs_actual(10.0, 8.0, False)
    assert result['diff'] == -2.0
    assert 'Prediction vs Actual' in caplog.text
