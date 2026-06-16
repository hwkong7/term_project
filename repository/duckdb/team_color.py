"""repository/duckdb/team_color.py"""
import pandas as pd
from typing import Optional
from ..interfaces import ITeamColorRepository

class DuckDBTeamColorRepository(ITeamColorRepository):
    def create_table(self) -> None:
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS team_color (
                code VARCHAR PRIMARY KEY,
                hex_value VARCHAR NOT NULL
            )
        """)
    def count(self) -> int:
        return self._con.execute("SELECT COUNT(*) FROM team_color").fetchone()[0]
    def save(self, df: pd.DataFrame) -> None:
        self._con.execute("INSERT INTO team_color (code, hex_value) SELECT code, hex_value FROM df")
    def find_all(self) -> pd.DataFrame:
        return self._con.execute("SELECT * FROM team_color").fetchdf()
    def find_by_code(self, code: str) -> Optional[dict]:
        row = self._con.execute("SELECT * FROM team_color WHERE code = ?", [code]).fetchone()
        return None if row is None else {"code": row[0], "hex_value": row[1]}
