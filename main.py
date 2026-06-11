"""
main.py
파산게임 시뮬레이터 진입점 + 화면 라우팅.

실행:
    uv run flet run main.py
"""

import flet as ft

from db import db
from repositories import (
    DuckDBTeamRepository,
    DuckDBTeamColorRepository,
    DuckDBCategoryRepository,
    DuckDBItemRepository,
    DuckDBTradeRepository,
    DuckDBRouletteRepository,
    DuckDBHistoryQueryRepository,
    DuckDBSystemImageRepository,
)
from services import (
    TeamService,
    ItemService,
    TradeService,
    RouletteService,
    HistoryService,
    DashboardService,
)
from views import (
    TeamRegistrationView,
    TeamSelectionView,
    DashboardView,
    MarketplaceView,
    RouletteView,
    HistoryView,
    show_bankrupt_dialog,
    show_winner_dialog,
)
from theme import BG_MAIN


class AppContainer:
    def __init__(self):
        conn = db.conn
        self.team_color_repo = DuckDBTeamColorRepository(conn)
        self.category_repo = DuckDBCategoryRepository(conn)
        self.item_repo = DuckDBItemRepository(conn)
        self.team_repo = DuckDBTeamRepository(conn)
        self.trade_repo = DuckDBTradeRepository(conn)
        self.roulette_repo = DuckDBRouletteRepository(conn)
        self.history_repo = DuckDBHistoryQueryRepository(conn)
        self.image_repo = DuckDBSystemImageRepository(conn)

        self.team_service = TeamService(self.team_repo, self.team_color_repo)
        self.item_service = ItemService(self.item_repo, self.category_repo)
        self.trade_service = TradeService(
            self.item_repo, self.trade_repo, self.team_repo
        )
        self.roulette_service = RouletteService(self.roulette_repo, self.team_repo)
        self.history_service = HistoryService(self.history_repo)
        self.dashboard_service = DashboardService(
            self.team_repo, self.trade_repo, self.roulette_repo
        )


def main(page: ft.Page):
    page.title = "파산게임 시뮬레이터"
    page.bgcolor = BG_MAIN
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO
    page.window.width = 1200
    page.window.height = 860

    container = AppContainer()
    state = {"current_team_id": None}

    def get_team_info(team_id):
        return container.team_repo.find_by_id(team_id)

    def get_all_teams():
        return container.team_repo.find_all().to_dict("records")

    def get_bankrupt_image():
        rec = container.image_repo.find_by_key("BANKRUPT")
        return rec["image_path"] if rec else None

    def get_winner_image():
        rec = container.image_repo.find_by_key("WINNER")
        return rec["image_path"] if rec else None

    def show_bankrupt(team_name):
        show_bankrupt_dialog(page, team_name, get_bankrupt_image())

    def show_winner(team_name, final_balance):
        show_winner_dialog(
            page, team_name, final_balance,
            get_winner_image(), on_new_game=reset_game
        )

    # 화면 전환
    def show_team_registration():
        page.controls.clear()
        page.add(
            TeamRegistrationView(
                team_service=container.team_service,
                on_register_success=show_team_selection,
            )
        )
        page.update()

    def show_team_selection():
        state["current_team_id"] = None  # 다시 선택하게
        page.controls.clear()
        page.add(
            TeamSelectionView(
                teams=get_all_teams(),
                on_select=on_team_selected,
                on_back=show_team_registration,
            )
        )
        page.update()

    def on_team_selected(team_id: int):
        state["current_team_id"] = team_id
        show_dashboard()

    def show_dashboard():
        if state["current_team_id"] is None:
            show_team_selection()
            return
        page.controls.clear()
        page.add(
            DashboardView(
                dashboard_service=container.dashboard_service,
                current_team_id=state["current_team_id"],
                on_goto_marketplace=show_marketplace,
                on_goto_roulette=show_roulette,
                on_goto_history=show_history,
                on_change_team=show_team_selection,
                on_reset_game=reset_game,
            )
        )
        page.update()

    # ▼ 추가: 파산한 팀이 있으면 알림 (한 번만)
    all_teams = get_all_teams()
    bankrupted = [t for t in all_teams if t["current_balance"] <= 0]
    if bankrupted and "shown_bankrupt" not in state:
        state["shown_bankrupt"] = set()
    if bankrupted:
        for t in bankrupted:
            if t["id"] not in state.get("shown_bankrupt", set()):
                state.setdefault("shown_bankrupt", set()).add(t["id"])
                show_bankrupt(t["name"])
                break  # 한 번에 하나씩만

    def show_marketplace():
        page.controls.clear()
        page.add(
            MarketplaceView(
                item_service=container.item_service,
                trade_service=container.trade_service,
                current_team_id=state["current_team_id"],
                get_team_info=get_team_info,
                on_back=show_dashboard,
            )
        )
        page.update()

    def show_roulette():
        page.controls.clear()
        page.add(
            RouletteView(
                roulette_service=container.roulette_service,
                current_team_id=state["current_team_id"],
                get_team_info=get_team_info,
                get_all_teams=get_all_teams,
                on_back=show_dashboard,
                on_bankrupt=show_bankrupt,
                on_winner=show_winner,
            )
        )
        page.update()

    def show_history():
        page.controls.clear()
        page.add(
            HistoryView(
                history_service=container.history_service,
                teams=get_all_teams(),
                current_team_id=state["current_team_id"],
                on_back=show_dashboard,
            )
        )
        page.update()

    def reset_game():
        db.reset_game_data()
        state["current_team_id"] = None
        show_team_registration()

    # 시작 화면 결정
    existing = get_all_teams()
    if existing:
        # 기존 게임이 있으면 팀 선택부터
        show_team_selection()
    else:
        show_team_registration()


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
