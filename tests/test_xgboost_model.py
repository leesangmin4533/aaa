import pandas as pd
import pickle

from prediction import xgboost


class DummyModel:
    def predict(self, X):
        return [99.0]


def test_train_and_predict_loads_tuned_model(tmp_path, monkeypatch):
    """사전 학습된 모델이 존재하면 해당 모델을 사용해 예측하는지 검증합니다."""
    model_dir = tmp_path / "models"
    model_dir.mkdir()

    with open(model_dir / "model_001.pkl", "wb") as f:
        pickle.dump(DummyModel(), f)

    def fake_weather(dates):
        return pd.DataFrame(
            {
                "date": dates,
                "temperature": [0.0] * len(dates),
                "rainfall": [0.0] * len(dates),
            }
        )

    monkeypatch.setattr(xgboost, "get_weather_data", fake_weather)

    result = xgboost.train_and_predict(
        "001", pd.DataFrame(), model_dir=model_dir
    )

    assert result == 99.0
