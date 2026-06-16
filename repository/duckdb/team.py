"""repository/duckdb/team.py"""
import pandas as pd
from typing import Optional
from ..interfaces import ITeamRepository

class DuckDBTeamRepository(ITeamRepository):
    def create_table(self) -> None:
        self._con.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_team_id START 1;
            CREATE TABLE IF NOT EXISTS team (
                id              INTEGER   PRIMARY KEY DEFAULT nextval('seq_team_id'),
                name            VARCHAR   NOT NULL UNIQUE,
                color_code      VARCHAR   NOT NULL UNIQUE,
                slogan          VARCHAR,
                icon_path       VARCHAR,
                initial_balance INTEGER   NOT NULL CHECK (initial_balance > 0),
                current_balance INTEGER   NOT NULL,
                hp_percent      INTEGER   NOT NULL DEFAULT 100
                                          CHECK (hp_percent BETWEEN 0 AND 100),
                registered_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (color_code) REFERENCES team_color (code)
            )
        """)
    def count(self) -> int:
        return self._con.execute("SELECT COUNT(*) FROM team").fetchone()[0]
    def save(self, df: pd.DataFrame) -> None:
        self._con.execute("""
            INSERT INTO team (name, color_code, slogan, icon_path, initial_balance, current_balance)
            SELECT name, color_code, slogan, icon_path, initial_balance, current_balance FROM df
        """)
    def find_by_id(self, team_id: int) -> Optional[dict]:
        row = self._con.execute("""
            SELECT t.id, t.name, t.color_code, tc.hex_value,
                   t.slogan, t.icon_path, t.initial_balance, t.current_balance, t.hp_percent
            FROM team t INNER JOIN team_color tc ON t.color_code = tc.code
            WHERE t.id = ?
        """, [team_id]).fetchone()
        if row is None:
            return None
        return {"id": row[0], "name": row[1], "color_code": row[2], "hex_value": row[3],
                "slogan": row[4], "icon_path": row[5],
                "initial_balance": row[6], "current_balance": row[7], "hp_percent": row[8]}
    def find_all(self) -> pd.DataFrame:
        return self._con.execute("""
            SELECT t.id, t.name, t.color_code, tc.hex_value,
                   t.slogan, t.icon_path, t.initial_balance, t.current_balance, t.hp_percent
            FROM team t INNER JOIN team_color tc ON t.color_code = tc.code ORDER BY t.id
        """).fetchdf()
    def exists_by_name(self, name: str) -> bool:
        return self._con.execute("SELECT COUNT(*) FROM team WHERE name = ?", [name]).fetchone()[0] > 0
    def exists_by_color(self, color_code: str) -> bool:
        return self._con.execute("SELECT COUNT(*) FROM team WHERE color_code = ?", [color_code]).fetchone()[0] > 0
    def add_balance(self, team_id: int, amount: int) -> dict:
        self._con.execute("UPDATE team SET current_balance = current_balance + ? WHERE id = ?", [amount, team_id])
        self._recalc_hp(team_id)
        return self.find_by_id(team_id)
    def subtract_balance(self, team_id: int, amount: int) -> dict:
        self._con.execute("""
            UPDATE team SET current_balance = GREATEST(current_balance - ?, 0) WHERE id = ?
        """, [amount, team_id])
        self._recalc_hp(team_id)
        return self.find_by_id(team_id)
    def _recalc_hp(self, team_id: int) -> None:
        self._con.execute("""
            UPDATE team SET hp_percent = CAST(
                LEAST(100, GREATEST(0, 100.0 * current_balance / initial_balance)) AS INTEGER)
            WHERE id = ?
        """, [team_id])
    def update(self, df: pd.DataFrame) -> None:
        for _, r in df.iterrows():
            self._con.execute("""
                UPDATE team SET name=?, color_code=?, slogan=?, icon_path=?,
                    current_balance=?, hp_percent=? WHERE id=?
            """, [r["name"], r["color_code"], r["slogan"], r["icon_path"],
                  r["current_balance"], r["hp_percent"], r["id"]])
    def delete_by_id(self, team_id: int) -> bool:
        self._con.execute("DELETE FROM team WHERE id = ?", [team_id])
        return True
    def delete_all(self) -> int:
        self._con.execute("DELETE FROM roulette_spin")
        self._con.execute("DELETE FROM trade")
        self._con.execute("DELETE FROM team")
        return 0
