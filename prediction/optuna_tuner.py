import logging
from pathlib import Path
from typing import Any

import joblib
import optuna
import pandas as pd
import xgboost
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def tune_model(mid_code: str, df: pd.DataFrame, output_dir: Path) -> xgboost.XGBRegressor:
    """Optuna로 XGBoost 모델 하이퍼파라미터 튜닝 후 저장합니다.

    Parameters
    ----------
    mid_code : str
        중분류 코드.
    df : pd.DataFrame
        ``total_sales`` 열을 타깃으로 사용하며 나머지 열은 특징으로 사용합니다.
    output_dir : Path
        모델과 학습 결과가 저장될 디렉터리.

    Returns
    -------
    xgboost.XGBRegressor
        최적 하이퍼파라미터로 학습된 모델.
    """

    if 'total_sales' not in df.columns:
        raise ValueError("DataFrame must contain 'total_sales' column as target")

    output_dir.mkdir(parents=True, exist_ok=True)

    X = df.drop(columns=['total_sales'])
    y = df['total_sales']

    def objective(trial: optuna.Trial) -> float:
        params: dict[str, Any] = {
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
            'max_depth': trial.suggest_int('max_depth', 3, 10),
            'n_estimators': trial.suggest_int('n_estimators', 50, 300),
            'subsample': trial.suggest_float('subsample', 0.5, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
            'objective': 'reg:squarederror',
            'random_state': 42,
        }

        X_train, X_valid, y_train, y_valid = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        model = xgboost.XGBRegressor(**params)
        model.fit(X_train, y_train)
        pred = model.predict(X_valid)
        return mean_squared_error(y_valid, pred)

    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=50, n_jobs=1)

    best_params = study.best_params
    best_model = xgboost.XGBRegressor(
        **best_params, objective='reg:squarederror', random_state=42
    )
    best_model.fit(X, y)

    model_path = output_dir / f"model_{mid_code}.pkl"
    study_path = output_dir / f"study_{mid_code}.pkl"
    joblib.dump(best_model, model_path)
    joblib.dump(study, study_path)
    log.info("Saved model to %s and study to %s", model_path, study_path)

    return best_model
