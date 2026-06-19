"""
repository/duckdb/roulette.py
룰렛 스핀 기록 DuckDB 구현체.

IRouletteRepository 인터페이스를 구현한다.
roulette_spin 테이블은 룰렛 1회 실행마다 생성되는 스핀 기록을 저장한다.

[시퀀스]
  seq_roulette_id: 스핀 저장 시 자동으로 부여되는 대리 키(Surrogate Key).

[find_recent_with_team_names]
  roulette_spin ⨝ team(스피너) ⨝ team(타겟) 형태로 두 번 JOIN하여
  룰렛 화면의 '최근 결과' 섹션에 팀명과 색상 코드를 함께 반환한다.
  같은 테이블(team)을 두 별칭(s, t)으로 각각 JOIN하는 Self-Join 패턴을 사용한다.
"""

import pandas as pd
from typing import Optional
from ..interfaces import IRouletteRepository


class DuckDBRouletteRepository(IRouletteRepository):
    """roulette_spin 테이블 DuckDB 구현체."""

    def create_table(self) -> None:
        """시퀀스와 roulette_spin 테이블이 없으면 생성한다."""
        self._con.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_roulette_id START 1;

            CREATE TABLE IF NOT EXISTS roulette_spin (
                id               INTEGER   PRIMARY KEY DEFAULT nextval('seq_roulette_id'),
                spinner_team_id  INTEGER   NOT NULL,  -- 룰렛을 돌린 팀 (FK → team.id)
                target_team_id   INTEGER   NOT NULL,  -- 패널티를 받은 팀 (FK → team.id)
                penalty_amount   INTEGER   NOT NULL CHECK (penalty_amount >= 0),  -- 차감 금액
                spin_cost        INTEGER   NOT NULL DEFAULT 100000,  -- 스핀 비용
                spun_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (spinner_team_id) REFERENCES team (id),
                FOREIGN KEY (target_team_id)  REFERENCES team (id)
            )
        """)

    def count(self) -> int:
        """roulette_spin 테이블의 전체 행 수를 반환한다."""
        return self._con.execute("SELECT COUNT(*) FROM roulette_spin").fetchone()[0]

    def save(self, df: pd.DataFrame) -> int:
        """
        룰렛 스핀 1건을 INSERT하고 새로 부여된 spin_id를 반환한다.
        currval('seq_roulette_id')로 방금 INSERT된 행의 id를 조회한다.
        """
        self._con.execute("""
            INSERT INTO roulette_spin
                (spinner_team_id, target_team_id, penalty_amount, spin_cost)
            SELECT spinner_team_id, target_team_id, penalty_amount, spin_cost FROM df
        """)
        return int(self._con.execute("SELECT currval('seq_roulette_id')").fetchone()[0])

    def find_by_id(self, spin_id: int) -> Optional[dict]:
        """PK(id)로 스핀 단건을 조회한다. 없으면 None을 반환한다."""
        row = self._con.execute(
            "SELECT * FROM roulette_spin WHERE id = ?", [spin_id]
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0], "spinner_team_id": row[1], "target_team_id": row[2],
            "penalty_amount": row[3], "spin_cost": row[4], "spun_at": row[5],
        }

    def find_recent_with_team_names(self, limit: int = 3) -> pd.DataFrame:
        """
        최근 N건의 룰렛 결과를 spinner/target 팀명 및 색상 포함해서 반환한다.
        team 테이블을 s(스피너), t(타겟) 두 별칭으로 각각 INNER JOIN한다.
        spun_at 기준 최신순 정렬 후 LIMIT으로 건수를 제한한다.
        """
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
        """전체 스핀 횟수를 반환한다 (대시보드 ROULETTE SPINS 표시용)."""
        return int(self._con.execute("SELECT COUNT(*) FROM roulette_spin").fetchone()[0])

    def delete_by_id(self, spin_id: int) -> bool:
        """PK(id)로 스핀 1건을 DELETE한다."""
        self._con.execute("DELETE FROM roulette_spin WHERE id = ?", [spin_id])
        return True
