"""
views/dashboard.py
대시보드 화면 (4.6).
"""
import flet as ft
from typing import Callable

from theme import (
    BG_PANEL,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    TEXT_GOLD,
    ACCENT_RED,
    ACCENT_GREEN_DARK,
    ACCENT_ORANGE,
    TEAM_COLORS,
    TEAM_CARD_BG,
    format_won,
    format_won_man,
)
from services import DashboardService


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
