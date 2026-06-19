"""
service/finance_service.py
비즈니스 로직 계층.

[계층형 아키텍처에서의 역할]
Service 계층은 Controller(main.py)와 Repository 계층 사이에 위치하며
게임 규칙(비즈니스 로직)을 담당한다.
SQL을 직접 작성하지 않고 Repository 인터페이스의 메서드만 호출한다.
이를 통해 DBMS가 교체되어도 이 파일은 수정하지 않아도 된다.

[서비스 클래스 구성]
  TeamService         : 팀 등록, 색상 조회, 유효성 검사
  ItemService         : 아이템 조회, 커스텀 아이템 추가
  TradeService        : 아이템 판매 처리 (잔액 증가 포함)
  RouletteService     : 룰렛 스핀 실행 (타겟 선정, 패널티 차감)
  HistoryService      : 팀별 자금 흐름 이력 조회
  DashboardService    : 대시보드 집계 데이터(거래수, 스핀수, 총 잔액) 제공
  FinanceService      : DB 초기화 및 게임 데이터 리셋 (main.py AppContainer용)

[예외 클래스]
  TeamRegistrationError: 팀 등록 유효성 검사 실패
  TradeError           : 판매 비즈니스 규칙 위반
  RouletteError        : 룰렛 비즈니스 규칙 위반

[상수]
  SPIN_COST       : 룰렛 1회 스핀 비용 (₩100,000)
  PENALTY_AMOUNTS : 룰렛 패널티 금액 후보 목록
"""

import random
from typing import List, Optional
import pandas as pd

from repository.interfaces import (
    ITeamRepository,
    ITeamColorRepository,
    IItemRepository,
    ICategoryRepository,
    ITradeRepository,
    IRouletteRepository,
    IHistoryQueryRepository,
)


# ===========================================================
# 3.2 TeamService
# ===========================================================

class TeamRegistrationError(Exception):
    """팀 등록 유효성 검사 실패 예외 (팀 수 초과, 이름 중복, 잔액 오류 등)."""
    pass


class TeamService:
    """
    팀 등록 및 색상 조회 서비스.

    ITeamRepository와 ITeamColorRepository에만 의존하며
    팀 등록 시 다양한 유효성 검사(팀 수, 이름 중복, 색상 중복, 잔액)를 수행한다.
    """

    def __init__(self, team_repo: ITeamRepository, color_repo: ITeamColorRepository):
        # Repository 인터페이스를 생성자로 주입받음 (DI 패턴)
        self.team_repo = team_repo
        self.color_repo = color_repo

    def create_teams(self, teams_data: List[dict]) -> pd.DataFrame:
        """
        팀 목록을 등록한다.
        유효성 검사 통과 후 기존 팀이 있으면 전체 삭제 후 재등록한다.
        등록된 전체 팀 DataFrame을 반환한다.
        """
        self._validate_input(teams_data)
        valid_colors = self.color_repo.find_all()["code"].tolist()
        for t in teams_data:
            if t["color_code"] not in valid_colors:
                raise TeamRegistrationError(
                    f"유효하지 않은 색상 코드: {t['color_code']}"
                )
        self._validate_no_duplicates(teams_data)

        # 기존 게임 데이터가 있으면 초기화 후 재등록
        if len(self.team_repo.find_all()) > 0:
            self.team_repo.delete_all()

        df = pd.DataFrame([
            {
                "name": t["name"],
                "color_code": t["color_code"],
                "slogan": t.get("slogan", ""),
                "icon_path": t.get("icon_path"),
                "initial_balance": t["initial_balance"],
                "current_balance": t["initial_balance"],  # 초기 잔액 = 현재 잔액
            }
            for t in teams_data
        ])
        self.team_repo.save(df)
        return self.team_repo.find_all()

    def _validate_input(self, teams_data: List[dict]):
        """
        팀 등록 입력값의 기본 유효성을 검사한다.
        팀 수(2~6), 이름 공백 여부, 색상 선택 여부, 잔액 형식 및 범위를 확인한다.
        """
        if not teams_data or len(teams_data) < 2:
            raise TeamRegistrationError("최소 2팀이 필요합니다.")
        if len(teams_data) > 6:
            raise TeamRegistrationError("최대 6팀까지 등록 가능합니다.")
        for i, t in enumerate(teams_data, start=1):
            if not t.get("name", "").strip():
                raise TeamRegistrationError(f"팀 {i}의 이름이 비어 있습니다.")
            if not t.get("color_code"):
                raise TeamRegistrationError(f"팀 {i}의 색상이 선택되지 않았습니다.")
            try:
                balance = int(t.get("initial_balance", 0))
            except (TypeError, ValueError):
                raise TeamRegistrationError(f"팀 {i}의 초기 잔액이 숫자가 아닙니다.")
            if balance < 1:
                raise TeamRegistrationError(
                    f"팀 {i}의 초기 잔액은 1원 이상이어야 합니다."
                )

    def _validate_no_duplicates(self, teams_data: List[dict]):
        """팀 이름 중복 및 색상 중복 여부를 검사한다."""
        names = [t["name"].strip() for t in teams_data]
        colors = [t["color_code"] for t in teams_data]
        if len(set(names)) != len(names):
            raise TeamRegistrationError("팀 이름이 중복되었습니다.")
        if len(set(colors)) != len(colors):
            raise TeamRegistrationError("팀 색상이 중복되었습니다.")

    def find_all_teams(self) -> pd.DataFrame:
        """전체 팀 목록을 반환한다."""
        return self.team_repo.find_all()

    def find_all_colors(self) -> pd.DataFrame:
        """전체 팀 색상 마스터 목록을 반환한다 (팀 등록 화면 색상 선택용)."""
        return self.color_repo.find_all()


