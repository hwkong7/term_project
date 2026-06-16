"""
main.py
파산게임 시뮬레이터 진입점 + 화면 라우팅.

[변경 내용]
- 기존: db.py 싱글턴 + repositories.py + services.py
- 변경: repository/ 패키지(DI) + service/ 패키지
- 화면 라우팅 로직(show_*, reset_game 등)은 기존과 동일

실행:
    uv run flet run main.py
"""

import flet as ft

# =========================================================================
# [변경] repository 패키지 — DB_TYPE에 맞는 구현체 자동 선택
# =========================================================================
from repository import (
    DatabaseManager,
    TeamColorRepository,
    CategoryRepository,
    ItemRepository,
    TeamRepository,
    TradeRepository,
    RouletteRepository,
    HistoryQueryRepository,
    SystemImageRepository,
)

# =========================================================================
# [변경] service 패키지 — 기존 services.py와 동일한 클래스명 유지
# =========================================================================
from service import (
    FinanceService,
    TeamService,
    ItemService,
    TradeService,
    RouletteService,
    HistoryService,
    DashboardService,
)

# =========================================================================
# [유지] views, theme은 기존 그대로
# =========================================================================
from views import (
    TeamRegistrationView,
    TeamSelectionView,
    DashboardView,
    MarketplaceView,
    RouletteView,
    HistoryView,
    show_bankrupt_dialog,
)
from theme import BG_MAIN
from views.dialogs import show_winner_dialog


class AppContainer:
    def __init__(self):
        # .env의 DB_TYPE에 맞는 DB 매니저 자동 선택
        db_manager = DatabaseManager()

        # 각 Repository에 DB 매니저 주입
        self.team_color_repo = TeamColorRepository(db_manager)
        self.category_repo = CategoryRepository(db_manager)
        self.item_repo = ItemRepository(db_manager)
        self.team_repo = TeamRepository(db_manager)
        self.trade_repo = TradeRepository(db_manager)
        self.roulette_repo = RouletteRepository(db_manager)
        self.history_repo = HistoryQueryRepository(db_manager)
        self.image_repo = SystemImageRepository(db_manager)

        # DB 초기화 (테이블 생성 + 마스터 데이터)
        self._finance = FinanceService(db_manager)
        self._finance.initialize()

        # 각 Service에 Repository 주입 — 기존 services.py와 동일한 구조
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

    def reset_game_data(self):
        """게임 데이터 초기화 — 기존 db.reset_game_data() 역할"""
        self._finance.reset_game_data()


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
            page,
            team_name,
            final_balance,
            get_winner_image(),
            on_new_game=reset_game,
        )

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
        state["current_team_id"] = None
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

    all_teams = get_all_teams()
    bankrupted = [t for t in all_teams if t["current_balance"] <= 0]
    if bankrupted and "shown_bankrupt" not in state:
        state["shown_bankrupt"] = set()
    if bankrupted:
        for t in bankrupted:
            if t["id"] not in state.get("shown_bankrupt", set()):
                state.setdefault("shown_bankrupt", set()).add(t["id"])
                show_bankrupt(t["name"])
                break

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

    # [변경] db.reset_game_data() → container.reset_game_data()
    def reset_game():
        container.reset_game_data()
        state["current_team_id"] = None
        show_team_registration()

    existing = get_all_teams()
    if existing:
        show_team_selection()
    else:
        show_team_registration()


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
