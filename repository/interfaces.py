"""
repository/interfaces.py
Repository 인터페이스 정의 (파산게임 시뮬레이터).

인터페이스(I로 시작)는 DBMS 독립적인 추상 클래스이고,
DuckDB로 시작하는 클래스가 실제 구현체이다.
DBMS 교체 시 구현체만 새로 작성하면 된다.
"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class IDatabaseManager(ABC):
    """데이터베이스 연결 관리 인터페이스"""

    @abstractmethod
    def get_connection(self): ...

    @abstractmethod
    def close(self) -> None: ...


class IRepository(ABC):
    """공통 인터페이스 — 커넥션 주입 + 테이블 생성 + 카디널리티"""

    def __init__(self, db: IDatabaseManager):
        self._con = db.get_connection()

    @abstractmethod
    def create_table(self) -> None: ...

    @abstractmethod
    def count(self) -> int: ...


class ITeamColorRepository(IRepository):
    @abstractmethod
    def save(self, df: pd.DataFrame) -> None: ...
    @abstractmethod
    def find_all(self) -> pd.DataFrame: ...
    @abstractmethod
    def find_by_code(self, code: str) -> Optional[dict]: ...


class ICategoryRepository(IRepository):
    @abstractmethod
    def save(self, df: pd.DataFrame) -> None: ...
    @abstractmethod
    def find_all(self) -> pd.DataFrame: ...
    @abstractmethod
    def delete_by_name(self, name: str) -> bool: ...


class IItemRepository(IRepository):
    @abstractmethod
    def save(self, df: pd.DataFrame) -> None: ...
    @abstractmethod
    def find_by_id(self, item_id: int) -> Optional[dict]: ...
    @abstractmethod
    def find_all(self) -> pd.DataFrame: ...
    @abstractmethod
    def find_by_category(self, category_name: str) -> pd.DataFrame: ...
    @abstractmethod
    def find_new_items(self) -> pd.DataFrame: ...
    @abstractmethod
    def save_one(self, name: str, category_name: str, price: int, image_path: "str | None") -> int: ...
    @abstractmethod
    def update(self, df: pd.DataFrame) -> None: ...
    @abstractmethod
    def delete_by_id(self, item_id: int) -> bool: ...


class ITeamRepository(IRepository):
    @abstractmethod
    def save(self, df: pd.DataFrame) -> None: ...
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
    def update(self, df: pd.DataFrame) -> None: ...
    @abstractmethod
    def delete_by_id(self, team_id: int) -> bool: ...
    @abstractmethod
    def delete_all(self) -> int: ...


class ITradeRepository(IRepository):
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


class IRouletteRepository(IRepository):
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


class IHistoryQueryRepository(ABC):
    """★핵심★ — IRepository 미상속 (create_table/count 불필요한 읽기 전용)"""

    def __init__(self, db: IDatabaseManager):
        self._con = db.get_connection()

    @abstractmethod
    def find_integrated_history_by_team(self, team_id: int) -> pd.DataFrame: ...

    @abstractmethod
    def find_integrated_history_by_team_and_type(
        self, team_id: int, event_type: str
    ) -> pd.DataFrame: ...


class ISystemImageRepository(ABC):
    def __init__(self, db: IDatabaseManager):
        self._con = db.get_connection()

    @abstractmethod
    def find_by_key(self, key: str) -> Optional[dict]: ...

    @abstractmethod
    def find_all(self) -> pd.DataFrame: ...
