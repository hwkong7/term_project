"""repository/duckdb/connection.py — DuckDB 커넥션 관리"""

import os
import duckdb
from dotenv import load_dotenv
from ..interfaces import IDatabaseManager

load_dotenv()


class DuckDBManager(IDatabaseManager):
    """DuckDB 커넥션 관리 클래스"""

    def __init__(self):
        self._db_path = os.getenv("DUCKDB_PATH", "data/bankruptcy.duckdb")
        self._con = None
        db_dir = os.path.dirname(self._db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        if self._con is None:
            try:
                self._con = duckdb.connect(self._db_path)
            except Exception as e:
                raise ConnectionError(f"[ERROR] DuckDB 연결 실패 (경로: {self._db_path}): {e}")
        return self._con

    def close(self) -> None:
        if self._con is not None:
            try:
                self._con.close()
            except Exception:
                pass
            finally:
                self._con = None
