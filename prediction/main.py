from __future__ import annotations

import argparse
import logging
import sqlite3
from pathlib import Path

import pandas as pd

from .model import (
    get_training_data_for_category,
    get_weather_data,
    run_all_category_predictions,
)

try:  # pragma: no cover - optuna/xgboost가 없을 경우를 대비
    from .optuna_tuner import tune_model
except Exception:  # pragma: no cover - 라이브러리 미설치 시
    tune_model = None

log = logging.getLogger(__name__)


def tune_all_models(db_path: Path, output_dir: Path) -> None:
    """주어진 DB에서 중분류별 모델을 튜닝합니다."""
    if tune_model is None:
        log.error("tune_model 함수를 불러올 수 없습니다. Optuna가 설치되어 있는지 확인하세요.")
        return

    with sqlite3.connect(db_path) as conn:
        mid_codes = pd.read_sql("SELECT DISTINCT mid_code FROM mid_sales", conn)[
            "mid_code"
        ].tolist()

    output_dir.mkdir(parents=True, exist_ok=True)

    for mid_code in mid_codes:
        try:
            training_df = get_training_data_for_category(db_path, mid_code)
            if training_df.empty:
                log.warning("[%s] 학습 데이터가 없어 튜닝을 건너뜁니다.", mid_code)
                continue
            weather_df = get_weather_data(training_df["date"].tolist())
            df = pd.merge(training_df, weather_df, on="date").drop(columns=["date"])
            tune_model(mid_code, df, output_dir)
            log.info("[%s] 모델 튜닝 성공", mid_code)
        except Exception:  # pragma: no cover - 실제 실행 시에만 호출
            log.exception("[%s] 모델 튜닝 실패", mid_code)


def run_for_db_paths(
    db_paths: list[Path], tune: bool = False, model_dir: Path | None = None
) -> None:
    """주어진 DB 경로들에 대해 순차적으로 예측을 실행합니다."""
    if model_dir is None:
        model_dir = Path("prediction") / "tuned_models"

    for db_path in db_paths:
        try:
            if not db_path.exists():
                log.error("DB 파일을 찾을 수 없습니다: %s", db_path)
                continue

            log.info("[%s] 예측 및 추천 실행 시작", db_path)

            if tune:
                log.info("[%s] 모델 튜닝 단계 시작", db_path)
                tune_all_models(db_path, model_dir / db_path.stem)

            run_all_category_predictions(db_path)
            log.info("[%s] 예측 및 추천 실행 완료", db_path)
        except Exception:
            log.exception("[%s] 예측 실행 중 오류 발생", db_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DB 경로별 카테고리 예측 실행 스크립트"
    )
    parser.add_argument(
        "db_paths", nargs="+", help="판매 데이터가 저장된 SQLite DB 파일 경로"
    )
    parser.add_argument(
        "--tune",
        action="store_true",
        help="예측 전에 중분류별 모델을 튜닝합니다.",
    )
    parser.add_argument(
        "--model-dir",
        default=Path("prediction") / "tuned_models",
        help="튜닝된 모델이 저장될 디렉터리",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    log.info("카테고리 예측 스크립트 시작")
    run_for_db_paths(
        [Path(p) for p in args.db_paths],
        tune=args.tune,
        model_dir=Path(args.model_dir),
    )
    log.info("카테고리 예측 스크립트 종료")


if __name__ == "__main__":
    main()
