import logging
from pathlib import Path
from typing import Any

import joblib
import optuna
import pandas as pd
import xgboost
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split

from prediction import monitor

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def should_retrain(mid_code: str, prediction_db_path: Path, threshold: float) -> bool:
    """최근 성능 기준으로 재학습 여부를 판단합니다.

    ``monitor.load_recent_performance``로부터 최근 오차율을 불러와
    평균값이 ``threshold`` 이상이면 ``True``를 반환합니다.
    데이터가 없거나 조회에 실패하면 재학습이 필요하다고 간주합니다.
    """

    try:
        df = monitor.load_recent_performance(prediction_db_path, mid_code)
    except Exception as e:  # pragma: no cover - 예외는 로깅만
        log.debug("[%s] 최근 성능을 불러오지 못했습니다: %s", mid_code, e)
        return True

    if df.empty:
        log.debug("[%s] 최근 성능 데이터가 없어 재학습합니다.", mid_code)
        return True

    mean_error = df["error_rate_percent"].mean()
    log.debug("[%s] 평균 오차율: %.2f%%", mid_code, mean_error)
    return mean_error >= threshold


def tune_model(
    mid_code: str,
    df: pd.DataFrame,
    output_dir: Path,
    prediction_db_path: Path,
    error_threshold: float,
) -> xgboost.XGBRegressor:
    """Optuna로 XGBoost 모델 하이퍼파라미터 튜닝 후 저장합니다.

    Parameters
    ----------
    mid_code : str
        중분류 코드.
    df : pd.DataFrame
        ``total_sales`` 열을 타깃으로 사용하며 나머지 열은 특징으로 사용합니다.
    output_dir : Path
        모델과 학습 결과가 저장될 디렉터리.
    prediction_db_path : Path
        예측 및 성능 기록이 저장된 DB 경로.
    error_threshold : float
        최근 평균 오차율이 이 값 이상일 때만 재학습을 수행합니다.

    Returns
    -------
    xgboost.XGBRegressor
        최적 하이퍼파라미터로 학습된 모델.
    """

    if 'total_sales' not in df.columns:
        raise ValueError("DataFrame must contain 'total_sales' column as target")

    model_path = output_dir / f"model_{mid_code}.pkl"

    # 재학습 필요 여부 확인
    if not should_retrain(mid_code, prediction_db_path, error_threshold):
        if model_path.exists():
            log.info(
                "[%s] 최근 오차율이 기준 미만으로 기존 모델을 사용합니다.", mid_code
            )
            return joblib.load(model_path)
        log.info("[%s] 기존 모델이 없어 재학습을 진행합니다.", mid_code)

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

    study_path = output_dir / f"study_{mid_code}.pkl"
    joblib.dump(best_model, model_path)
    joblib.dump(study, study_path)
    log.info("Saved model to %s and study to %s", model_path, study_path)

    # 성능 로그 갱신
    store_name = prediction_db_path.stem.replace("category_predictions_", "")
    sales_db_path = prediction_db_path.parent / f"{store_name}.db"
    try:  # pragma: no cover - 실제 파일이 없을 수 있음
        monitor.update_performance_log(sales_db_path, prediction_db_path)
    except Exception as e:  # pragma: no cover - 로그만 남김
        log.debug("[%s] 성능 로그 갱신 실패: %s", mid_code, e)

    return best_model
