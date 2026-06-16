"""repository/duckdb/roulette.py"""
import pandas as pd
from typing import Optional
from ..interfaces import IRouletteRepository

class DuckDBRouletteRepository(IRouletteRepository):
    def create_table(self) -> None:
        self._con.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_roulette_id START 1;
            CREATE TABLE IF NOT EXISTS roulette_spin (
                id               INTEGER   PRIMARY KEY DEFAULT nextval('seq_roulette_id'),
                spinner_team_id  INTEGER   NOT NULL,
                target_team_id   INTEGER   NOT NULL,
                penalty_amount   INTEGER   NOT NULL CHECK (penalty_amount >= 0),
                spin_cost        INTEGER   NOT NULL DEFAULT 100000,
                spun_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (spinner_team_id) REFERENCES team (id),
                FOREIGN KEY (target_team_id)  REFERENCES team (id)
            )
        """)
    def count(self) -> int:
        return self._con.execute("SELECT COUNT(*) FROM roulette_spin").fetchone()[0]
    def save(self, df: pd.DataFrame) -> int:
        self._con.execute("""
            INSERT INTO roulette_spin (spinner_team_id, target_team_id, penalty_amount, spin_cost)
            SELECT spinner_team_id, target_team_id, penalty_amount, spin_cost FROM df
        """)
        return int(self._con.execute("SELECT currval('seq_roulette_id')").fetchone()[0])
    def find_by_id(self, spin_id: int) -> Optional[dict]:
        row = self._con.execute("SELECT * FROM roulette_spin WHERE id = ?", [spin_id]).fetchone()
        if row is None:
            return None
        return {"id": row[0], "spinner_team_id": row[1], "target_team_id": row[2],
                "penalty_amount": row[3], "spin_cost": row[4], "spun_at": row[5]}
    def find_recent_with_team_names(self, limit: int = 3) -> pd.DataFrame:
        return self._con.execute("""
            SELECT r.id, r.spun_at,
                   s.name AS spinner_name, s.color_code AS spinner_color,
                   t.name AS target_name, t.color_code AS target_color,
                   r.penalty_amount
            FROM roulette_spin r
            INNER JOIN team s ON r.spinner_team_id = s.id
            INNER JOIN team t ON r.target_team_id  = t.id
            ORDER BY r.spun_at DESC LIMIT ?
        """, [limit]).fetchdf()
    def count_all(self) -> int:
        return int(self._con.execute("SELECT COUNT(*) FROM roulette_spin").fetchone()[0])
    def delete_by_id(self, spin_id: int) -> bool:
        self._con.execute("DELETE FROM roulette_spin WHERE id = ?", [spin_id])
        return True
