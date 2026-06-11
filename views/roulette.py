"""
views/roulette.py
룰렛 화면 (4.4) — async 슬롯머신 애니메이션.

animate_position + 스레드 방식 → async/await + 텍스트 사이클링 방식으로 변경.
Flet 이벤트 루프 위에서 직접 실행하므로 끊김 없이 매끄럽게 동작한다.
"""

import asyncio
import flet as ft
from typing import Callable, List

from theme import (
    BG_PANEL,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    TEXT_GOLD,
    ACCENT_RED,
    ACCENT_ORANGE,
    TEAM_COLORS,
    format_won,
    format_won_man,
)
from services import RouletteService, RouletteError, SPIN_COST
from views._helpers import _snack

# 룰렛 금액 목록
_AMOUNTS = [500_000, 800_000, 1_000_000, 1_500_000, 2_000_000, 2_500_000, 3_000_000]


class _ReelDisplay(ft.Container):
    """슬롯머신 한 칸 — 큰 텍스트를 교체해 사이클링 효과를 낸다."""

    def __init__(self, width: int):
        self._label = ft.Text(
            "???",
            size=38,
            weight=ft.FontWeight.BOLD,
            color=TEXT_DARK,
            text_align=ft.TextAlign.CENTER,
        )
        super().__init__(
            content=ft.Container(
                content=self._label,
                alignment=ft.Alignment.CENTER,
            ),
            width=width,
            height=100,
            bgcolor="#D4C4A0",
            border=ft.Border.all(3, TEXT_GOLD),
            alignment=ft.Alignment.CENTER,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )

    def set_value(self, text: str, color: str = TEXT_DARK):
        self._label.value = text
        self._label.color = color
        self._label.update()

    def flash(self, color: str):
        self.bgcolor = color
        self.update()

    def unflash(self):
        self.bgcolor = "#D4C4A0"
        self.update()


class RouletteView(ft.Column):
    def __init__(
        self,
        roulette_service: RouletteService,
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

        self._all_teams = get_all_teams()
        self._team_names = [t["name"] for t in self._all_teams]
        self._amount_labels = [format_won_man(a) for a in _AMOUNTS]

        self.team_reel = _ReelDisplay(300)
        self.amount_reel = _ReelDisplay(300)

        self.team_status = ft.Text("READY", size=15, color=TEXT_MUTED)
        self.amount_status = ft.Text("READY", size=15, color=TEXT_MUTED)

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
                    width=300,
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

    async def _on_spin_click(self, e):
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
        self.spin_button.bgcolor = "#444444"
        self.spin_button.content = ft.Text(
            "⏳ SPINNING...", color="#AAAAAA", size=18, weight=ft.FontWeight.W_500
        )
        self.team_status.value = ""
        self.amount_status.value = ""
        self.spin_button.update()
        self.team_status.update()
        self.amount_status.update()

        await self._animate(result)

    async def _animate(self, result):
        """
        async 슬롯머신 애니메이션.
        총 30프레임: 처음엔 빠르게(0.04s), 갈수록 느려지다(0.25s) 결과에서 정지.
        마지막 5프레임은 결과값을 보여주며 확실히 감속.
        """
        TOTAL = 30
        SETTLE = 5  # 마지막 N프레임은 결과값 고정

        for i in range(TOTAL):
            # easeOut 커브: 시작 빠름 → 끝 느림
            t = i / (TOTAL - 1)
            delay = 0.04 + (t**2) * 0.22

            if i < TOTAL - SETTLE:
                # 빠르게 순환
                team_val = self._team_names[i % len(self._team_names)]
                amt_val = self._amount_labels[i % len(self._amount_labels)]
                self.team_reel.set_value(team_val, TEXT_DARK)
                self.amount_reel.set_value(amt_val, TEXT_DARK)
            else:
                # 결과값으로 서서히 고정
                self.team_reel.set_value(result["target_name"], TEXT_DARK)
                self.amount_reel.set_value(
                    format_won_man(result["penalty_amount"]), TEXT_DARK
                )

            await asyncio.sleep(delay)

        # 결과 확정 — 3번 깜빡임
        for _ in range(3):
            self.team_reel.set_value(result["target_name"], TEXT_GOLD)
            self.amount_reel.set_value(
                format_won_man(result["penalty_amount"]), ACCENT_RED
            )
            await asyncio.sleep(0.18)
            self.team_reel.set_value(result["target_name"], TEXT_DARK)
            self.amount_reel.set_value(
                format_won_man(result["penalty_amount"]), TEXT_DARK
            )
            await asyncio.sleep(0.12)

        # 최종 색상 고정
        self.team_reel.set_value(result["target_name"], TEXT_GOLD)
        self.amount_reel.set_value(format_won_man(result["penalty_amount"]), ACCENT_RED)

        # 상태 텍스트 표시
        self.team_status.value = f"🎯 {result['target_name']}팀"
        self.team_status.color = TEXT_GOLD
        self.amount_status.value = f"💸 {format_won(result['penalty_amount'])} 차감!"
        self.amount_status.color = ACCENT_RED
        self.team_status.update()
        self.amount_status.update()

        # 버튼 재활성화
        self.is_spinning = False
        self.spin_button.content = ft.Text(
            f"🎲 SPIN!  ({format_won_man(SPIN_COST)})",
            color=TEXT_LIGHT,
            size=20,
            weight=ft.FontWeight.W_500,
        )
        self.spin_button.bgcolor = ACCENT_RED
        self.spin_button.update()

        # 최근 결과 + 헤더 갱신
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
            await asyncio.sleep(0.8)
            self.on_bankrupt(target_team["name"])
