"""
views.py
Flet UI 화면들. flet 0.85 API 기준.
  - TeamRegistrationView   (4.2 팀 등록)
  - TeamSelectionView      (게임 시작 후 '나는 어느 팀?' 선택)
  - DashboardView          (4.6 대시보드)
  - MarketplaceView        (4.1 + 4.3 거래소)
  - RouletteView           (4.4 룰렛 — 슬롯머신 애니메이션)
  - HistoryView            (4.5 자금 흐름)
"""

import flet as ft
import threading
import time
import random
from typing import Callable, List, Optional

from theme import (
    BG_PANEL,
    BG_BUTTON,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    TEXT_GOLD,
    ACCENT_RED,
    ACCENT_GREEN_DARK,
    ACCENT_ORANGE,
    TEAM_COLORS,
    TEAM_COLOR_LABELS,
    TEAM_CARD_BG,
    ITEM_EMOJIS,
    DEFAULT_INITIAL_BALANCE,
    MIN_TEAMS,
    MAX_TEAMS,
    format_won,
    format_won_man,
)
from services import (
    TeamService,
    TeamRegistrationError,
    ItemService,
    TradeService,
    TradeError,
    RouletteService,
    RouletteError,
    SPIN_COST,
    HistoryService,
    DashboardService,
)


def _snack(page: ft.Page, msg: str, bgcolor: str):
    """flet 0.85 SnackBar"""
    page.show_dialog(
        ft.SnackBar(content=ft.Text(msg, color=TEXT_LIGHT), bgcolor=bgcolor)
    )


