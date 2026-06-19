"""
repository/duckdb/trade.py
거래(판매) 기록 DuckDB 구현체.

ITradeRepository 인터페이스를 구현한다.
trade 테이블은 팀이 아이템을 판매할 때마다 생성되는 거래 기록을 저장한다.

[시퀀스]
  seq_trade_id: 거래 저장 시 자동으로 부여되는 대리 키(Surrogate Key).
  currval('seq_trade_id'): INSERT 직후 마지막으로 발급된 id를 조회한다.

[find_by_team_id]
  trade ⨝ item INNER JOIN으로 item_name, total_amount(수량 × 단가)를
  함께 반환한다. 자금 흐름 화면의 TRADE 이벤트 조회에 활용된다.
"""

import pandas as pd
from typing import Optional
from ..interfaces import ITradeRepository


class DuckDBTradeRepository(ITradeRepository):
    """trade 테이블 DuckDB 구현체."""

    def create_table(self) -> None:
        """시퀀스와 trade 테이블이 없으면 생성한다."""
        self._con.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_trade_id START 1;

            CREATE TABLE IF NOT EXISTS trade (
                id         INTEGER   PRIMARY KEY DEFAULT nextval('seq_trade_id'),
                team_id    INTEGER   NOT NULL,    -- 판매한 팀 (FK → team.id)
                item_id    INTEGER   NOT NULL,    -- 판매한 아이템 (FK → item.id)
                quantity   INTEGER   NOT NULL CHECK (quantity > 0),   -- 판매 수량
                unit_price INTEGER   NOT NULL CHECK (unit_price >= 0),-- 판매 단가
                traded_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES team (id),
                FOREIGN KEY (item_id) REFERENCES item (id)
            )
        """)

    def count(self) -> int:
        """trade 테이블의 전체 행 수를 반환한다."""
        return self._con.execute("SELECT COUNT(*) FROM trade").fetchone()[0]

    def save(self, df: pd.DataFrame) -> int:
        """
        거래 1건을 INSERT하고 새로 부여된 trade_id를 반환한다.
        currval('seq_trade_id')로 방금 INSERT된 행의 id를 조회한다.
        """
        self._con.execute("""
            INSERT INTO trade (team_id, item_id, quantity, unit_price)
            SELECT team_id, item_id, quantity, unit_price FROM df
        """)
        return int(self._con.execute("SELECT currval('seq_trade_id')").fetchone()[0])

    def find_by_id(self, trade_id: int) -> Optional[dict]:
        """PK(id)로 거래 단건을 조회한다. 없으면 None을 반환한다."""
        row = self._con.execute(
            "SELECT * FROM trade WHERE id = ?", [trade_id]
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0], "team_id": row[1], "item_id": row[2],
            "quantity": row[3], "unit_price": row[4], "traded_at": row[5],
        }

    def find_by_team_id(self, team_id: int) -> pd.DataFrame:
        """
        특정 팀의 전체 거래 내역을 item과 INNER JOIN하여 반환한다.
        total_amount(수량 × 단가)를 계산 컬럼으로 포함한다.
        traded_at 기준 최신순 정렬.
        """
        return self._con.execute("""
            SELECT t.id, t.team_id, t.item_id, i.name AS item_name,
                   t.quantity, t.unit_price,
                   (t.quantity * t.unit_price) AS total_amount, t.traded_at
            FROM trade t INNER JOIN item i ON t.item_id = i.id
            WHERE t.team_id = ? ORDER BY t.traded_at DESC
        """, [team_id]).fetchdf()

    def count_all(self) -> int:
        """전체 거래 건수를 반환한다 (대시보드 TOTAL TRADES 표시용)."""
        return int(self._con.execute("SELECT COUNT(*) FROM trade").fetchone()[0])

    def delete_by_id(self, trade_id: int) -> bool:
        """PK(id)로 거래 1건을 DELETE한다."""
        self._con.execute("DELETE FROM trade WHERE id = ?", [trade_id])
        return True