# ===========================================================
# 3.1 ItemService
# ===========================================================

class ItemService:
    """
    아이템 조회 및 커스텀 아이템 추가 서비스.

    거래소 화면의 카테고리 탭 전환 및 커스텀 아이템 추가 기능을 담당한다.
    category_repo는 views/marketplace.py에서 카테고리 목록을 직접 조회할 때도 사용된다.
    """

    def __init__(self, item_repo: IItemRepository, category_repo: ICategoryRepository):
        self.item_repo = item_repo
        self.category_repo = category_repo  # 거래소 NEW 탭 폼에서 직접 접근

    def find_items(self, category_filter: Optional[str] = None) -> pd.DataFrame:
        """
        카테고리 필터에 따라 아이템 목록을 반환한다.
          '전체' 또는 None → 전체 아이템
          'NEW'            → 커스텀 추가 아이템만
          그 외(예: '광물') → 해당 카테고리 아이템
        """
        if category_filter is None or category_filter == "전체":
            return self.item_repo.find_all()
        if category_filter == "NEW":
            return self.item_repo.find_new_items()
        return self.item_repo.find_by_category(category_filter)

    def find_by_id(self, item_id: int) -> Optional[dict]:
        """PK(id)로 아이템 단건을 조회한다."""
        return self.item_repo.find_by_id(item_id)

    def add_custom_item(
        self, name: str, category_name: str, price: int, image_path: Optional[str]
    ) -> int:
        """
        커스텀 아이템을 추가한다.
        이름 공백, 음수 가격, 존재하지 않는 카테고리를 검사한 후 저장한다.
        새로 부여된 아이템 id를 반환한다.
        """
        if not name.strip():
            raise ValueError("아이템 이름이 비어 있습니다.")
        if price < 0:
            raise ValueError("가격은 0 이상이어야 합니다.")
        cats = self.category_repo.find_all()["name"].tolist()
        if category_name not in cats:
            raise ValueError(f"존재하지 않는 카테고리: {category_name}")
        return self.item_repo.save_one(name.strip(), category_name, price, image_path)

    def find_new_items(self) -> pd.DataFrame:
        """커스텀 추가 아이템 목록을 반환한다."""
        return self.item_repo.find_new_items()


# ===========================================================
# 3.3 TradeService
# ===========================================================

