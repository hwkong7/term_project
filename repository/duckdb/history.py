"""repository/duckdb/history.py — ★핵심★ 4개 테이블 JOIN + UNION ALL"""
import pandas as pd
from ..interfaces import IHistoryQueryRepository

class DuckDBHistoryQueryRepository(IHistoryQueryRepository):
    def find_integrated_history_by_team(self, team_id: int) -> pd.DataFrame:
        return self._con.execute("""
            SELECT 'TRADE' AS event_type, t.traded_at AS event_at,
                   i.name AS detail, t.quantity AS quantity,
                   (t.quantity * t.unit_price) AS amount
            FROM trade t INNER JOIN item i ON t.item_id = i.id
            WHERE t.team_id = ?
            UNION ALL
            SELECT 'ROULETTE_COST' AS event_type, r.spun_at AS event_at,
                   '직접 룰렛 돌림' AS detail, 1 AS quantity,
                   -r.spin_cost AS amount
            FROM roulette_spin r WHERE r.spinner_team_id = ?
            UNION ALL
            SELECT 'ROULETTE_LOSS' AS event_type, r.spun_at AS event_at,
                   s.name || '팀에게 당함' AS detail, 1 AS quantity,
                   -r.penalty_amount AS amount
            FROM roulette_spin r INNER JOIN team s ON r.spinner_team_id = s.id
            WHERE r.target_team_id = ?
            ORDER BY event_at DESC
        """, [team_id, team_id, team_id]).fetchdf()

    def find_integrated_history_by_team_and_type(self, team_id: int, event_type: str) -> pd.DataFrame:
        df = self.find_integrated_history_by_team(team_id)
        if event_type == "TRADE":
            return df[df["event_type"] == "TRADE"]
        if event_type == "ROULETTE":
            return df[df["event_type"].isin(["ROULETTE_COST", "ROULETTE_LOSS"])]
        return df
