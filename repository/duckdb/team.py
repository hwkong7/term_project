"""
repository/duckdb/team.py
팀 DuckDB 구현체.

ITeamRepository 인터페이스를 구현한다.
team 테이블은 게임 참여 팀의 정보(이름, 색상, 잔액, HP)를 저장한다.

[핵심 메서드]
  add_balance()      : 아이템 판매 시 팀 잔액을 증가시킨다.
  subtract_balance() : 룰렛 패널티/스핀 비용 차감 시 잔액을 감소시킨다.
                       GREATEST(..., 0)으로 음수 방지.
  _recalc_hp()       : 잔액 변경 후 HP 비율을 재계산하는 내부 헬퍼.
                       hp_percent = ROUND(100 × current_balance / initial_balance)

[시퀀스]
  seq_team_id: 팀 등록 시 자동으로 부여되는 대리 키(Surrogate Key).
               create_table() 호출 시 IF NOT EXISTS로 안전하게 생성된다.
"""

import pandas as pd
from typing import Optional
from ..interfaces import ITeamRepository


class DuckDBTeamRepository(ITeamRepository):
    """team 테이블 DuckDB 구현체."""

    def create_table(self) -> None:
        """시퀀스와 team 테이블이 없으면 생성한다."""
        self._con.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_team_id START 1;

            CREATE TABLE IF NOT EXISTS team (
                id              INTEGER   PRIMARY KEY DEFAULT nextval('seq_team_id'),
                name            VARCHAR   NOT NULL UNIQUE,          -- 팀 이름 (중복 불가)
                color_code      VARCHAR   NOT NULL UNIQUE,          -- 팀 색상 코드 (중복 불가)
                slogan          VARCHAR,                            -- 슬로건
                icon_path       VARCHAR,                            -- 아이콘 경로 (선택)
                initial_balance INTEGER   NOT NULL CHECK (initial_balance > 0),  -- 초기 잔액
                current_balance INTEGER   NOT NULL,                 -- 현재 잔액
                hp_percent      INTEGER   NOT NULL DEFAULT 100
                                          CHECK (hp_percent BETWEEN 0 AND 100),  -- HP 비율
                registered_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (color_code) REFERENCES team_color (code)
            )
        """)

    def count(self) -> int:
        """team 테이블의 전체 행 수를 반환한다."""
        return self._con.execute("SELECT COUNT(*) FROM team").fetchone()[0]

    def save(self, df: pd.DataFrame) -> None:
        """
        팀 목록을 일괄 INSERT한다.
        id는 seq_team_id 시퀀스가 자동으로 부여하므로 INSERT에서 제외한다.
        """
        self._con.execute("""
            INSERT INTO team
                (name, color_code, slogan, icon_path, initial_balance, current_balance)
            SELECT name, color_code, slogan, icon_path, initial_balance, current_balance
            FROM df
        """)

    def find_by_id(self, team_id: int) -> Optional[dict]:
        """
        PK(id)로 팀 단건을 조회한다.
        team_color와 INNER JOIN하여 hex_value(HEX 색상값)를 포함한 딕셔너리를 반환한다.
        없으면 None을 반환한다.
        """
        row = self._con.execute("""
            SELECT t.id, t.name, t.color_code, tc.hex_value,
                   t.slogan, t.icon_path, t.initial_balance, t.current_balance, t.hp_percent
            FROM team t INNER JOIN team_color tc ON t.color_code = tc.code
            WHERE t.id = ?
        """, [team_id]).fetchone()
        if row is None:
            return None
        return {
            "id": row[0], "name": row[1], "color_code": row[2], "hex_value": row[3],
            "slogan": row[4], "icon_path": row[5],
            "initial_balance": row[6], "current_balance": row[7], "hp_percent": row[8],
        }

    def find_all(self) -> pd.DataFrame:
        """
        전체 팀 목록을 team_color와 INNER JOIN하여 반환한다.
        team_id 기준 오름차순으로 정렬된다.
        """
        return self._con.execute("""
            SELECT t.id, t.name, t.color_code, tc.hex_value,
                   t.slogan, t.icon_path, t.initial_balance, t.current_balance, t.hp_percent
            FROM team t INNER JOIN team_color tc ON t.color_code = tc.code ORDER BY t.id
        """).fetchdf()

    def exists_by_name(self, name: str) -> bool:
        """동일한 팀 이름이 이미 존재하는지 확인한다."""
        return self._con.execute(
            "SELECT COUNT(*) FROM team WHERE name = ?", [name]
        ).fetchone()[0] > 0

    def exists_by_color(self, color_code: str) -> bool:
        """동일한 색상 코드를 사용하는 팀이 이미 존재하는지 확인한다."""
        return self._con.execute(
            "SELECT COUNT(*) FROM team WHERE color_code = ?", [color_code]
        ).fetchone()[0] > 0

    def add_balance(self, team_id: int, amount: int) -> dict:
        """
        팀 잔액을 amount만큼 증가시킨다 (아이템 판매 수익 반영).
        갱신 후 _recalc_hp()로 HP를 재계산하고 최신 팀 정보를 반환한다.
        """
        self._con.execute(
            "UPDATE team SET current_balance = current_balance + ? WHERE id = ?",
            [amount, team_id],
        )
        self._recalc_hp(team_id)
        return self.find_by_id(team_id)

    def subtract_balance(self, team_id: int, amount: int) -> dict:
        """
        팀 잔액을 amount만큼 차감한다 (룰렛 스핀 비용 또는 패널티 반영).
        GREATEST(..., 0)으로 잔액이 음수가 되지 않도록 보장한다.
        갱신 후 _recalc_hp()로 HP를 재계산하고 최신 팀 정보를 반환한다.
        """
        self._con.execute("""
            UPDATE team
            SET current_balance = GREATEST(current_balance - ?, 0)
            WHERE id = ?
        """, [amount, team_id])
        self._recalc_hp(team_id)
        return self.find_by_id(team_id)

    def _recalc_hp(self, team_id: int) -> None:
        """
        HP 비율을 재계산하는 내부 헬퍼 메서드.
        hp_percent = ROUND(100 × current_balance / initial_balance)
        LEAST(100, GREATEST(0, ...))로 0~100 범위를 보장한다.
        """
        self._con.execute("""
            UPDATE team
            SET hp_percent = CAST(
                LEAST(100, GREATEST(0,
                    100.0 * current_balance / initial_balance)) AS INTEGER)
            WHERE id = ?
        """, [team_id])

    def update(self, df: pd.DataFrame) -> None:
        """DataFrame의 각 행에 대해 팀 정보를 UPDATE한다."""
        for _, r in df.iterrows():
            self._con.execute("""
                UPDATE team SET name=?, color_code=?, slogan=?, icon_path=?,
                    current_balance=?, hp_percent=? WHERE id=?
            """, [r["name"], r["color_code"], r["slogan"], r["icon_path"],
                  r["current_balance"], r["hp_percent"], r["id"]])

    def delete_by_id(self, team_id: int) -> bool:
        """PK(id)로 팀 1건을 DELETE한다."""
        self._con.execute("DELETE FROM team WHERE id = ?", [team_id])
        return True

    def delete_all(self) -> int:
        """
        FK 제약 순서에 따라 roulette_spin → trade → team 순으로 전체 삭제한다.
        새 게임 시작(reset_game_data) 시 호출되어 게임 데이터를 초기화한다.
        """
        self._con.execute("DELETE FROM roulette_spin")
        self._con.execute("DELETE FROM trade")
        self._con.execute("DELETE FROM team")
        return 0