class TradeError(Exception):
    """판매 비즈니스 규칙 위반 예외 (수량 오류, 존재하지 않는 아이템 등)."""
    pass


class TradeService:
    """
    아이템 판매 거래 처리 서비스.

    거래 1건을 DB에 저장하고, 판매 수익(수량 × 단가)을 팀 잔액에 반영한다.
    IItemRepository, ITradeRepository, ITeamRepository 세 개의 인터페이스를 사용한다.
    """

    def __init__(
        self,
        item_repo: IItemRepository,
        trade_repo: ITradeRepository,
        team_repo: ITeamRepository,
    ):
        self.item_repo = item_repo
        self.trade_repo = trade_repo
        self.team_repo = team_repo

    def create_trade(self, team_id: int, item_id: int, quantity: int) -> dict:
        """
        아이템 판매 거래를 처리한다.
        1. 수량 유효성 검사 (1 이상)
        2. 아이템 존재 여부 확인
        3. trade 테이블에 거래 기록 저장
        4. 팀 잔액에 판매 수익(수량 × 단가) 반영
        5. 거래 결과 딕셔너리 반환
        """
        if quantity < 1:
            raise TradeError("판매 수량은 1 이상이어야 합니다.")
        item = self.item_repo.find_by_id(item_id)
        if item is None:
            raise TradeError(f"존재하지 않는 아이템: id={item_id}")
        unit_price = int(item["price"])
        trade_df = pd.DataFrame([{
            "team_id": team_id, "item_id": item_id,
            "quantity": quantity, "unit_price": unit_price,
        }])
        trade_id = self.trade_repo.save(trade_df)
        total = quantity * unit_price
        updated_team = self.team_repo.add_balance(team_id, total)
        return {
            "trade_id": trade_id, "item_name": item["name"],
            "quantity": quantity, "unit_price": unit_price,
            "total_amount": total, "team": updated_team,
        }

    def count_all_trades(self) -> int:
        """전체 거래 건수를 반환한다."""
        return self.trade_repo.count_all()


# ===========================================================
# 3.4 RouletteService
# ===========================================================

class RouletteError(Exception):
    """룰렛 비즈니스 규칙 위반 예외 (팀 수 부족, 잔액 부족, 생존 팀 없음 등)."""
    pass


# 룰렛 관련 게임 규칙 상수
SPIN_COST = 100_000        # 룰렛 1회 스핀 비용: ₩100,000
PENALTY_AMOUNTS = [        # 룰렛 패널티 금액 후보 목록 (무작위 선정)
    500_000, 800_000, 1_000_000, 1_500_000, 2_000_000, 2_500_000, 3_000_000
]