# ============================================================
# 파산 다이얼로그 (DB의 system_image 경로 사용)
# ============================================================
def show_bankrupt_dialog(
    page: ft.Page,
    team_name: str,
    bankrupt_image_path: Optional[str],
    on_confirm: Callable = None,
):
    """잔액이 0 이하가 된 팀에게 표시되는 파산 알림"""

    def close_dialog(e):
        dlg.open = False
        page.update()
        if on_confirm:
            on_confirm()

    # 이미지가 있으면 보여주고, 없으면 텍스트만
    if bankrupt_image_path:
        image_widget = ft.Image(
            src=bankrupt_image_path,
            width=500,
            height=320,
            fit=ft.BoxFit.CONTAIN,
            error_content=ft.Text(
                "💀 파산당했습니다.. 💀",
                size=32,
                weight=ft.FontWeight.BOLD,
                color=ACCENT_RED,
            ),
        )
    else:
        image_widget = ft.Text(
            "💀 파산당했습니다.. 💀",
            size=32,
            weight=ft.FontWeight.BOLD,
            color=ACCENT_RED,
        )

    dlg = ft.AlertDialog(
        modal=True,
        bgcolor="#1A1A1A",
        content=ft.Container(
            content=ft.Column(
                [
                    image_widget,
                    ft.Container(height=12),
                    ft.Text(
                        f"{team_name}팀",
                        size=20,
                        weight=ft.FontWeight.W_500,
                        color=TEXT_GOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    # ft.Text(
                    #     "모든 잔액이 0원이 되어\n파산 처리되었습니다.",
                    #     size=14,
                    #     color=TEXT_LIGHT,
                    #     text_align=ft.TextAlign.CENTER,
                    # ),
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
            width=540,
            padding=20,
        ),
        actions=[
            ft.Container(
                content=ft.Text(
                    "확인", color=TEXT_DARK, size=16, weight=ft.FontWeight.W_500
                ),
                bgcolor=TEAM_COLORS["YELLOW"],
                border=ft.Border.all(3, TEXT_DARK),
                padding=ft.Padding.symmetric(horizontal=40, vertical=12),
                on_click=close_dialog,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )
    page.show_dialog(dlg)


# ============================================================
# 4.2 팀 등록 화면
# ============================================================
DEFAULT_PRESETS = [
    {"name": "양띵", "color": "YELLOW", "slogan": "우승하자!"},
    {"name": "콩콩", "color": "BLUE", "slogan": "콩콩이팀"},
    {"name": "신혜원", "color": "PINK", "slogan": "끝까지간다"},
    {"name": "악어", "color": "GREEN", "slogan": "악어다!"},
    {"name": "팀5", "color": "PURPLE", "slogan": "도전!"},
    {"name": "팀6", "color": "ORANGE", "slogan": "파이팅!"},
]


class TeamCard(ft.Container):
    def __init__(self, index, preset, on_color_change):
        self.index = index
        self.selected_color = preset["color"]
        self.on_color_change = on_color_change

        self.name_field = ft.TextField(
            value=preset["name"],
            label="팀 이름",
            text_size=14,
            border_color=TEXT_DARK,
            bgcolor=ft.Colors.WHITE,
            color=TEXT_DARK,
            label_style=ft.TextStyle(color=TEXT_MUTED, size=11),
        )
        self.slogan_field = ft.TextField(
            value=preset["slogan"],
            label="슬로건",
            text_size=13,
            border_color=TEXT_DARK,
            bgcolor=ft.Colors.WHITE,
            color=TEXT_DARK,
            label_style=ft.TextStyle(color=TEXT_MUTED, size=11),
        )
        self.balance_field = ft.TextField(
            value=str(DEFAULT_INITIAL_BALANCE),
            label="초기 잔액 (원)",
            text_size=13,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=TEXT_DARK,
            bgcolor=ft.Colors.WHITE,
            color=TEXT_DARK,
            label_style=ft.TextStyle(color=TEXT_MUTED, size=11),
        )

        self.color_buttons_row = self._build_color_buttons()
        self.header = ft.Container(
            content=ft.Text(
                f"팀 {index + 1}", size=14, weight=ft.FontWeight.W_500, color=TEXT_LIGHT
            ),
            bgcolor=TEAM_COLORS[self.selected_color],
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        )

        super().__init__(
            content=ft.Column(
                [
                    self.header,
                    ft.Container(
                        content=ft.Column(
                            [
                                self.name_field,
                                self.slogan_field,
                                ft.Text(
                                    "대표 색상",
                                    size=11,
                                    weight=ft.FontWeight.W_500,
                                    color=TEXT_MUTED,
                                ),
                                self.color_buttons_row,
                                self.balance_field,
                            ],
                            spacing=10,
                        ),
                        padding=12,
                    ),
                ],
                spacing=0,
            ),
            bgcolor=TEAM_CARD_BG[self.selected_color],
            border=ft.Border.all(2, TEXT_DARK),
            border_radius=4,
            width=240,
        )

    def _build_color_buttons(self):
        buttons = []
        for code, hex_val in TEAM_COLORS.items():
            sel = code == self.selected_color
            buttons.append(
                ft.Container(
                    content=ft.Container(width=24, height=24, bgcolor=hex_val),
                    border=ft.Border.all(3 if sel else 1, TEXT_DARK),
                    padding=2,
                    tooltip=TEAM_COLOR_LABELS[code],
                    data=code,
                    on_click=self._on_color_click,
                )
            )
        return ft.Row(buttons, spacing=6)

    def _on_color_click(self, e):
        new_c = e.control.data
        old_c = self.selected_color
        self.selected_color = new_c
        self.header.bgcolor = TEAM_COLORS[new_c]
        self.bgcolor = TEAM_CARD_BG[new_c]
        for btn in self.color_buttons_row.controls:
            btn.border = ft.Border.all(3 if btn.data == new_c else 1, TEXT_DARK)
        self.on_color_change(self.index, old_c, new_c)
        self.update()

    def to_dict(self):
        try:
            balance = int(self.balance_field.value or 0)
        except ValueError:
            balance = 0
        return {
            "name": (self.name_field.value or "").strip(),
            "color_code": self.selected_color,
            "slogan": (self.slogan_field.value or "").strip(),
            "icon_path": None,
            "initial_balance": balance,
        }


class TeamRegistrationView(ft.Column):
    def __init__(self, team_service: TeamService, on_register_success: Callable):
        super().__init__(spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)
        self.team_service = team_service
        self.on_register_success = on_register_success
        self.team_count = 4
        self.team_cards: List[TeamCard] = []
        self._build()

    def _build(self):
        self.controls.clear()
        self.controls.append(self._build_header())
        self.controls.append(self._build_team_count_selector())
        self.controls.append(self._build_team_cards_row())
        self.controls.append(self._build_bottom_buttons())

    def _build_header(self):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Text("📦", size=32),
                        width=56,
                        height=56,
                        bgcolor="#8B5A2B",
                        border=ft.Border.all(3, BG_PANEL),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                "파산게임 시뮬레이터",
                                size=22,
                                weight=ft.FontWeight.W_500,
                                color=TEXT_LIGHT,
                            ),
                            ft.Text(
                                "GAME SETUP / 팀 등록",
                                size=11,
                                weight=ft.FontWeight.W_500,
                                color=TEXT_GOLD,
                            ),
                        ],
                        spacing=2,
                    ),
                ],
                spacing=12,
            ),
            bgcolor=BG_PANEL,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        )

    def _build_team_count_selector(self):
        buttons = []
        for n in range(MIN_TEAMS, MAX_TEAMS + 1):
            sel = n == self.team_count
            buttons.append(
                ft.Container(
                    content=ft.Text(
                        f"{n}팀{'  ✓' if sel else ''}",
                        color=TEXT_LIGHT,
                        size=14,
                        weight=ft.FontWeight.W_500,
                    ),
                    bgcolor=BG_BUTTON if sel else "#9A9A9A",
                    border=ft.Border.all(2, TEXT_DARK),
                    width=85,
                    height=36,
                    alignment=ft.Alignment.CENTER,
                    data=n,
                    on_click=self._on_team_count_click,
                )
            )
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(width=4, height=20, bgcolor=TEXT_DARK),
                            ft.Text(
                                "참여 팀 수",
                                size=15,
                                weight=ft.FontWeight.W_500,
                                color=TEXT_DARK,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Row(buttons, spacing=8),
                ],
                spacing=10,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
        )

    def _build_team_cards_row(self):
        self.team_cards = [
            TeamCard(i, DEFAULT_PRESETS[i], self._on_color_change)
            for i in range(self.team_count)
        ]
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(width=4, height=20, bgcolor=TEXT_DARK),
                            ft.Text(
                                "팀 정보 입력",
                                size=15,
                                weight=ft.FontWeight.W_500,
                                color=TEXT_DARK,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Row(self.team_cards, spacing=12, scroll=ft.ScrollMode.AUTO),
                ],
                spacing=10,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
        )

    def _build_bottom_buttons(self):
        reset_btn = ft.Container(
            content=ft.Text(
                "↺ 초기화", color=TEXT_LIGHT, size=15, weight=ft.FontWeight.W_500
            ),
            bgcolor="#9A9A9A",
            border=ft.Border.all(3, TEXT_DARK),
            height=52,
            expand=1,
            alignment=ft.Alignment.CENTER,
            on_click=self._on_reset_click,
        )
        start_btn = ft.Container(
            content=ft.Text(
                "▶ 게임 시작", color=TEXT_LIGHT, size=17, weight=ft.FontWeight.W_500
            ),
            bgcolor=ACCENT_RED,
            border=ft.Border.all(3, TEXT_DARK),
            height=52,
            expand=2,
            alignment=ft.Alignment.CENTER,
            on_click=self._on_start_click,
        )
        return ft.Container(
            content=ft.Row([reset_btn, start_btn], spacing=12),
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
        )

    def _on_team_count_click(self, e):
        if e.control.data == self.team_count:
            return
        self.team_count = e.control.data
        self._build()
        self.update()

    def _on_color_change(self, idx, old_c, new_c):
        for i, card in enumerate(self.team_cards):
            if i == idx:
                continue
            if card.selected_color == new_c:
                card.selected_color = old_c
                card.header.bgcolor = TEAM_COLORS[old_c]
                card.bgcolor = TEAM_CARD_BG[old_c]
                for btn in card.color_buttons_row.controls:
                    btn.border = ft.Border.all(3 if btn.data == old_c else 1, TEXT_DARK)
                card.update()
                break

    def _on_reset_click(self, e):
        self.team_count = 4
        self._build()
        self.update()

    def _on_start_click(self, e):
        teams_data = [c.to_dict() for c in self.team_cards]
        try:
            self.team_service.create_teams(teams_data)
            _snack(
                self.page, f"✅ {len(teams_data)}개 팀 등록 완료!", ACCENT_GREEN_DARK
            )
            self.on_register_success()
        except TeamRegistrationError as ex:
            _snack(self.page, f"⚠ {ex}", ACCENT_RED)
        except Exception as ex:
            _snack(self.page, f"⚠ 오류: {ex}", ACCENT_RED)


