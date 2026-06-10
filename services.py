"""
services.py
비즈니스 로직 계층 (3.1~3.5 유스케이스 + 대시보드 집계).
"""
import random
from typing import List, Optional
import pandas as pd

from repositories import (
    ITeamRepository, ITeamColorRepository, IItemRepository,
    ICategoryRepository, ITradeRepository, IRouletteRepository,
    IHistoryQueryRepository,
)


# ============================================================
# 3.2 TeamService
# ============================================================
class TeamRegistrationError(Exception):
    pass


class TeamService:
    def __init__(self, team_repo: ITeamRepository,
                 color_repo: ITeamColorRepository):
        self.team_repo = team_repo
        self.color_repo = color_repo

    def create_teams(self, teams_data: List[dict]) -> pd.DataFrame:
        self._validate_input(teams_data)
        valid_colors = self.color_repo.find_all()["code"].tolist()
        for t in teams_data:
            if t["color_code"] not in valid_colors:
                raise TeamRegistrationError(
                    f"유효하지 않은 색상 코드: {t['color_code']}")
        self._validate_no_duplicates(teams_data)

        if len(self.team_repo.find_all()) > 0:
            self.team_repo.delete_all()

        df = pd.DataFrame([{
            "name": t["name"], "color_code": t["color_code"],
            "slogan": t.get("slogan", ""), "icon_path": t.get("icon_path"),
            "initial_balance": t["initial_balance"],
            "current_balance": t["initial_balance"],
        } for t in teams_data])
        self.team_repo.save(df)
        return self.team_repo.find_all()

    def _validate_input(self, teams_data: List[dict]):
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
                raise TeamRegistrationError(f"팀 {i}의 초기 잔액은 1원 이상이어야 합니다.")

    def _validate_no_duplicates(self, teams_data: List[dict]):
        names = [t["name"].strip() for t in teams_data]
        colors = [t["color_code"] for t in teams_data]
        if len(set(names)) != len(names):
            raise TeamRegistrationError("팀 이름이 중복되었습니다.")
        if len(set(colors)) != len(colors):
            raise TeamRegistrationError("팀 색상이 중복되었습니다.")

    def find_all_teams(self) -> pd.DataFrame:
        return self.team_repo.find_all()

    def find_all_colors(self) -> pd.DataFrame:
        return self.color_repo.find_all()


# ============================================================
# 3.1 ItemService
# ============================================================
class ItemService:
    def __init__(self, item_repo: IItemRepository,
                 category_repo: ICategoryRepository):
        self.item_repo = item_repo
        self.category_repo = category_repo

    def find_items(self, category_filter: Optional[str] = None) -> pd.DataFrame:
        if category_filter is None or category_filter == "전체":
            return self.item_repo.find_all()
        if category_filter == "NEW":
            return self.item_repo.find_new_items()
        return self.item_repo.find_by_category(category_filter)

    def find_by_id(self, item_id: int) -> Optional[dict]:
        return self.item_repo.find_by_id(item_id)


# ============================================================
# 3.3 TradeService
# ============================================================
class TradeError(Exception):
    pass


class TradeService:
    def __init__(self, item_repo: IItemRepository,
                 trade_repo: ITradeRepository, team_repo: ITeamRepository):
        self.item_repo = item_repo
        self.trade_repo = trade_repo
        self.team_repo = team_repo

    def create_trade(self, team_id: int, item_id: int, quantity: int) -> dict:
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
        return {"trade_id": trade_id, "item_name": item["name"],
                "quantity": quantity, "unit_price": unit_price,
                "total_amount": total, "team": updated_team}

    def count_all_trades(self) -> int:
        return self.trade_repo.count_all()


# ============================================================
# 3.4 RouletteService
# ============================================================
class RouletteError(Exception):
    pass


SPIN_COST = 100_000
PENALTY_AMOUNTS = [
    500_000, 800_000, 1_000_000, 1_500_000,
    2_000_000, 2_500_000, 3_000_000,
]


class RouletteService:
    def __init__(self, roulette_repo: IRouletteRepository,
                 team_repo: ITeamRepository, rng: random.Random = None):
        self.roulette_repo = roulette_repo
        self.team_repo = team_repo
        self.rng = rng or random.Random()

    def execute_spin(self, spinner_team_id: int) -> dict:
        teams = self.team_repo.find_all()
        if len(teams) < 2:
            raise RouletteError("최소 2팀이 등록되어 있어야 합니다.")
        spinner = self.team_repo.find_by_id(spinner_team_id)
        if spinner is None:
            raise RouletteError(f"존재하지 않는 팀: id={spinner_team_id}")
        if spinner["current_balance"] < SPIN_COST:
            raise RouletteError("룰렛 비용(₩100,000)이 부족합니다.")

        team_ids = teams["id"].tolist()
        target_team_id = int(self.rng.choice(team_ids))
        penalty_amount = self.rng.choice(PENALTY_AMOUNTS)

        spin_df = pd.DataFrame([{
            "spinner_team_id": spinner_team_id,
            "target_team_id": target_team_id,
            "penalty_amount": penalty_amount, "spin_cost": SPIN_COST,
        }])
        spin_id = self.roulette_repo.save(spin_df)

        self.team_repo.subtract_balance(spinner_team_id, SPIN_COST)
        updated_target = self.team_repo.subtract_balance(
            target_team_id, penalty_amount)

        return {"spin_id": spin_id, "spinner_team_id": spinner_team_id,
                "target_team_id": target_team_id,
                "target_name": updated_target["name"],
                "target_color": updated_target["color_code"],
                "penalty_amount": penalty_amount, "spin_cost": SPIN_COST}

    def find_recent_results(self, limit: int = 3) -> pd.DataFrame:
        return self.roulette_repo.find_recent_with_team_names(limit)

    def count_all_spins(self) -> int:
        return self.roulette_repo.count_all()


# ============================================================
# 3.5 HistoryService
# ============================================================
class HistoryService:
    def __init__(self, history_repo: IHistoryQueryRepository):
        self.history_repo = history_repo

    def get_team_history(self, team_id: int,
                         event_type: str = "전체") -> pd.DataFrame:
        if event_type == "판매만":
            return self.history_repo.find_integrated_history_by_team_and_type(
                team_id, "TRADE")
        if event_type == "룰렛만":
            return self.history_repo.find_integrated_history_by_team_and_type(
                team_id, "ROULETTE")
        return self.history_repo.find_integrated_history_by_team(team_id)


# ============================================================
# 4.6 DashboardService
# ============================================================
class DashboardService:
    def __init__(self, team_repo: ITeamRepository,
                 trade_repo: ITradeRepository,
                 roulette_repo: IRouletteRepository):
        self.team_repo = team_repo
        self.trade_repo = trade_repo
        self.roulette_repo = roulette_repo

    def get_summary(self) -> dict:
        teams = self.team_repo.find_all()
        total_gold = int(teams["current_balance"].sum()) if len(teams) else 0
        return {"total_trades": self.trade_repo.count_all(),
                "roulette_spins": self.roulette_repo.count_all(),
                "total_gold": total_gold,
                "round_no": self.roulette_repo.count_all() + 1}

    def get_teams_with_status(self) -> pd.DataFrame:
        teams = self.team_repo.find_all()
        if len(teams) == 0:
            return teams
        teams["balance_delta"] = teams["current_balance"] - teams["initial_balance"]
        teams["is_bankrupt_imminent"] = teams["hp_percent"] < 30
        teams["is_bankrupt"] = teams["current_balance"] <= 0
        return teams
