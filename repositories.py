"""
repositories.py
설계서 8장 Repository Interface 설계 + DuckDB 구현체.

인터페이스(I로 시작)는 DBMS 독립적인 추상 클래스이고,
DuckDB로 시작하는 클래스가 실제 구현체이다.
DBMS 교체 시 구현체만 새로 작성하면 된다.
"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
import duckdb


# ============================================================
# 8.1 IItemRepository (3.1 아이템 조회)
# ============================================================
class IItemRepository(ABC):
    @abstractmethod
    def save(self, df: pd.DataFrame): ...
    @abstractmethod
    def find_by_id(self, item_id: int) -> Optional[dict]: ...
    @abstractmethod
    def find_all(self) -> pd.DataFrame: ...
    @abstractmethod
    def find_by_category(self, category_name: str) -> pd.DataFrame: ...
    @abstractmethod
    def find_new_items(self) -> pd.DataFrame: ...
    @abstractmethod
    def find_custom_items(self) -> pd.DataFrame: ...
    @abstractmethod
    def save_one(
        self, name: str, category_name: str, price: int, image_path: "str | None"
    ) -> int: ...
    @abstractmethod
    def update(self, df: pd.DataFrame): ...
    @abstractmethod
    def delete_by_id(self, item_id: int) -> bool: ...


# 8.2 ITeamRepository (3.2 팀 등록 + 잔액 갱신)
class ITeamRepository(ABC):
    @abstractmethod
    def save(self, df: pd.DataFrame): ...
    @abstractmethod
    def find_by_id(self, team_id: int) -> Optional[dict]: ...
    @abstractmethod
    def find_all(self) -> pd.DataFrame: ...
    @abstractmethod
    def exists_by_name(self, name: str) -> bool: ...
    @abstractmethod
    def exists_by_color(self, color_code: str) -> bool: ...
    @abstractmethod
    def add_balance(self, team_id: int, amount: int) -> dict: ...
    @abstractmethod
    def subtract_balance(self, team_id: int, amount: int) -> dict: ...
    @abstractmethod
    def update(self, df: pd.DataFrame): ...
    @abstractmethod
    def delete_by_id(self, team_id: int) -> bool: ...
    @abstractmethod
    def delete_all(self) -> int: ...


# 8.3 ITradeRepository (3.3 상품 판매)
class ITradeRepository(ABC):
    @abstractmethod
    def save(self, df: pd.DataFrame) -> int: ...
    @abstractmethod
    def find_by_id(self, trade_id: int) -> Optional[dict]: ...
    @abstractmethod
    def find_by_team_id(self, team_id: int) -> pd.DataFrame: ...
    @abstractmethod
    def count_all(self) -> int: ...
    @abstractmethod
    def delete_by_id(self, trade_id: int) -> bool: ...


# 8.4 IRouletteRepository (3.4 룰렛 돌리기)
class IRouletteRepository(ABC):
    @abstractmethod
    def save(self, df: pd.DataFrame) -> int: ...
    @abstractmethod
    def find_by_id(self, spin_id: int) -> Optional[dict]: ...
    @abstractmethod
    def find_recent_with_team_names(self, limit: int = 3) -> pd.DataFrame: ...
    @abstractmethod
    def count_all(self) -> int: ...
    @abstractmethod
    def delete_by_id(self, spin_id: int) -> bool: ...


# 8.5 IHistoryQueryRepository (3.5 자금 흐름 Join) ★핵심★
class IHistoryQueryRepository(ABC):
    @abstractmethod
    def find_integrated_history_by_team(self, team_id: int) -> pd.DataFrame: ...
    @abstractmethod
    def find_integrated_history_by_team_and_type(
        self, team_id: int, event_type: str
    ) -> pd.DataFrame: ...


# 8.6 마스터 테이블 인터페이스
class ITeamColorRepository(ABC):
    @abstractmethod
    def save(self, df: pd.DataFrame): ...
    @abstractmethod
    def find_all(self) -> pd.DataFrame: ...
    @abstractmethod
    def find_by_code(self, code: str) -> Optional[dict]: ...


class ICategoryRepository(ABC):
    @abstractmethod
    def save(self, df: pd.DataFrame): ...
    @abstractmethod
    def find_all(self) -> pd.DataFrame: ...
    @abstractmethod
    def delete_by_name(self, name: str) -> bool: ...


# ============================================================
# DuckDB 구현체 — 6.3 유스케이스별 SQL
# ============================================================
class DuckDBTeamColorRepository(ITeamColorRepository):
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def save(self, df: pd.DataFrame):
        self.conn.execute(
            "INSERT INTO team_color (code, hex_value) SELECT code, hex_value FROM df"
        )

    def find_all(self) -> pd.DataFrame:
        return self.conn.execute("SELECT * FROM team_color").fetchdf()

    def find_by_code(self, code: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM team_color WHERE code = ?", [code]
        ).fetchone()
        return None if row is None else {"code": row[0], "hex_value": row[1]}


class DuckDBCategoryRepository(ICategoryRepository):
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def save(self, df: pd.DataFrame):
        self.conn.execute("INSERT INTO category (name) SELECT name FROM df")

    def find_all(self) -> pd.DataFrame:
        return self.conn.execute("SELECT * FROM category").fetchdf()

    def delete_by_name(self, name: str) -> bool:
        self.conn.execute("DELETE FROM category WHERE name = ?", [name])
        return True


class DuckDBItemRepository(IItemRepository):
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def save(self, df: pd.DataFrame):
        self.conn.execute(
            "INSERT INTO item (id, name, category_name, price, image_path, is_new) "
            "SELECT id, name, category_name, price, image_path, is_new FROM df"
        )

    def find_by_id(self, item_id: int) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT id, name, category_name, price, image_path, is_new "
            "FROM item WHERE id = ?",
            [item_id],
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "name": row[1],
            "category_name": row[2],
            "price": row[3],
            "image_path": row[4],
            "is_new": row[5],
        }

    def find_all(self) -> pd.DataFrame:
        # 6.3.1 item ⨝ category
        return self.conn.execute("""
            SELECT i.id, i.name, c.name AS category,
                   i.price, i.image_path, i.is_new
            FROM item i
            INNER JOIN category c ON i.category_name = c.name
            ORDER BY i.id
        """).fetchdf()

    def find_by_category(self, category_name: str) -> pd.DataFrame:
        return self.conn.execute(
            """
            SELECT i.id, i.name, c.name AS category,
                   i.price, i.image_path, i.is_new
            FROM item i
            INNER JOIN category c ON i.category_name = c.name
            WHERE i.category_name = ?
            ORDER BY i.id
        """,
            [category_name],
        ).fetchdf()

    def find_new_items(self) -> pd.DataFrame:
        return self.conn.execute("""
            SELECT i.id, i.name, c.name AS category,
                   i.price, i.image_path, i.is_new
            FROM item i
            INNER JOIN category c ON i.category_name = c.name
            WHERE i.is_new = TRUE
        """).fetchdf()

    def find_custom_items(self) -> pd.DataFrame:
        return self.conn.execute("""
            SELECT i.id, i.name, c.name AS category,
                   i.price, i.image_path, i.is_new
            FROM item i
            INNER JOIN category c ON i.category_name = c.name
            WHERE i.is_custom = TRUE
            ORDER BY i.id
        """).fetchdf()

    def save_one(
        self, name: str, category_name: str, price: int, image_path: "str | None"
    ) -> int:
        new_id = self.conn.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM item"
        ).fetchone()[0]
        self.conn.execute(
            "INSERT INTO item (id, name, category_name, price, image_path, is_new, is_custom) "
            "VALUES (?, ?, ?, ?, ?, FALSE, TRUE)",
            [new_id, name, category_name, price, image_path],
        )
        return int(new_id)

    def update(self, df: pd.DataFrame):
        for _, r in df.iterrows():
            self.conn.execute(
                "UPDATE item SET name=?, category_name=?, price=?, "
                "image_path=?, is_new=? WHERE id=?",
                [
                    r["name"],
                    r["category_name"],
                    r["price"],
                    r["image_path"],
                    r["is_new"],
                    r["id"],
                ],
            )

    def delete_by_id(self, item_id: int) -> bool:
        self.conn.execute("DELETE FROM item WHERE id = ?", [item_id])
        return True


class DuckDBTeamRepository(ITeamRepository):
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def save(self, df: pd.DataFrame):
        # 6.3.2 일괄 INSERT (id는 시퀀스 자동)
        self.conn.execute("""
            INSERT INTO team
                (name, color_code, slogan, icon_path,
                 initial_balance, current_balance)
            SELECT name, color_code, slogan, icon_path,
                   initial_balance, current_balance
            FROM df
        """)

    def find_by_id(self, team_id: int) -> Optional[dict]:
        row = self.conn.execute(
            """
            SELECT t.id, t.name, t.color_code, tc.hex_value,
                   t.slogan, t.icon_path,
                   t.initial_balance, t.current_balance, t.hp_percent
            FROM team t
            INNER JOIN team_color tc ON t.color_code = tc.code
            WHERE t.id = ?
        """,
            [team_id],
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "name": row[1],
            "color_code": row[2],
            "hex_value": row[3],
            "slogan": row[4],
            "icon_path": row[5],
            "initial_balance": row[6],
            "current_balance": row[7],
            "hp_percent": row[8],
        }

    def find_all(self) -> pd.DataFrame:
        return self.conn.execute("""
            SELECT t.id, t.name, t.color_code, tc.hex_value,
                   t.slogan, t.icon_path,
                   t.initial_balance, t.current_balance, t.hp_percent
            FROM team t
            INNER JOIN team_color tc ON t.color_code = tc.code
            ORDER BY t.id
        """).fetchdf()

    def exists_by_name(self, name: str) -> bool:
        return (
            self.conn.execute(
                "SELECT COUNT(*) FROM team WHERE name = ?", [name]
            ).fetchone()[0]
            > 0
        )

    def exists_by_color(self, color_code: str) -> bool:
        return (
            self.conn.execute(
                "SELECT COUNT(*) FROM team WHERE color_code = ?", [color_code]
            ).fetchone()[0]
            > 0
        )

    def add_balance(self, team_id: int, amount: int) -> dict:
        # 6.3.3 판매 시 잔액 증가
        self.conn.execute(
            "UPDATE team SET current_balance = current_balance + ? WHERE id = ?",
            [amount, team_id],
        )
        self._recalc_hp(team_id)
        return self.find_by_id(team_id)

    def subtract_balance(self, team_id: int, amount: int) -> dict:
        # 6.3.4 룰렛 시 잔액 차감
        self.conn.execute(
            """
            UPDATE team
            SET current_balance = GREATEST(current_balance - ?, 0)
            WHERE id = ?
        """,
            [amount, team_id],
        )
        self._recalc_hp(team_id)
        return self.find_by_id(team_id)

    def _recalc_hp(self, team_id: int):
        self.conn.execute(
            """
            UPDATE team
            SET hp_percent = CAST(
                LEAST(100, GREATEST(0,
                    100.0 * current_balance / initial_balance)) AS INTEGER)
            WHERE id = ?
        """,
            [team_id],
        )

    def update(self, df: pd.DataFrame):
        for _, r in df.iterrows():
            self.conn.execute(
                """
                UPDATE team SET name=?, color_code=?, slogan=?, icon_path=?,
                    current_balance=?, hp_percent=? WHERE id=?
            """,
                [
                    r["name"],
                    r["color_code"],
                    r["slogan"],
                    r["icon_path"],
                    r["current_balance"],
                    r["hp_percent"],
                    r["id"],
                ],
            )

    def delete_by_id(self, team_id: int) -> bool:
        self.conn.execute("DELETE FROM team WHERE id = ?", [team_id])
        return True

    def delete_all(self) -> int:
        self.conn.execute("DELETE FROM roulette_spin")
        self.conn.execute("DELETE FROM trade")
        self.conn.execute("DELETE FROM team")
        return 0


class DuckDBTradeRepository(ITradeRepository):
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def save(self, df: pd.DataFrame) -> int:
        self.conn.execute("""
            INSERT INTO trade (team_id, item_id, quantity, unit_price)
            SELECT team_id, item_id, quantity, unit_price FROM df
        """)
        return int(self.conn.execute("SELECT currval('seq_trade_id')").fetchone()[0])

    def find_by_id(self, trade_id: int) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM trade WHERE id = ?", [trade_id]
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "team_id": row[1],
            "item_id": row[2],
            "quantity": row[3],
            "unit_price": row[4],
            "traded_at": row[5],
        }

    def find_by_team_id(self, team_id: int) -> pd.DataFrame:
        return self.conn.execute(
            """
            SELECT t.id, t.team_id, t.item_id, i.name AS item_name,
                   t.quantity, t.unit_price,
                   (t.quantity * t.unit_price) AS total_amount, t.traded_at
            FROM trade t
            INNER JOIN item i ON t.item_id = i.id
            WHERE t.team_id = ?
            ORDER BY t.traded_at DESC
        """,
            [team_id],
        ).fetchdf()

    def count_all(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM trade").fetchone()[0])

    def delete_by_id(self, trade_id: int) -> bool:
        self.conn.execute("DELETE FROM trade WHERE id = ?", [trade_id])
        return True


class DuckDBRouletteRepository(IRouletteRepository):
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def save(self, df: pd.DataFrame) -> int:
        self.conn.execute("""
            INSERT INTO roulette_spin
                (spinner_team_id, target_team_id, penalty_amount, spin_cost)
            SELECT spinner_team_id, target_team_id, penalty_amount, spin_cost
            FROM df
        """)
        return int(self.conn.execute("SELECT currval('seq_roulette_id')").fetchone()[0])

    def find_by_id(self, spin_id: int) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM roulette_spin WHERE id = ?", [spin_id]
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "spinner_team_id": row[1],
            "target_team_id": row[2],
            "penalty_amount": row[3],
            "spin_cost": row[4],
            "spun_at": row[5],
        }

    def find_recent_with_team_names(self, limit: int = 3) -> pd.DataFrame:
        # 6.3.4 최근 룰렛 결과
        return self.conn.execute(
            """
            SELECT r.id, r.spun_at,
                   s.name AS spinner_name, s.color_code AS spinner_color,
                   t.name AS target_name, t.color_code AS target_color,
                   r.penalty_amount
            FROM roulette_spin r
            INNER JOIN team s ON r.spinner_team_id = s.id
            INNER JOIN team t ON r.target_team_id = t.id
            ORDER BY r.spun_at DESC
            LIMIT ?
        """,
            [limit],
        ).fetchdf()

    def count_all(self) -> int:
        return int(
            self.conn.execute("SELECT COUNT(*) FROM roulette_spin").fetchone()[0]
        )

    def delete_by_id(self, spin_id: int) -> bool:
        self.conn.execute("DELETE FROM roulette_spin WHERE id = ?", [spin_id])
        return True


class DuckDBHistoryQueryRepository(IHistoryQueryRepository):
    """★핵심★ 4개 테이블 JOIN + UNION ALL"""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def find_integrated_history_by_team(self, team_id: int) -> pd.DataFrame:
        # 6.3.5 trade⨝item + roulette_spin + roulette_spin⨝team
        return self.conn.execute(
            """
            SELECT 'TRADE' AS event_type, t.traded_at AS event_at,
                   i.name AS detail, t.quantity AS quantity,
                   (t.quantity * t.unit_price) AS amount
            FROM trade t
            INNER JOIN item i ON t.item_id = i.id
            WHERE t.team_id = ?

            UNION ALL

            SELECT 'ROULETTE_COST' AS event_type, r.spun_at AS event_at,
                   '직접 룰렛 돌림' AS detail, 1 AS quantity,
                   -r.spin_cost AS amount
            FROM roulette_spin r
            WHERE r.spinner_team_id = ?

            UNION ALL

            SELECT 'ROULETTE_LOSS' AS event_type, r.spun_at AS event_at,
                   s.name || '팀에게 당함' AS detail, 1 AS quantity,
                   -r.penalty_amount AS amount
            FROM roulette_spin r
            INNER JOIN team s ON r.spinner_team_id = s.id
            WHERE r.target_team_id = ?

            ORDER BY event_at DESC
        """,
            [team_id, team_id, team_id],
        ).fetchdf()

    def find_integrated_history_by_team_and_type(
        self, team_id: int, event_type: str
    ) -> pd.DataFrame:
        df = self.find_integrated_history_by_team(team_id)
        if event_type == "TRADE":
            return df[df["event_type"] == "TRADE"]
        if event_type == "ROULETTE":
            return df[df["event_type"].isin(["ROULETTE_COST", "ROULETTE_LOSS"])]
        return df


# ============================================================
# 시스템 이미지 Repository (미학 — DB에 이미지 경로 저장)
# ============================================================
class ISystemImageRepository(ABC):
    @abstractmethod
    def find_by_key(self, key: str) -> Optional[dict]: ...
    @abstractmethod
    def find_all(self) -> pd.DataFrame: ...


class DuckDBSystemImageRepository(ISystemImageRepository):
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def find_by_key(self, key: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT key, image_path, description FROM system_image WHERE key = ?", [key]
        ).fetchone()
        if row is None:
            return None
        return {"key": row[0], "image_path": row[1], "description": row[2]}

    def find_all(self) -> pd.DataFrame:
        return self.conn.execute("SELECT * FROM system_image").fetchdf()