# ============================================================
# 팀 선택 화면 (새로 추가) — "나는 어느 팀?"
# ============================================================
class TeamSelectionView(ft.Column):
    """게임 시작 후 본인이 어느 팀인지 선택하는 화면.
    멀티플레이 환경에서 각 노트북에서 자기 팀을 선택해 사용."""

    def __init__(
        self, teams: list, on_select: Callable[[int], None], on_back: Callable
    ):
        super().__init__(
            spacing=20,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.teams = teams
        self.on_select = on_select
        self.on_back = on_back
        self._build()

    def _build(self):
        self.controls.clear()
        self.controls.append(self._build_header())
        self.controls.append(ft.Container(height=20))
        self.controls.append(
            ft.Text(
                "이번 게임에서 어느 팀이신가요?",
                size=20,
                weight=ft.FontWeight.W_500,
                color=TEXT_DARK,
            )
        )
        self.controls.append(
            ft.Text(
                "선택한 팀의 입장에서 거래소와 룰렛을 사용하게 됩니다.",
                size=13,
                color=TEXT_MUTED,
            )
        )
        self.controls.append(ft.Container(height=10))
        self.controls.append(self._build_team_grid())
        self.controls.append(ft.Container(height=10))
        self.controls.append(self._build_back_button())

    def _build_header(self):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Text("👤", size=32),
                        width=56,
                        height=56,
                        bgcolor="#8B5A2B",
                        border=ft.Border.all(3, BG_PANEL),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                "파산게임 시뮬레이터",
                                size=22,
                                weight=ft.FontWeight.W_500,
                                color=TEXT_LIGHT,
                            ),
                            ft.Text(
                                "PLAYER SELECT / 내 팀 선택",
                                size=11,
                                weight=ft.FontWeight.W_500,
                                color=TEXT_GOLD,
                            ),
                        ],
                        spacing=2,
                    ),
                ],
                spacing=12,
            ),
            bgcolor=BG_PANEL,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            width=10000,
        )

    def _build_team_grid(self):
        cards = [self._team_card(t) for t in self.teams]
        return ft.Container(
            content=ft.Row(
                cards,
                spacing=16,
                wrap=True,
                alignment=ft.MainAxisAlignment.CENTER,
                run_spacing=16,
            ),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _team_card(self, team):
        cc = team["color_code"]
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Text(
                            team["name"],
                            color=TEXT_LIGHT,
                            size=18,
                            weight=ft.FontWeight.W_500,
                        ),
                        bgcolor=TEAM_COLORS[cc],
                        padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Container(
                                    content=ft.Text(":)", size=44, color=TEXT_DARK),
                                    width=100,
                                    height=100,
                                    bgcolor=TEAM_COLORS[cc],
                                    border=ft.Border.all(3, TEXT_DARK),
                                    alignment=ft.Alignment.CENTER,
                                ),
                                ft.Container(height=8),
                                ft.Text(
                                    f'"{team.get("slogan", "")}"',
                                    size=12,
                                    italic=True,
                                    color=TEXT_MUTED,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Text(
                                    format_won(int(team["current_balance"])),
                                    size=15,
                                    weight=ft.FontWeight.W_500,
                                    color=ACCENT_ORANGE,
                                ),
                            ],
                            spacing=6,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=16,
                    ),
                ],
                spacing=0,
            ),
            bgcolor=TEAM_CARD_BG[cc],
            border=ft.Border.all(2, TEXT_DARK),
            border_radius=4,
            width=200,
            ink=True,
            data=team["id"],
            on_click=self._on_team_click,
        )

    def _on_team_click(self, e):
        self.on_select(e.control.data)

    def _build_back_button(self):
        return ft.Container(
            content=ft.Text(
                "↺ 팀 등록으로 돌아가기",
                color=TEXT_LIGHT,
                size=13,
                weight=ft.FontWeight.W_500,
            ),
            bgcolor="#9A9A9A",
            border=ft.Border.all(2, TEXT_DARK),
            width=240,
            height=40,
            alignment=ft.Alignment.CENTER,
            on_click=lambda e: self.on_back(),
        )