class RouletteService:
    """
    룰렛 스핀 실행 서비스.

    스핀 비용(SPIN_COST)을 스피너 팀에서 차감하고,
    생존 팀(잔액 > 0) 중 무작위로 타겟을 선정하여 패널티를 부과한다.
    rng(random.Random)를 생성자 주입으로 받아 테스트 시 결과를 고정할 수 있다.
    """

    def __init__(
        self,
        roulette_repo: IRouletteRepository,
        team_repo: ITeamRepository,
        rng: random.Random = None,
    ):
        self.roulette_repo = roulette_repo
        self.team_repo = team_repo
        self.rng = rng or random.Random()  # 기본값: 새 Random 인스턴스

    def execute_spin(self, spinner_team_id: int) -> dict:
        """
        룰렛 스핀 1회를 실행한다.

        처리 순서:
          1. 팀 수 검사 (2팀 이상 필요)
          2. 스피너 팀 존재 및 잔액 검사 (SPIN_COST 이상 필요)
          3. 파산팀(잔액 <= 0) 제외 후 생존 팀 목록에서 타겟 무작위 선정
          4. 패널티 금액 무작위 선정
          5. roulette_spin 테이블에 스핀 기록 저장
          6. 스피너 잔액에서 SPIN_COST 차감
          7. 타겟 잔액에서 penalty_amount 차감
          8. 결과 딕셔너리 반환
        """
        teams = self.team_repo.find_all()
        if len(teams) < 2:
            raise RouletteError("최소 2팀이 등록되어 있어야 합니다.")
        spinner = self.team_repo.find_by_id(spinner_team_id)
        if spinner is None:
            raise RouletteError(f"존재하지 않는 팀: id={spinner_team_id}")
        if spinner["current_balance"] < SPIN_COST:
            raise RouletteError("룰렛 비용(₩100,000)이 부족합니다.")

        # 파산팀(잔액 <= 0) 제외 — 생존 팀만 타겟 후보로 포함
        alive_teams = teams[teams["current_balance"] > 0]
        if len(alive_teams) < 1:
            raise RouletteError("생존 팀이 없습니다.")
        team_ids = alive_teams["id"].tolist()
        target_team_id = int(self.rng.choice(team_ids))   # 무작위 타겟 선정
        penalty_amount = self.rng.choice(PENALTY_AMOUNTS)  # 무작위 패널티 선정

        # 스핀 기록 저장
        spin_df = pd.DataFrame([{
            "spinner_team_id": spinner_team_id,
            "target_team_id": target_team_id,
            "penalty_amount": penalty_amount,
            "spin_cost": SPIN_COST,
        }])
        spin_id = self.roulette_repo.save(spin_df)

        # 잔액 차감
        self.team_repo.subtract_balance(spinner_team_id, SPIN_COST)
        updated_target = self.team_repo.subtract_balance(target_team_id, penalty_amount)

        return {
            "spin_id": spin_id,
            "spinner_team_id": spinner_team_id,
            "target_team_id": target_team_id,
            "target_name": updated_target["name"],
            "target_color": updated_target["color_code"],
            "penalty_amount": penalty_amount,
            "spin_cost": SPIN_COST,
        }

    def find_recent_results(self, limit: int = 3) -> pd.DataFrame:
        """최근 룰렛 결과 N건을 팀명 포함해서 반환한다."""
        return self.roulette_repo.find_recent_with_team_names(limit)

    def count_all_spins(self) -> int:
        """전체 스핀 횟수를 반환한다."""
        return self.roulette_repo.count_all()


# ===========================================================
# 3.5 HistoryService
# ===========================================================

class HistoryService:
    """
    팀별 자금 흐름 이력 조회 서비스.

    IHistoryQueryRepository의 UNION ALL 복합 쿼리 결과를
    필터 타입(전체/판매만/룰렛만)에 따라 적절히 반환한다.
    """

    def __init__(self, history_repo: IHistoryQueryRepository):
        self.history_repo = history_repo

    def get_team_history(self, team_id: int, event_type: str = "전체") -> pd.DataFrame:
        """
        팀의 자금 흐름 이력을 필터 타입에 따라 반환한다.
          '전체'  → 거래 + 룰렛 이벤트 모두
          '판매만' → TRADE 이벤트만
          '룰렛만' → ROULETTE_COST + ROULETTE_LOSS 이벤트
        """
        if event_type == "판매만":
            return self.history_repo.find_integrated_history_by_team_and_type(
                team_id, "TRADE"
            )
        if event_type == "룰렛만":
            return self.history_repo.find_integrated_history_by_team_and_type(
                team_id, "ROULETTE"
            )
        return self.history_repo.find_integrated_history_by_team(team_id)


# ===========================================================
# 4.6 DashboardService
# ===========================================================

