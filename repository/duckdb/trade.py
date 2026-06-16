"""repository/duckdb/trade.py"""
import pandas as pd
from typing import Optional
from ..interfaces import ITradeRepository

class DuckDBTradeRepository(ITradeRepository):
    def create_table(self) -> None:
        self._con.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_trade_id START 1;
            CREATE TABLE IF NOT EXISTS trade (
                id         INTEGER   PRIMARY KEY DEFAULT nextval('seq_trade_id'),
                team_id    INTEGER   NOT NULL,
                item_id    INTEGER   NOT NULL,
                quantity   INTEGER   NOT NULL CHECK (quantity > 0),
                unit_price INTEGER   NOT NULL CHECK (unit_price >= 0),
                traded_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES team (id),
                FOREIGN KEY (item_id) REFERENCES item (id)
            )
        """)
    def count(self) -> int:
        return self._con.execute("SELECT COUNT(*) FROM trade").fetchone()[0]
    def save(self, df: pd.DataFrame) -> int:
        self._con.execute("""
            INSERT INTO trade (team_id, item_id, quantity, unit_price)
            SELECT team_id, item_id, quantity, unit_price FROM df
        """)
        return int(self._con.execute("SELECT currval('seq_trade_id')").fetchone()[0])
    def find_by_id(self, trade_id: int) -> Optional[dict]:
        row = self._con.execute("SELECT * FROM trade WHERE id = ?", [trade_id]).fetchone()
        if row is None:
            return None
        return {"id": row[0], "team_id": row[1], "item_id": row[2],
                "quantity": row[3], "unit_price": row[4], "traded_at": row[5]}
    def find_by_team_id(self, team_id: int) -> pd.DataFrame:
        return self._con.execute("""
            SELECT t.id, t.team_id, t.item_id, i.name AS item_name,
                   t.quantity, t.unit_price, (t.quantity * t.unit_price) AS total_amount, t.traded_at
            FROM trade t INNER JOIN item i ON t.item_id = i.id
            WHERE t.team_id = ? ORDER BY t.traded_at DESC
        """, [team_id]).fetchdf()
    def count_all(self) -> int:
        return int(self._con.execute("SELECT COUNT(*) FROM trade").fetchone()[0])
    def delete_by_id(self, trade_id: int) -> bool:
        self._con.execute("DELETE FROM trade WHERE id = ?", [trade_id])
        return True