# ============================================================
# 4.6 대시보드 화면
# ============================================================
class DashboardView(ft.Column):
    def __init__(
        self,
        dashboard_service: DashboardService,
        current_team_id: int,
        on_goto_marketplace,
        on_goto_roulette,
        on_goto_history,
        on_change_team,
        on_reset_game,
    ):
        super().__init__(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        self.svc = dashboard_service
        self.current_team_id = current_team_id
        self.on_goto_marketplace = on_goto_marketplace
        self.on_goto_roulette = on_goto_roulette
        self.on_goto_history = on_goto_history
        self.on_change_team = on_change_team
        self.on_reset_game = on_reset_game
        self._build()

    def _build(self):
        self.controls.clear()
        summary = self.svc.get_summary()
        teams = self.svc.get_teams_with_status()
        self.controls.append(self._build_header(summary))
        self.controls.append(self._build_summary_cards(summary))
        self.controls.append(self._section_label("팀 상황"))
        self.controls.append(self._build_team_cards(teams))
        self.controls.append(self._section_label("BALANCE GRAPH"))
        self.controls.append(self._build_balance_graph(teams))
        self.controls.append(self._build_menu_buttons())

    def _build_header(self, summary):
        my_team = self.svc.team_repo.find_by_id(self.current_team_id)
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Text("📦", size=32),
                        width=56,
                        height=56,
                        bgcolor="#8B5A2B",
                        border=ft.Border.all(3, BG_PANEL),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                "파산게임 시뮬레이터",
                                size=22,
                                weight=ft.FontWeight.W_500,
                                color=TEXT_LIGHT,
                            ),
                            ft.Text(
                                f"ROUND {summary['round_no']} / 진행중",
                                size=11,
                                weight=ft.FontWeight.W_500,
                                color=TEXT_GOLD,
                            ),
                        ],
                        spacing=2,
                    ),
                    ft.Container(expand=True),
                    # 내 팀 표시 + 팀 변경 버튼
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Text("내 팀:", color=TEXT_MUTED, size=11),
                                ft.Container(
                                    width=20,
                                    height=20,
                                    bgcolor=TEAM_COLORS[my_team["color_code"]],
                                    border=ft.Border.all(2, TEXT_DARK),
                                ),
                                ft.Text(
                                    my_team["name"],
                                    color=TEXT_LIGHT,
                                    size=14,
                                    weight=ft.FontWeight.W_500,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.SWAP_HORIZ,
                                    icon_color=TEXT_GOLD,
                                    icon_size=18,
                                    tooltip="팀 변경",
                                    on_click=lambda e: self.on_change_team(),
                                ),
                            ],
                            spacing=8,
                        ),
                        bgcolor="#5A3F1F",
                        border=ft.Border.all(2, TEXT_GOLD),
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH,
                        icon_color=TEXT_LIGHT,
                        tooltip="새 게임 (초기화)",
                        on_click=lambda e: self.on_reset_game(),
                    ),
                ],
                spacing=12,
            ),
            bgcolor=BG_PANEL,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        )

    def _build_summary_cards(self, summary):
        return ft.Container(
            content=ft.Row(
                [
                    self._summary_card(
                        "TOTAL TRADES", str(summary["total_trades"]), TEXT_LIGHT
                    ),
                    self._summary_card(
                        "ROULETTE SPINS", str(summary["roulette_spins"]), TEXT_LIGHT
                    ),
                    self._summary_card(
                        "TOTAL GOLD", format_won_man(summary["total_gold"]), TEXT_GOLD
                    ),
                ],
                spacing=12,
            ),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _summary_card(self, label, value, value_color):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        label, size=11, weight=ft.FontWeight.W_500, color=TEXT_GOLD
                    ),
                    ft.Text(
                        value, size=24, weight=ft.FontWeight.W_500, color=value_color
                    ),
                ],
                spacing=4,
            ),
            bgcolor=BG_PANEL,
            border=ft.Border.all(2, BG_PANEL),
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            expand=True,
        )

    def _section_label(self, text):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(width=4, height=20, bgcolor=TEXT_DARK),
                    ft.Text(text, size=15, weight=ft.FontWeight.W_500, color=TEXT_DARK),
                ],
                spacing=8,
            ),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _build_team_cards(self, teams):
        cards = [self._team_card(t) for _, t in teams.iterrows()]
        return ft.Container(
            content=ft.Row(cards, spacing=10, scroll=ft.ScrollMode.AUTO),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _team_card(self, t):
        cc = t["color_code"]
        delta = int(t["balance_delta"])
        hp = int(t["hp_percent"])
        imminent = bool(t["is_bankrupt_imminent"])
        is_me = int(t["id"]) == self.current_team_id

        if delta > 0:
            delta_text = ft.Text(
                f"▲ +{format_won_man(delta)}",
                size=11,
                color=ACCENT_GREEN_DARK,
                weight=ft.FontWeight.W_500,
            )
        elif delta < 0:
            delta_text = ft.Text(
                f"▼ {format_won_man(delta)}",
                size=11,
                color=ACCENT_RED,
                weight=ft.FontWeight.W_500,
            )
        else:
            delta_text = ft.Text("─ 변동 없음", size=11, color=TEXT_MUTED)

        hp_section = []
        if imminent:
            hp_section = [
                ft.Text(
                    "▼ 파산임박!", size=11, color=ACCENT_RED, weight=ft.FontWeight.W_500
                ),
                ft.Row(
                    [
                        ft.Container(
                            width=max(hp * 1.4, 2), height=12, bgcolor=ACCENT_RED
                        ),
                        ft.Container(
                            width=max((100 - hp) * 1.4, 2), height=12, bgcolor="#5A3F1F"
                        ),
                    ],
                    spacing=0,
                ),
                ft.Text(f"HP {hp}%", size=10, color=TEXT_MUTED),
            ]

        # 내 팀이면 별표 + 두꺼운 테두리
        name_row = [
            ft.Text(t["name"], color=TEXT_LIGHT, size=13, weight=ft.FontWeight.W_500)
        ]
        if is_me:
            name_row.append(
                ft.Text("★ ME", color=TEXT_GOLD, size=11, weight=ft.FontWeight.W_500)
            )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Row(name_row, spacing=6),
                        bgcolor=TEAM_COLORS[cc],
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                    ),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Container(
                                            content=ft.Text(
                                                ":)", size=18, color=TEXT_DARK
                                            ),
                                            width=44,
                                            height=44,
                                            bgcolor=TEAM_COLORS[cc],
                                            border=ft.Border.all(2, TEXT_DARK),
                                            alignment=ft.Alignment.CENTER,
                                        ),
                                        ft.Text(
                                            format_won_man(int(t["current_balance"])),
                                            size=16,
                                            weight=ft.FontWeight.W_500,
                                            color=TEXT_DARK,
                                        ),
                                    ],
                                    spacing=10,
                                ),
                                delta_text,
                                *hp_section,
                                ft.Text(
                                    f'"{t.get("slogan", "")}"',
                                    size=10,
                                    italic=True,
                                    color=TEXT_MUTED,
                                ),
                            ],
                            spacing=4,
                        ),
                        padding=10,
                    ),
                ],
                spacing=0,
            ),
            bgcolor=TEAM_CARD_BG[cc],
            border=ft.Border.all(
                4 if is_me else (3 if imminent else 2),
                TEXT_GOLD if is_me else (ACCENT_RED if imminent else TEXT_DARK),
            ),
            width=200,
        )

    def _build_balance_graph(self, teams):
        if len(teams) == 0:
            return ft.Container()
        max_balance = max(int(teams["current_balance"].max()), 1)
        bars = []
        for _, t in teams.iterrows():
            balance = int(t["current_balance"])
            ratio = balance / max_balance
            color = TEAM_COLORS[t["color_code"]]
            text_color = ACCENT_RED if t["is_bankrupt_imminent"] else TEXT_DARK
            bars.append(
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(
                                t["name"],
                                size=12,
                                weight=ft.FontWeight.W_500,
                                color=text_color,
                            ),
                            width=60,
                        ),
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Container(
                                        expand=max(int(ratio * 100), 1),
                                        height=18,
                                        bgcolor=color,
                                    ),
                                    ft.Container(
                                        expand=max(int((1 - ratio) * 100), 1),
                                        height=18,
                                        bgcolor="#5A3F1F",
                                    ),
                                ],
                                spacing=0,
                            ),
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Text(
                                format_won_man(balance),
                                size=12,
                                weight=ft.FontWeight.W_500,
                                color=text_color,
                            ),
                            width=100,
                        ),
                    ],
                    spacing=10,
                )
            )
        return ft.Container(
            content=ft.Container(
                content=ft.Column(bars, spacing=8),
                bgcolor="#F5EDD8",
                border=ft.Border.all(2, TEXT_DARK),
                padding=12,
            ),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _build_menu_buttons(self):
        def btn(emoji, label, color, handler):
            return ft.Container(
                content=ft.Row(
                    [
                        ft.Text(emoji, size=20),
                        ft.Text(
                            label, color=TEXT_LIGHT, size=16, weight=ft.FontWeight.W_500
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=8,
                ),
                bgcolor=color,
                border=ft.Border.all(3, TEXT_DARK),
                height=52,
                expand=True,
                alignment=ft.Alignment.CENTER,
                on_click=lambda e: handler(),
            )

        return ft.Container(
            content=ft.Row(
                [
                    btn("🛒", "거래소", ACCENT_ORANGE, self.on_goto_marketplace),
                    btn("🎰", "룰렛돌리기", ACCENT_RED, self.on_goto_roulette),
                    btn("📜", "기록보기", "#888888", self.on_goto_history),
                ],
                spacing=12,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
        )


# ============================================================
# 4.1 + 4.3 거래소 화면
# ============================================================
CATEGORY_TABS = ["전체", "광물", "식량", "NEW"]


class ItemCard(ft.Container):
    def __init__(self, item, on_sell):
        self.item = item
        self.on_sell = on_sell
        emoji = ITEM_EMOJIS.get(item["name"], "📦")
        self.qty_field = ft.TextField(
            value="1",
            width=80,
            height=40,
            text_size=13,
            text_align=ft.TextAlign.CENTER,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=TEXT_DARK,
            bgcolor=ft.Colors.WHITE,
            color=TEXT_DARK,
        )
        sell_btn = ft.Container(
            content=ft.Text(
                "판매", color=TEXT_LIGHT, size=13, weight=ft.FontWeight.W_500
            ),
            bgcolor=ACCENT_GREEN_DARK,
            border=ft.Border.all(2, TEXT_DARK),
            width=70,
            height=40,
            alignment=ft.Alignment.CENTER,
            on_click=self._on_sell_click,
        )
        super().__init__(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Text(emoji, size=44),
                        bgcolor="#5A4632",
                        height=110,
                        alignment=ft.Alignment.CENTER,
                        border=ft.Border.all(1, TEXT_DARK),
                    ),
                    ft.Text(
                        item["name"],
                        size=15,
                        weight=ft.FontWeight.W_500,
                        color=TEXT_DARK,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        f"[{item['category']}]",
                        size=11,
                        color=TEXT_MUTED,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        format_won(int(item["price"])),
                        size=16,
                        weight=ft.FontWeight.W_500,
                        color=ACCENT_ORANGE,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Row(
                        [self.qty_field, sell_btn],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6,
                    ),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="#E8DCC0",
            border=ft.Border.all(2, "#6B4F2E"),
            border_radius=4,
            padding=10,
            width=210,
        )

    def _on_sell_click(self, e):
        try:
            qty = int(self.qty_field.value or 0)
        except ValueError:
            qty = 0
        self.on_sell(self.item["id"], self.item["name"], qty)


class MarketplaceView(ft.Column):
    def __init__(
        self, item_service, trade_service, current_team_id, get_team_info, on_back
    ):
        super().__init__(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        self.item_service = item_service
        self.trade_service = trade_service
        self.current_team_id = current_team_id
        self.get_team_info = get_team_info
        self.on_back = on_back
        self.active_category = "전체"
        self._build()

    def _build(self):
        self.controls.clear()
        self.controls.append(self._build_header())
        self.controls.append(self._build_category_tabs())
        self.controls.append(self._build_item_grid())

    def _build_header(self):
        team = self.get_team_info(self.current_team_id)
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.ARROW_BACK_IOS, color=TEXT_LIGHT, size=16
                                ),
                                ft.Text(
                                    "BACK",
                                    color=TEXT_LIGHT,
                                    size=14,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                            spacing=4,
                        ),
                        on_click=lambda e: self.on_back(),
                        padding=8,
                    ),
                    ft.Text(
                        "🛒 거래소",
                        color=TEXT_LIGHT,
                        size=20,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.Container(expand=True),
                    self._team_badge(team),
                ],
                spacing=12,
            ),
            bgcolor=BG_PANEL,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        )

    def _team_badge(self, team):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Text(":)", size=14, color=TEXT_DARK),
                        width=28,
                        height=28,
                        bgcolor=TEAM_COLORS[team["color_code"]],
                        border=ft.Border.all(2, TEXT_DARK),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Text(
                        f"{team['name']}팀",
                        color=TEXT_LIGHT,
                        size=14,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.Text("잔액", color=TEXT_MUTED, size=12),
                    ft.Text(
                        format_won(int(team["current_balance"])),
                        color=TEXT_GOLD,
                        size=15,
                        weight=ft.FontWeight.W_500,
                    ),
                ],
                spacing=10,
            ),
            bgcolor="#5A3F1F",
            border=ft.Border.all(2, TEXT_GOLD),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        )

    def _build_category_tabs(self):
        tabs = []
        for cat in CATEGORY_TABS:
            sel = cat == self.active_category
            tabs.append(
                ft.Container(
                    content=ft.Text(
                        cat, color=TEXT_LIGHT, size=14, weight=ft.FontWeight.W_500
                    ),
                    bgcolor=BG_BUTTON if sel else "#9A9A9A",
                    border=ft.Border.all(2, TEXT_DARK),
                    width=110,
                    height=44,
                    alignment=ft.Alignment.CENTER,
                    data=cat,
                    on_click=self._on_tab_click,
                )
            )
        return ft.Container(
            content=ft.Row(tabs, spacing=10),
            padding=ft.Padding.symmetric(horizontal=16, vertical=4),
        )

    def _build_item_grid(self):
        items = self.item_service.find_items(self.active_category)
        cards = [ItemCard(it.to_dict(), self._on_sell) for _, it in items.iterrows()]
        grid = ft.Row(cards, spacing=12, wrap=True, run_spacing=12)
        return ft.Container(
            content=ft.Container(
                content=grid,
                bgcolor="#8B6B45",
                border=ft.Border.all(3, "#3E2A14"),
                padding=16,
            ),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _on_tab_click(self, e):
        self.active_category = e.control.data
        self._build()
        self.update()

    def _on_sell(self, item_id, item_name, qty):
        try:
            result = self.trade_service.create_trade(self.current_team_id, item_id, qty)
            _snack(
                self.page,
                f"✅ {item_name} {qty}개 판매! (+{format_won(result['total_amount'])})",
                ACCENT_GREEN_DARK,
            )
            self.controls[0] = self._build_header()
            self.update()
        except TradeError as ex:
            _snack(self.page, f"⚠ {ex}", ACCENT_RED)
        except Exception as ex:
            _snack(self.page, f"⚠ 오류: {ex}", ACCENT_RED)


# ============================================================
# 4.4 룰렛 화면 — 진짜 슬롯머신 애니메이션
# ============================================================
class SlotReel(ft.Container):
    """슬롯머신 한 칸 — Stack 안에서 위로 움직이는 띠"""

    def __init__(
        self, width: int, height: int, items: List[str], color: str = TEXT_DARK
    ):
        self.item_height = height
        self.items = items
        self.text_color = color

        # 띠 안에 들어갈 텍스트들 (위에서 아래로)
        self.text_controls = [
            ft.Container(
                content=ft.Text(
                    text,
                    size=32,
                    weight=ft.FontWeight.BOLD,
                    color=self.text_color,
                    text_align=ft.TextAlign.CENTER,
                ),
                width=width,
                height=height,
                alignment=ft.Alignment.CENTER,
            )
            for text in items
        ]

        # 띠 (Column)
        self.strip = ft.Column(
            controls=self.text_controls,
            spacing=0,
            tight=True,
        )

        # 띠를 감싸는 Stack (위로 이동 효과)
        self.strip_container = ft.Container(
            content=self.strip,
            top=0,
            left=0,
            animate_position=ft.Animation(80, ft.AnimationCurve.LINEAR),
        )

        super().__init__(
            content=ft.Stack(
                [self.strip_container], clip_behavior=ft.ClipBehavior.HARD_EDGE
            ),
            width=width,
            height=height,
            bgcolor="#D4C4A0",
            border=ft.Border.all(3, TEXT_GOLD),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )

    def set_position(
        self, index: int, duration_ms: int = 80, curve=ft.AnimationCurve.LINEAR
    ):
        """띠를 위로 올려서 index 번째 항목이 가운데에 오게 함"""
        self.strip_container.animate_position = ft.Animation(duration_ms, curve)
        self.strip_container.top = -index * self.item_height
        self.strip_container.update()

    def get_text(self, index: int) -> str:
        return self.items[index % len(self.items)]


class RouletteView(ft.Column):
    def __init__(
        self,
        roulette_service,
        current_team_id,
        get_team_info,
        get_all_teams,
        on_back,
        on_bankrupt: Callable = None,
    ):
        super().__init__(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        self.svc = roulette_service
        self.current_team_id = current_team_id
        self.get_team_info = get_team_info
        self.get_all_teams = get_all_teams
        self.on_back = on_back
        self.on_bankrupt = on_bankrupt
        self.is_spinning = False

        # 슬롯 릴 만들 때 사용할 항목들
        self._all_teams = get_all_teams()
        team_names = [t["name"] for t in self._all_teams]
        # 띠는 충분히 길게 (계속 돌리는 효과)
        self.team_strip = team_names * 8
        amount_labels = [
            format_won_man(a)
            for a in [
                500_000,
                800_000,
                1_000_000,
                1_500_000,
                2_000_000,
                2_500_000,
                3_000_000,
            ]
        ]
        self.amount_strip = amount_labels * 8

        self.team_reel = SlotReel(320, 100, self.team_strip, TEXT_DARK)
        self.amount_reel = SlotReel(320, 100, self.amount_strip, TEXT_DARK)

        self.team_status = ft.Text("READY", size=16, color=TEXT_MUTED)
        self.amount_status = ft.Text("READY", size=16, color=TEXT_MUTED)
        self._build()

    def _build(self):
        self.controls.clear()
        self.controls.append(self._build_header())
        self.controls.append(self._build_panel())
        self.controls.append(self._build_recent())

    def _build_header(self):
        team = self.get_team_info(self.current_team_id)
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.ARROW_BACK_IOS, color=TEXT_LIGHT, size=16
                                ),
                                ft.Text(
                                    "BACK",
                                    color=TEXT_LIGHT,
                                    size=14,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                            spacing=4,
                        ),
                        on_click=lambda e: self.on_back(),
                        padding=8,
                    ),
                    ft.Text(
                        "🎰 룰렛 시스템",
                        color=TEXT_LIGHT,
                        size=20,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.Container(expand=True),
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Container(
                                    content=ft.Text(":)", size=14, color=TEXT_DARK),
                                    width=28,
                                    height=28,
                                    bgcolor=TEAM_COLORS[team["color_code"]],
                                    border=ft.Border.all(2, TEXT_DARK),
                                    alignment=ft.Alignment.CENTER,
                                ),
                                ft.Text(
                                    f"{team['name']}팀",
                                    color=TEXT_LIGHT,
                                    size=14,
                                    weight=ft.FontWeight.W_500,
                                ),
                                ft.Text("잔액", color=TEXT_MUTED, size=12),
                                ft.Text(
                                    format_won(int(team["current_balance"])),
                                    color=TEXT_GOLD,
                                    size=15,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                            spacing=10,
                        ),
                        bgcolor="#5A3F1F",
                        border=ft.Border.all(2, TEXT_GOLD),
                        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                    ),
                ],
                spacing=12,
            ),
            bgcolor=BG_PANEL,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        )

    def _build_panel(self):
        self.spin_button = ft.Container(
            content=ft.Text(
                f"🎲 SPIN!  ({format_won_man(SPIN_COST)})",
                color=TEXT_LIGHT,
                size=20,
                weight=ft.FontWeight.W_500,
            ),
            bgcolor=ACCENT_RED,
            border=ft.Border.all(3, TEXT_GOLD),
            height=60,
            alignment=ft.Alignment.CENTER,
            on_click=self._on_spin_click,
        )
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "★ 파산 룰렛 ★",
                        color=TEXT_GOLD,
                        size=20,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.Row(
                        [
                            self._slot("걸릴 팀", self.team_reel, self.team_status),
                            self._slot(
                                "차감 금액", self.amount_reel, self.amount_status
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=20,
                    ),
                    self.spin_button,
                ],
                spacing=20,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="#2A2A2A",
            border=ft.Border.all(3, TEXT_GOLD),
            padding=20,
            margin=ft.Margin.symmetric(horizontal=16, vertical=0),
        )

    def _slot(self, title, reel, status):
        return ft.Column(
            [
                ft.Container(
                    content=ft.Text(
                        title, color=TEXT_GOLD, size=14, weight=ft.FontWeight.W_500
                    ),
                    bgcolor="#2A1C0E",
                    padding=ft.Padding.symmetric(vertical=8),
                    alignment=ft.Alignment.CENTER,
                    width=320,
                ),
                reel,
                ft.Container(
                    content=status,
                    padding=ft.Padding.symmetric(vertical=6),
                    alignment=ft.Alignment.CENTER,
                ),
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_recent(self):
        recent = self.svc.find_recent_results(3)
        rows = []
        if len(recent) == 0:
            rows.append(
                ft.Text("아직 룰렛 기록이 없습니다.", size=13, color=TEXT_MUTED)
            )
        else:
            labels = ["방금", "1분전", "3분전"]
            for i, (_, r) in enumerate(recent.iterrows()):
                rows.append(self._result_row(labels[i] if i < 3 else f"{i}회전", r))
        return ft.Container(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Container(width=4, height=18, bgcolor=TEXT_DARK),
                                ft.Text(
                                    "최근 룰렛 결과",
                                    size=14,
                                    weight=ft.FontWeight.W_500,
                                    color=TEXT_DARK,
                                ),
                            ],
                            spacing=8,
                        ),
                        *rows,
                    ],
                    spacing=8,
                ),
                bgcolor="#F5EDD8",
                border=ft.Border.all(2, TEXT_DARK),
                padding=12,
            ),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _result_row(self, label, r):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Text(label, size=11, color=TEXT_MUTED), width=50
                    ),
                    ft.Container(
                        width=16,
                        height=16,
                        bgcolor=TEAM_COLORS.get(r["spinner_color"], "#999"),
                    ),
                    ft.Text(
                        r["spinner_name"],
                        size=13,
                        weight=ft.FontWeight.W_500,
                        color=TEXT_DARK,
                    ),
                    ft.Text("→", size=14, color=TEXT_MUTED),
                    ft.Container(
                        width=16,
                        height=16,
                        bgcolor=TEAM_COLORS.get(r["target_color"], "#999"),
                    ),
                    ft.Text(
                        r["target_name"],
                        size=13,
                        weight=ft.FontWeight.W_500,
                        color=TEXT_DARK,
                    ),
                    ft.Container(expand=True),
                    ft.Text(
                        format_won(-int(r["penalty_amount"])),
                        size=14,
                        weight=ft.FontWeight.W_500,
                        color=ACCENT_RED,
                    ),
                ],
                spacing=8,
            ),
            bgcolor="#FFFFFF",
            border=ft.Border.all(1, "#C4B590"),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        )

    def _on_spin_click(self, e):
        if self.is_spinning:
            return
        try:
            result = self.svc.execute_spin(self.current_team_id)
        except RouletteError as ex:
            _snack(self.page, f"⚠ {ex}", ACCENT_RED)
            return
        except Exception as ex:
            _snack(self.page, f"⚠ 오류: {ex}", ACCENT_RED)
            return

        self.is_spinning = True
        self.spin_button.bgcolor = "#888888"
        self.team_status.value = "SPINNING..."
        self.amount_status.value = "CALCULATING..."
        self.update()
        threading.Thread(target=self._animate, args=(result,), daemon=True).start()

    def _animate(self, result):
        """진짜 슬롯머신처럼 띠를 위로 빠르게 → 천천히 → 정지"""
        # 결과가 위치할 인덱스를 찾는다 (띠 후반부에 위치하도록)
        team_names = [t["name"] for t in self._all_teams]
        target_team_idx_in_loop = team_names.index(result["target_name"])
        # 띠는 8번 반복돼 있으니 6번째 루프의 해당 인덱스로 정지
        team_target_index = 6 * len(team_names) + target_team_idx_in_loop

        amount_labels = [
            format_won_man(a)
            for a in [
                500_000,
                800_000,
                1_000_000,
                1_500_000,
                2_000_000,
                2_500_000,
                3_000_000,
            ]
        ]
        amount_target_idx_in_loop = amount_labels.index(
            format_won_man(result["penalty_amount"])
        )
        amount_target_index = 6 * len(amount_labels) + amount_target_idx_in_loop

        # 1단계: 빠르게 돌리기 (위로 쭉)
        self.team_reel.set_position(
            team_target_index - 8, duration_ms=1200, curve=ft.AnimationCurve.EASE_IN_OUT
        )
        self.amount_reel.set_position(
            amount_target_index - 12,
            duration_ms=1400,
            curve=ft.AnimationCurve.EASE_IN_OUT,
        )
        time.sleep(1.5)

        # 2단계: 천천히 정지 위치로 (감속)
        self.team_reel.set_position(
            team_target_index, duration_ms=900, curve=ft.AnimationCurve.DECELERATE
        )
        time.sleep(0.5)
        self.amount_reel.set_position(
            amount_target_index, duration_ms=1100, curve=ft.AnimationCurve.DECELERATE
        )
        time.sleep(1.0)

        # 결과 확정 표시
        self.team_status.value = "🎯 당첨!"
        self.amount_status.value = "확정!"
        self.is_spinning = False
        self.spin_button.bgcolor = ACCENT_RED

        try:
            self.controls[2] = self._build_recent()
            self.controls[0] = self._build_header()
            self.update()
            _snack(
                self.page,
                f"🎰 {result['target_name']}팀 {format_won(result['penalty_amount'])} 차감!",
                ACCENT_RED,
            )

            # 파산 체크
            target_team = self.get_team_info(result["target_team_id"])
            if target_team and target_team["current_balance"] <= 0 and self.on_bankrupt:
                # 약간 딜레이 후 파산 다이얼로그
                time.sleep(0.8)
                self.on_bankrupt(target_team["name"])
        except Exception:
            pass


