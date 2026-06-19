"""
repository/duckdb/connection.py
DuckDB 커넥션 관리 클래스.

IDatabaseManager 인터페이스를 구현하며, .env의 DUCKDB_PATH를 읽어
DuckDB 파일에 연결한다.

[연결 전략]
최초 get_connection() 호출 시 연결을 맺고(Lazy Connection),
이후 호출에서는 동일한 커넥션 객체를 재사용한다.
이렇게 하면 불필요한 파일 I/O를 줄이고 동일 트랜잭션 컨텍스트를 유지할 수 있다.

[data 폴더 자동 생성]
DB 파일 경로(data/bankruptcy.duckdb)가 존재하지 않는 경우
os.makedirs()로 폴더를 자동 생성하여 첫 실행 시 오류를 방지한다.
"""

import os
import duckdb
from dotenv import load_dotenv
from ..interfaces import IDatabaseManager

# 환경 변수 로드 (.env → DUCKDB_PATH 등)
load_dotenv()


class DuckDBManager(IDatabaseManager):
    """
    DuckDB 커넥션 관리 클래스.

    IDatabaseManager를 구현하는 DuckDB 전용 커넥션 관리자.
    main.py의 AppContainer에서 단 한 번 생성되어 모든 Repository에 주입된다.
    """

    def __init__(self):
        # .env의 DUCKDB_PATH를 읽어오고, 없을 경우 기본값 사용
        self._db_path = os.getenv("DUCKDB_PATH", "data/bankruptcy.duckdb")
        self._con = None  # Lazy Connection: 최초 get_connection() 호출 시 연결

        # DB 파일이 위치할 data/ 폴더가 없으면 자동 생성
        db_dir = os.path.dirname(self._db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """
        현재 활성화된 DuckDB 커넥션을 반환한다.
        기존 연결이 없으면 새로 연결을 맺고, 있으면 기존 객체를 재사용한다.
        """
        if self._con is None:
            try:
                self._con = duckdb.connect(self._db_path)
            except Exception as e:
                raise ConnectionError(
                    f"[ERROR] DuckDB 연결 실패 (경로: {self._db_path}): {e}"
                )
        return self._con

    def close(self) -> None:
        """현재 열려 있는 DuckDB 커넥션을 종료한다."""
        if self._con is not None:
            try:
                self._con.close()
            except Exception:
                pass   # 이미 닫힌 경우 무시
            finally:
                self._con = None   # 참조 해제