class DashboardService:
    """
    대시보드 집계 데이터 제공 서비스.

    전체 거래 건수, 스핀 횟수, 팀별 잔액 합계, 현재 라운드 번호 등
    대시보드 화면 상단에 표시되는 요약 정보를 계산하여 제공한다.
    get_teams_with_status()는 파생 컬럼(balance_delta, is_bankrupt_imminent 등)을
    추가하여 팀 카드 및 잔액 그래프 표시에 활용한다.
    """

    def __init__(
        self,
        team_repo: ITeamRepository,
        trade_repo: ITradeRepository,
        roulette_repo: IRouletteRepository,
    ):
        # 대시보드에 필요한 세 개의 Repository를 주입받음
        self.team_repo = team_repo
        self.trade_repo = trade_repo
        self.roulette_repo = roulette_repo

    def get_summary(self) -> dict:
        """
        대시보드 상단 요약 카드용 집계 데이터를 반환한다.
          total_trades  : 전체 아이템 판매 거래 건수
          roulette_spins: 전체 룰렛 스핀 횟수
          total_gold    : 모든 팀의 현재 잔액 합계
          round_no      : 현재 라운드 번호 (스핀 횟수 + 1)
        """
        teams = self.team_repo.find_all()
        total_gold = int(teams["current_balance"].sum()) if len(teams) else 0
        return {
            "total_trades": self.trade_repo.count_all(),
            "roulette_spins": self.roulette_repo.count_all(),
            "total_gold": total_gold,
            "round_no": self.roulette_repo.count_all() + 1,
        }

    def get_teams_with_status(self) -> pd.DataFrame:
        """
        팀 목록에 파생 컬럼을 추가하여 반환한다.
          balance_delta        : 현재 잔액 - 초기 잔액 (양수=수익, 음수=손실)
          is_bankrupt_imminent : HP가 30% 미만인 경우 True (파산 임박 경고용)
          is_bankrupt          : 현재 잔액이 0 이하인 경우 True
        """
        teams = self.team_repo.find_all()
        if len(teams) == 0:
            return teams
        teams["balance_delta"] = teams["current_balance"] - teams["initial_balance"]
        teams["is_bankrupt_imminent"] = teams["hp_percent"] < 30
        teams["is_bankrupt"] = teams["current_balance"] <= 0
        return teams


# ===========================================================
# FinanceService — DB 초기화 및 게임 데이터 리셋
# ===========================================================

class FinanceService:
    """
    DB 초기화 및 게임 데이터 리셋 서비스.

    main.py의 AppContainer에서 DatabaseManager를 직접 주입받아
    테이블 생성, 마스터 데이터 적재, 게임 리셋을 담당한다.
    기존 db.py의 역할(Database 클래스의 _init_schema_if_needed, reset_game_data)을
    Service 계층으로 이전한 것이다.
    """

    def __init__(self, db_manager):
        # DatabaseManager로부터 커넥션 객체를 직접 받아 저장
        self._con = db_manager.get_connection()

    def initialize(self) -> None:
        """
        테이블 생성 및 마스터 데이터 초기 적재를 수행한다.
        information_schema.tables를 조회하여 team_color 테이블이 없으면
        최초 실행으로 판단하고 SCHEMA_DDL + MASTER_DATA_SQL을 실행한다.
        이미 테이블이 있으면 '[DB] 기존 DB 연결'만 출력하고 종료한다.
        """
        from db_init import SCHEMA_DDL, MASTER_DATA_SQL
        result = self._con.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'team_color'
        """).fetchone()
        is_first_run = result[0] == 0   # team_color 테이블 미존재 → 최초 실행
        self._con.execute(SCHEMA_DDL)
        if is_first_run:
            self._con.execute(MASTER_DATA_SQL)
            print("[DB] 스키마 및 마스터 데이터 초기화 완료")
        else:
            print("[DB] 기존 DB 연결")

    def reset_game_data(self) -> None:
        """
        게임 데이터를 초기화한다 (마스터 데이터는 유지).
        FK 제약 순서에 따라 roulette_spin → trade → team 순으로 DELETE한다.
        각 시퀀스를 DROP 후 START 1로 재생성하여 id가 1부터 다시 시작되도록 한다.
        """
        self._con.execute("DELETE FROM roulette_spin")
        self._con.execute("DELETE FROM trade")
        self._con.execute("DELETE FROM team")
        for seq in ("seq_team_id", "seq_trade_id", "seq_roulette_id"):
            self._con.execute(f"DROP SEQUENCE IF EXISTS {seq}")
            self._con.execute(f"CREATE SEQUENCE {seq} START 1")
        print("[DB] 게임 데이터 초기화 완료")
