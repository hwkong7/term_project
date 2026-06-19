"""
main.py
파산게임 시뮬레이터 진입점 + 화면 라우팅.

[역할]
  - Flet 앱의 진입점(Entry Point)이자 Controller 역할을 담당한다.
  - 의존성 주입(DI) 방식으로 Repository와 Service 객체를 구성한다.
  - 화면 전환(show_*) 함수를 통해 각 View를 page에 렌더링한다.

[AppContainer]
  .env의 DB_TYPE에 따라 적절한 DatabaseManager를 선택하고,
  각 Repository에 DatabaseManager를 주입한 뒤,
  각 Service에 해당 Repository를 주입한다.
  이 구성이 완료되면 View는 Service 인터페이스만 통해 데이터를 요청한다.

[화면 전환 흐름]
  앱 시작
    → 기존 팀 있음: show_team_selection()
    → 기존 팀 없음: show_team_registration()
  팀 등록 완료 → show_team_selection()
  팀 선택 → show_dashboard()
  대시보드에서
    → 거래소 버튼  → show_marketplace()
    → 룰렛 버튼   → show_roulette()
    → 기록 버튼   → show_history()
    → 팀 변경 버튼 → show_team_selection()
    → 초기화 버튼  → reset_game() → show_team_registration()

실행:
    uv run flet run main.py
"""

import flet as ft

# ===========================================================
# repository 패키지 — DB_TYPE에 맞는 구현체 자동 선택
# .env의 DB_TYPE 값에 따라 repository/__init__.py가 적절한
# DuckDB(또는 MySQL, Oracle 등) 구현체를 DatabaseManager 등의 이름으로 노출한다.
# ===========================================================
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

# ===========================================================
# service 패키지 — 비즈니스 로직 서비스 클래스들
# ===========================================================
from service import (
    FinanceService,
    TeamService,
    ItemService,
    TradeService,
    RouletteService,
    HistoryService,
    DashboardService,
)

# ===========================================================
# views, theme — UI 계층
# ===========================================================
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
    """
    의존성 주입(DI) 컨테이너.

    DatabaseManager → Repository → Service 순으로 객체를 생성하고 주입한다.
    main() 함수에서 단 한 번 생성되어 전체 앱 생명주기 동안 유지된다.

    [구성 순서]
      1. DatabaseManager 생성 (.env DB_TYPE 기반)
      2. 각 Repository에 DatabaseManager 주입
      3. FinanceService로 DB 초기화 (테이블 생성 + 마스터 데이터)
      4. 각 Service에 Repository 주입
    """

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
    """
    Flet 앱 메인 함수. ft.run()에 의해 호출된다.

    AppContainer를 생성하여 DI 구성을 완료한 후,
    게임 상태에 따라 팀 선택 또는 팀 등록 화면으로 시작한다.
    """
    # 페이지 기본 설정
    page.title = "파산게임 시뮬레이터"
    page.bgcolor = BG_MAIN
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO
    page.window.width = 1200
    page.window.height = 860

    # DI 컨테이너 생성 (DB 초기화 포함)
    container = AppContainer()
    # 현재 플레이어가 선택한 팀 id를 저장하는 상태 딕셔너리
    state = {"current_team_id": None}

    # -----------------------------------------------------------
    # 공통 콜백 함수
    # -----------------------------------------------------------

    def get_team_info(team_id):
        """team_id로 팀 정보 딕셔너리를 조회한다 (View에서 헤더 갱신 시 사용)."""
        return container.team_repo.find_by_id(team_id)

    def get_all_teams():
        """전체 팀 목록을 dict 리스트로 반환한다."""
        return container.team_repo.find_all().to_dict("records")

    def get_bankrupt_image():
        """파산 다이얼로그에 표시할 이미지 경로를 DB에서 조회한다."""
        rec = container.image_repo.find_by_key("BANKRUPT")
        return rec["image_path"] if rec else None

    def get_winner_image():
        """우승 다이얼로그에 표시할 이미지 경로를 DB에서 조회한다."""
        rec = container.image_repo.find_by_key("WINNER")
        return rec["image_path"] if rec else None

    def show_bankrupt(team_name):
        """파산 알림 다이얼로그를 표시한다."""
        show_bankrupt_dialog(page, team_name, get_bankrupt_image())

    def show_winner(team_name, final_balance):
        """우승 알림 다이얼로그를 표시한다. 새 게임 시작 시 reset_game 콜백 전달."""
        show_winner_dialog(
            page,
            team_name,
            final_balance,
            get_winner_image(),
            on_new_game=reset_game,
        )

    # -----------------------------------------------------------
    # 화면 전환 함수
    # -----------------------------------------------------------

    def show_team_registration():
        """팀 등록 화면으로 전환한다."""
        page.controls.clear()
        page.add(
            TeamRegistrationView(
                team_service=container.team_service,
                on_register_success=show_team_selection,
            )
        )
        page.update()

    def show_team_selection():
        """팀 선택 화면으로 전환한다. 현재 팀 id를 초기화한다."""
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
        """팀 선택 시 현재 팀 id를 저장하고 대시보드로 이동한다."""
        state["current_team_id"] = team_id
        show_dashboard()

    def show_dashboard():
        """대시보드 화면으로 전환한다. 팀이 선택되지 않은 경우 팀 선택으로 리다이렉트."""
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

    # 대시보드 진입 시 파산팀이 있으면 팀당 1회 파산 알림 표시
    all_teams = get_all_teams()
    bankrupted = [t for t in all_teams if t["current_balance"] <= 0]
    if bankrupted and "shown_bankrupt" not in state:
        state["shown_bankrupt"] = set()
    if bankrupted:
        for t in bankrupted:
            if t["id"] not in state.get("shown_bankrupt", set()):
                state.setdefault("shown_bankrupt", set()).add(t["id"])
                show_bankrupt(t["name"])
                break  # 한 번에 하나씩만 표시

    def show_marketplace():
        """거래소 화면으로 전환한다."""
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
        """룰렛 화면으로 전환한다."""
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
        """자금 흐름 화면으로 전환한다."""
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
        """게임 데이터를 초기화하고 팀 등록 화면으로 돌아간다."""
        container.reset_game_data()
        state["current_team_id"] = None
        show_team_registration()

    # -----------------------------------------------------------
    # 시작 화면 결정
    # -----------------------------------------------------------
    existing = get_all_teams()
    if existing:
        # 기존 게임 데이터가 있으면 팀 선택 화면부터 시작
        show_team_selection()
    else:
        # 최초 실행이거나 게임 리셋 후라면 팀 등록 화면부터 시작
        show_team_registration()


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
