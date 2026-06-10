"""
views/history.py
자금 흐름 화면 (4.5).
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
    TEAM_COLORS,
    format_won,
)
from services import HistoryService


EVENT_FILTERS = ["전체", "판매만", "룰렛만"]
EVENT_META = {
    "TRADE": {"icon": "📦", "bar": ACCENT_GREEN_DARK},
    "ROULETTE_COST": {"icon": "🎲", "bar": ACCENT_RED},
    "ROULETTE_LOSS": {"icon": "🎲", "bar": ACCENT_RED},
}


class HistoryView(ft.Column):
    def __init__(self, history_service: HistoryService, teams, current_team_id, on_back):
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
                    bgcolor="#5A3F1F" if sel else "#9A9A9A",
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