# ============================================================
# 4.5 자금 흐름 화면
# ============================================================
EVENT_FILTERS = ["전체", "판매만", "룰렛만"]
EVENT_META = {
    "TRADE": {"icon": "📦", "bar": ACCENT_GREEN_DARK},
    "ROULETTE_COST": {"icon": "🎲", "bar": ACCENT_RED},
    "ROULETTE_LOSS": {"icon": "🎲", "bar": ACCENT_RED},
}


class HistoryView(ft.Column):
    def __init__(self, history_service, teams, current_team_id, on_back):
        super().__init__(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        self.svc = history_service
        self.teams = teams
        self.selected_team_id = current_team_id
        self.active_filter = "전체"
        self.on_back = on_back
        self._build()

    def _build(self):
        self.controls.clear()
        self.controls.append(self._build_header())
        self.controls.append(self._build_filters())
        self.controls.append(self._build_list())

    def _build_header(self):
        team_tabs = []
        for t in self.teams:
            sel = t["id"] == self.selected_team_id
            team_tabs.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                content=ft.Text(":)", size=12, color=TEXT_DARK),
                                width=24,
                                height=24,
                                bgcolor=TEAM_COLORS[t["color_code"]],
                                border=ft.Border.all(2, TEXT_DARK),
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Text(
                                f"{t['name']}팀",
                                color=TEXT_LIGHT,
                                size=12,
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                        spacing=6,
                    ),
                    bgcolor=TEAM_COLORS[t["color_code"]] if sel else "#5A4632",
                    border=ft.Border.all(
                        2 if sel else 1, TEXT_GOLD if sel else TEXT_DARK
                    ),
                    padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                    data=t["id"],
                    on_click=self._on_team_click,
                )
            )
        sel_team = next(
            (t for t in self.teams if t["id"] == self.selected_team_id),
            self.teams[0] if self.teams else None,
        )
        balance_text = (
            format_won(int(sel_team["current_balance"])) if sel_team else "₩0"
        )
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Icon(
                                            ft.Icons.ARROW_BACK_IOS,
                                            color=TEXT_LIGHT,
                                            size=16,
                                        ),
                                        ft.Text(
                                            "BACK",
                                            color=TEXT_LIGHT,
                                            size=14,
                                            weight=ft.FontWeight.W_500,
                                        ),
                                    ],
                                    spacing=4,
                                ),
                                on_click=lambda e: self.on_back(),
                                padding=8,
                            ),
                            ft.Text(
                                "📜 자금 흐름",
                                color=TEXT_LIGHT,
                                size=20,
                                weight=ft.FontWeight.W_500,
                            ),
                            ft.Container(expand=True),
                            ft.Text("현재 잔액", color=TEXT_MUTED, size=12),
                            ft.Text(
                                balance_text,
                                color=TEXT_GOLD,
                                size=16,
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                        spacing=12,
                    ),
                    ft.Row(team_tabs, spacing=8, scroll=ft.ScrollMode.AUTO),
                ],
                spacing=10,
            ),
            bgcolor=BG_PANEL,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        )

    def _build_filters(self):
        filters = []
        for f in EVENT_FILTERS:
            sel = f == self.active_filter
            filters.append(
                ft.Container(
                    content=ft.Text(
                        f, color=TEXT_LIGHT, size=13, weight=ft.FontWeight.W_500
                    ),
                    bgcolor=BG_BUTTON if sel else "#9A9A9A",
                    border=ft.Border.all(2, TEXT_DARK),
                    width=100,
                    height=40,
                    alignment=ft.Alignment.CENTER,
                    data=f,
                    on_click=self._on_filter_click,
                )
            )
        return ft.Container(
            content=ft.Row(
                [
                    *filters,
                    ft.Container(expand=True),
                    ft.Text("▼ 최신순", size=12, color=TEXT_MUTED),
                ],
                spacing=10,
            ),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _build_list(self):
        df = self.svc.get_team_history(self.selected_team_id, self.active_filter)
        rows = []
        if len(df) == 0:
            rows.append(
                ft.Container(
                    content=ft.Text(
                        "거래/룰렛 기록이 없습니다.", size=14, color=TEXT_MUTED
                    ),
                    padding=20,
                    alignment=ft.Alignment.CENTER,
                )
            )
        else:
            for _, row in df.iterrows():
                rows.append(self._history_card(row))
        return ft.Container(
            content=ft.Container(
                content=ft.Column(rows, spacing=10),
                bgcolor="#F5EDD8",
                border=ft.Border.all(3, "#5A4632"),
                padding=16,
            ),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _history_card(self, row):
        et = row["event_type"]
        meta = EVENT_META.get(et, {"icon": "📦", "bar": "#999"})
        amount = int(row["amount"])
        if et == "TRADE":
            title = f"상품 판매 — {row['detail']} × {int(row['quantity'])}"
        elif et == "ROULETTE_COST":
            title = "룰렛 비용 — 직접 룰렛 돌림"
        else:
            title = f"룰렛 손실 — {row['detail']}"
        try:
            time_str = row["event_at"].strftime("%Y-%m-%d %H:%M")
        except Exception:
            time_str = str(row["event_at"])
        amount_color = ACCENT_GREEN_DARK if amount >= 0 else ACCENT_RED
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(width=6, height=60, bgcolor=meta["bar"]),
                    ft.Container(
                        content=ft.Text(meta["icon"], size=28),
                        width=56,
                        height=56,
                        bgcolor="#6B4F2E",
                        border=ft.Border.all(2, "#3E2A14"),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                title,
                                size=15,
                                weight=ft.FontWeight.W_500,
                                color=TEXT_DARK,
                            ),
                            ft.Text(time_str, size=11, color=TEXT_MUTED),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.Text(
                        f"{'+' if amount >= 0 else ''}{format_won(amount)}",
                        size=18,
                        weight=ft.FontWeight.W_500,
                        color=amount_color,
                    ),
                ],
                spacing=12,
            ),
            bgcolor="#FBF4E0",
            border=ft.Border.all(2, "#C4B590"),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        )

    def _on_team_click(self, e):
        self.selected_team_id = e.control.data
        self._build()
        self.update()

    def _on_filter_click(self, e):
        self.active_filter = e.control.data
        self._build()
        self.update()
