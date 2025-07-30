"""데이터베이스 파일 존재 여부와 주요 테이블을 확인하는 스크립트."""

import argparse
import sqlite3
from pathlib import Path

from utils.config import DB_FILE
from utils.db_util import JUMEOKBAP_DB_PATH


def check_db(path: Path) -> None:
    """주어진 DB 경로의 파일과 테이블 존재 여부를 출력한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n[경로] {path}")
    if not path.exists():
        print("파일이 존재하지 않습니다.")
        return

    print("파일이 존재합니다.")
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        for table in ("mid_sales", "jumeokbap_predictions"):
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            exists = cursor.fetchone() is not None
            print(f" - 테이블 '{table}': {'존재' if exists else '없음'}")
        conn.close()
    except Exception as e:  # pragma: no cover - 단순 출력 스크립트
        print(f"DB 검사 중 오류 발생: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="DB 파일과 테이블을 확인합니다")
    parser.add_argument(
        "--db",
        choices=["integrated", "jumeokbap"],
        help="특정 DB만 확인합니다 (기본: 모두 확인)",
    )
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parent
    integrated_path = root_dir / DB_FILE

    if args.db in (None, "integrated"):
        check_db(integrated_path)
    if args.db in (None, "jumeokbap"):
        check_db(JUMEOKBAP_DB_PATH)


if __name__ == "__main__":
    main()
