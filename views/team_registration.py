"""
views/team_registration.py
팀 등록 화면 (4.2).
"""
import flet as ft
from typing import Callable, List

from theme import (
    BG_PANEL,
    BG_BUTTON,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    TEXT_GOLD,
    ACCENT_RED,
    ACCENT_GREEN_DARK,
    TEAM_COLORS,
    TEAM_COLOR_LABELS,
    TEAM_CARD_BG,
    DEFAULT_INITIAL_BALANCE,
    MIN_TEAMS,
    MAX_TEAMS,
)
from services import TeamService, TeamRegistrationError
from views._helpers import _snack


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
