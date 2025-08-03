from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .model import run_all_category_predictions

log = logging.getLogger(__name__)


def run_for_db_paths(db_paths: list[Path]) -> None:
    """주어진 DB 경로들에 대해 순차적으로 예측을 실행합니다."""
    for db_path in db_paths:
        try:
            if not db_path.exists():
                log.error("DB 파일을 찾을 수 없습니다: %s", db_path)
                continue
            log.info("[%s] 예측 및 추천 실행 시작", db_path)
            run_all_category_predictions(db_path)
        except Exception:
            log.exception("[%s] 예측 실행 중 오류 발생", db_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="DB 경로별 카테고리 예측 실행 스크립트")
    parser.add_argument("db_paths", nargs="+", help="판매 데이터가 저장된 SQLite DB 파일 경로")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    log.info("카테고리 예측 스크립트 시작")
    run_for_db_paths([Path(p) for p in args.db_paths])
    log.info("카테고리 예측 스크립트 종료")


if __name__ == "__main__":
    main()
