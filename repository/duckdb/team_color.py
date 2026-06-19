"""
repository/duckdb/team_color.py
팀 색상 마스터 DuckDB 구현체.

ITeamColorRepository 인터페이스를 구현한다.
team_color 테이블은 6가지 색상 코드(YELLOW, BLUE 등)와
HEX 값을 저장하는 마스터 테이블이다.
최초 실행 시 FinanceService.initialize()에서 마스터 데이터가 INSERT된다.
"""

import pandas as pd
from typing import Optional
from ..interfaces import ITeamColorRepository


class DuckDBTeamColorRepository(ITeamColorRepository):
    """team_color 테이블 DuckDB 구현체."""

    def create_table(self) -> None:
        """team_color 테이블이 없으면 생성한다."""
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS team_color (
                code      VARCHAR PRIMARY KEY,  -- 색상 코드 (예: YELLOW)
                hex_value VARCHAR NOT NULL       -- HEX 색상값 (예: #D4A537)
            )
        """)

    def count(self) -> int:
        """team_color 테이블의 전체 행 수를 반환한다."""
        return self._con.execute("SELECT COUNT(*) FROM team_color").fetchone()[0]

    def save(self, df: pd.DataFrame) -> None:
        """
        팀 색상 데이터를 일괄 INSERT한다.
        DuckDB의 'FROM df' 문법으로 pandas DataFrame을 직접 참조하여 삽입한다.
        """
        self._con.execute(
            "INSERT INTO team_color (code, hex_value) SELECT code, hex_value FROM df"
        )

    def find_all(self) -> pd.DataFrame:
        """전체 팀 색상 목록을 DataFrame으로 반환한다."""
        return self._con.execute("SELECT * FROM team_color").fetchdf()

    def find_by_code(self, code: str) -> Optional[dict]:
        """
        color_code로 단건 조회한다.
        없으면 None을 반환하고, 있으면 {'code': ..., 'hex_value': ...} 딕셔너리를 반환한다.
        """
        row = self._con.execute(
            "SELECT * FROM team_color WHERE code = ?", [code]
        ).fetchone()
        return None if row is None else {"code": row[0], "hex_value": row[1]}
