"""
repository/interfaces.py
Repository 인터페이스 정의 (파산게임 시뮬레이터).

[계층형 아키텍처에서의 역할]
이 파일은 데이터 저장소 계층(Repository Layer)의 추상 인터페이스를 정의한다.
인터페이스(I로 시작하는 클래스)는 DBMS에 독립적인 추상 클래스(ABC)이고,
실제 SQL을 실행하는 DuckDB 구현체는 repository/duckdb/ 폴더에 별도로 작성된다.

DBMS를 교체할 때는 인터페이스를 구현하는 새 폴더(mysql/, oracle/ 등)만 추가하면 되고,
이 파일과 service/ 계층은 수정하지 않아도 된다.

[인터페이스 계층 구조]
  IDatabaseManager           : DB 연결 관리 (연결 반환, 종료)
  IRepository                : 공통 기반 (연결 주입, 테이블 생성, 카디널리티)
    ├─ ITeamColorRepository  : 팀 색상 마스터
    ├─ ICategoryRepository   : 아이템 카테고리 마스터
    ├─ IItemRepository       : 아이템(상품)
    ├─ ITeamRepository       : 팀 (잔액·HP 갱신 포함)
    ├─ ITradeRepository      : 거래(판매) 기록
    └─ IRouletteRepository   : 룰렛 스핀 기록
  IHistoryQueryRepository    : 자금 흐름 통합 조회 (읽기 전용, IRepository 미상속)
  ISystemImageRepository     : 시스템 이미지 경로 (읽기 전용, IRepository 미상속)

[설계 원칙]
  - DIP(의존성 역전): Service 계층은 구현체가 아닌 이 인터페이스에만 의존한다.
  - OCP(개방-폐쇄): 새 DBMS를 추가할 때 기존 코드를 수정하지 않고 구현체만 추가한다.
  - LSP(리스코프 치환): 모든 구현체는 인터페이스를 완전히 대체할 수 있어야 한다.
"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


# ===========================================================
# 데이터베이스 연결 인터페이스
# ===========================================================

class IDatabaseManager(ABC):
    """
    데이터베이스 연결 관리 인터페이스.

    DuckDB, MySQL, Oracle 등 다양한 DBMS의 연결 객체를
    동일한 방식으로 관리하기 위한 추상 클래스.
    구현체(DuckDBManager 등)는 repository/duckdb/connection.py에 위치한다.
    """

    @abstractmethod
    def get_connection(self):
        """데이터베이스 커넥션 객체 반환. 최초 호출 시 연결을 맺고 이후 재사용한다."""
        ...

    @abstractmethod
    def close(self) -> None:
        """현재 활성화된 데이터베이스 커넥션을 닫는다."""
        ...


# ===========================================================
# 공통 레포지토리 인터페이스
# ===========================================================

class IRepository(ABC):
    """
    모든 Repository의 공통 기반 인터페이스.

    생성자에서 IDatabaseManager로부터 커넥션 객체를 주입받아 self._con에 저장한다.
    이후 모든 하위 구현체는 self._con을 통해 SQL을 실행한다.
    각 테이블 Repository는 반드시 create_table()과 count()를 구현해야 한다.
    """

    def __init__(self, db: IDatabaseManager):
        # IDatabaseManager 인터페이스를 통해 실제 커넥션 객체를 주입받음
        # Service나 main.py는 구체적인 DB 종류를 알 필요 없음 (DIP 적용)
        self._con = db.get_connection()

    @abstractmethod
    def create_table(self) -> None:
        """테이블이 없으면 생성한다 (IF NOT EXISTS 포함)."""
        ...

    @abstractmethod
    def count(self) -> int:
        """테이블의 전체 행 수(Cardinality)를 반환한다."""
        ...


# ===========================================================
# 각 테이블별 확장 인터페이스
# ===========================================================

class ITeamColorRepository(IRepository):
    """
    팀 색상 마스터 저장소 인터페이스.
    team_color 테이블에 대한 CRUD 추상 메서드를 정의한다.
    """

    @abstractmethod
    def save(self, df: pd.DataFrame) -> None:
        """팀 색상 데이터를 일괄 INSERT한다."""
        ...

    @abstractmethod
    def find_all(self) -> pd.DataFrame:
        """전체 팀 색상 목록을 반환한다."""
        ...

    @abstractmethod
    def find_by_code(self, code: str) -> Optional[dict]:
        """color_code로 단건 조회한다. 없으면 None을 반환한다."""
        ...


class ICategoryRepository(IRepository):
    """
    아이템 카테고리 마스터 저장소 인터페이스.
    category 테이블에 대한 CRUD 추상 메서드를 정의한다.
    """

    @abstractmethod
    def save(self, df: pd.DataFrame) -> None:
        """카테고리 데이터를 INSERT한다."""
        ...

    @abstractmethod
    def find_all(self) -> pd.DataFrame:
        """전체 카테고리 목록을 반환한다."""
        ...

    @abstractmethod
    def delete_by_name(self, name: str) -> bool:
        """카테고리명으로 1건을 삭제한다."""
        ...


class IItemRepository(IRepository):
    """
    아이템(상품) 저장소 인터페이스.
    item 테이블에 대한 CRUD 추상 메서드를 정의한다.
    거래소 화면에서 카테고리별 필터링, 커스텀 아이템 추가 등을 지원한다.
    """

    @abstractmethod
    def save(self, df: pd.DataFrame) -> None:
        """아이템 목록을 일괄 INSERT한다."""
        ...

    @abstractmethod
    def find_by_id(self, item_id: int) -> Optional[dict]:
        """PK(id)로 아이템 단건을 조회한다. 없으면 None을 반환한다."""
        ...

    @abstractmethod
    def find_all(self) -> pd.DataFrame:
        """전체 아이템 목록을 category와 JOIN해서 반환한다."""
        ...

    @abstractmethod
    def find_by_category(self, category_name: str) -> pd.DataFrame:
        """특정 카테고리의 아이템만 필터링해서 반환한다."""
        ...

    @abstractmethod
    def find_new_items(self) -> pd.DataFrame:
        """is_new=TRUE인 커스텀 추가 아이템만 반환한다."""
        ...

    @abstractmethod
    def save_one(self, name: str, category_name: str, price: int, image_path: "str | None") -> int:
        """커스텀 아이템 1건을 INSERT하고 새로 부여된 id를 반환한다."""
        ...

    @abstractmethod
    def update(self, df: pd.DataFrame) -> None:
        """아이템 정보를 UPDATE한다."""
        ...

    @abstractmethod
    def delete_by_id(self, item_id: int) -> bool:
        """PK(id)로 아이템 1건을 DELETE한다."""
        ...


class ITeamRepository(IRepository):
    """
    팀 저장소 인터페이스.
    team 테이블에 대한 CRUD 및 잔액·HP 갱신 추상 메서드를 정의한다.
    add_balance, subtract_balance는 판매·룰렛 시 잔액을 갱신하는 핵심 메서드다.
    """

    @abstractmethod
    def save(self, df: pd.DataFrame) -> None:
        """팀 목록을 일괄 INSERT한다. id는 시퀀스가 자동 부여한다."""
        ...

    @abstractmethod
    def find_by_id(self, team_id: int) -> Optional[dict]:
        """PK(id)로 팀 단건을 조회한다. team_color와 JOIN해서 반환한다."""
        ...

    @abstractmethod
    def find_all(self) -> pd.DataFrame:
        """전체 팀 목록을 team_color와 JOIN해서 반환한다."""
        ...

    @abstractmethod
    def exists_by_name(self, name: str) -> bool:
        """동일한 팀 이름이 이미 존재하는지 확인한다."""
        ...

    @abstractmethod
    def exists_by_color(self, color_code: str) -> bool:
        """동일한 색상 코드를 사용하는 팀이 이미 존재하는지 확인한다."""
        ...

    @abstractmethod
    def add_balance(self, team_id: int, amount: int) -> dict:
        """팀 잔액을 amount만큼 증가시키고 갱신된 팀 정보를 반환한다. HP도 재계산한다."""
        ...

    @abstractmethod
    def subtract_balance(self, team_id: int, amount: int) -> dict:
        """팀 잔액을 amount만큼 차감하고 갱신된 팀 정보를 반환한다. 0 미만 불가. HP도 재계산한다."""
        ...

    @abstractmethod
    def update(self, df: pd.DataFrame) -> None:
        """팀 정보를 UPDATE한다."""
        ...

    @abstractmethod
    def delete_by_id(self, team_id: int) -> bool:
        """PK(id)로 팀 1건을 DELETE한다."""
        ...

    @abstractmethod
    def delete_all(self) -> int:
        """FK 순서를 지켜 roulette_spin → trade → team 순으로 전체 삭제한다."""
        ...


class ITradeRepository(IRepository):
    """
    거래(판매) 기록 저장소 인터페이스.
    trade 테이블에 대한 CRUD 추상 메서드를 정의한다.
    """

    @abstractmethod
    def save(self, df: pd.DataFrame) -> int:
        """거래 1건을 INSERT하고 새로 부여된 trade_id를 반환한다."""
        ...

    @abstractmethod
    def find_by_id(self, trade_id: int) -> Optional[dict]:
        """PK(id)로 거래 단건을 조회한다. 없으면 None을 반환한다."""
        ...

    @abstractmethod
    def find_by_team_id(self, team_id: int) -> pd.DataFrame:
        """특정 팀의 전체 거래 내역을 item과 JOIN해서 반환한다."""
        ...

    @abstractmethod
    def count_all(self) -> int:
        """전체 거래 건수를 반환한다 (대시보드 TOTAL TRADES 표시용)."""
        ...

    @abstractmethod
    def delete_by_id(self, trade_id: int) -> bool:
        """PK(id)로 거래 1건을 DELETE한다."""
        ...


class IRouletteRepository(IRepository):
    """
    룰렛 스핀 기록 저장소 인터페이스.
    roulette_spin 테이블에 대한 CRUD 추상 메서드를 정의한다.
    """

    @abstractmethod
    def save(self, df: pd.DataFrame) -> int:
        """룰렛 스핀 1건을 INSERT하고 새로 부여된 spin_id를 반환한다."""
        ...

    @abstractmethod
    def find_by_id(self, spin_id: int) -> Optional[dict]:
        """PK(id)로 스핀 단건을 조회한다. 없으면 None을 반환한다."""
        ...

    @abstractmethod
    def find_recent_with_team_names(self, limit: int = 3) -> pd.DataFrame:
        """최근 N건의 룰렛 결과를 spinner/target 팀명 포함해서 반환한다."""
        ...

    @abstractmethod
    def count_all(self) -> int:
        """전체 스핀 횟수를 반환한다 (대시보드 ROULETTE SPINS 표시용)."""
        ...

    @abstractmethod
    def delete_by_id(self, spin_id: int) -> bool:
        """PK(id)로 스핀 1건을 DELETE한다."""
        ...


class IHistoryQueryRepository(ABC):
    """
    자금 흐름 통합 조회 저장소 인터페이스 ★핵심★.

    거래(trade)와 룰렛(roulette_spin) 이벤트를 통합하여
    팀별 자금 흐름을 시간 역순으로 조회하는 읽기 전용 인터페이스.

    IRepository를 상속하지 않는 이유:
      create_table(), count()가 필요 없는 읽기 전용 집계 뷰이기 때문.

    구현체(DuckDBHistoryQueryRepository)는
    trade⨝item UNION ALL roulette_spin×2 형태의 복합 쿼리를 사용한다.
    """

    def __init__(self, db: IDatabaseManager):
        # IDatabaseManager를 통해 커넥션을 주입받음
        self._con = db.get_connection()

    @abstractmethod
    def find_integrated_history_by_team(self, team_id: int) -> pd.DataFrame:
        """특정 팀의 전체 자금 흐름(거래+룰렛)을 최신순으로 반환한다."""
        ...

    @abstractmethod
    def find_integrated_history_by_team_and_type(
        self, team_id: int, event_type: str
    ) -> pd.DataFrame:
        """
        특정 팀의 자금 흐름을 이벤트 타입별로 필터링해서 반환한다.
        event_type: 'TRADE' | 'ROULETTE'
        """
        ...


class ISystemImageRepository(ABC):
    """
    시스템 이미지 경로 저장소 인터페이스.
    파산/우승 다이얼로그에 표시되는 이미지 경로를 조회하는 읽기 전용 인터페이스.
    IRepository를 상속하지 않는 이유: create_table(), count()가 불필요하기 때문.
    """

    def __init__(self, db: IDatabaseManager):
        self._con = db.get_connection()

    @abstractmethod
    def find_by_key(self, key: str) -> Optional[dict]:
        """key('WINNER', 'BANKRUPT' 등)로 이미지 경로 단건을 조회한다."""
        ...

    @abstractmethod
    def find_all(self) -> pd.DataFrame:
        """전체 시스템 이미지 목록을 반환한다."""
        ...
