"""
views/team_selection.py
팀 선택 화면.
"""

import flet as ft
from typing import Callable

from theme import (
    BG_PANEL,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    TEXT_GOLD,
    ACCENT_ORANGE,
    TEAM_COLORS,
    TEAM_CARD_BG,
    format_won,
)


class TeamSelectionView(ft.Column):
    """게임 시작 후 본인이 어느 팀인지 선택하는 화면."""

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
