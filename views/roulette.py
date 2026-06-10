"""
views/roulette.py
룰렛 화면 (4.4) — 슬롯머신 애니메이션.
"""
import flet as ft
import threading
import time
from typing import Callable, List

from theme import (
    BG_PANEL,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    TEXT_GOLD,
    ACCENT_RED,
    TEAM_COLORS,
    format_won,
    format_won_man,
)
from services import RouletteService, RouletteError, SPIN_COST
from views._helpers import _snack


class SlotReel(ft.Container):
    """슬롯머신 한 칸 — Stack 안에서 위로 움직이는 띠"""

    def __init__(
        self, width: int, height: int, items: List[str], color: str = TEXT_DARK
    ):
        self.item_height = height
        self.items = items
        self.text_color = color

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

        self.strip = ft.Column(
            controls=self.text_controls,
            spacing=0,
            tight=True,
        )

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

    def reset_instant(self):
        """애니메이션 없이 즉시 top=0으로 리셋"""
        self.strip_container.animate_position = ft.Animation(1, ft.AnimationCurve.LINEAR)
        self.strip_container.top = 0
        self.strip_container.update()

    def get_text(self, index: int) -> str:
        return self.items[index % len(self.items)]


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
        team_names = [t["name"] for t in self._all_teams]
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
        self.spin_button.bgcolor = "#555555"
        self.spin_button.content = ft.Text(
            "⏳ SPINNING...", color="#AAAAAA", size=18, weight=ft.FontWeight.W_500
        )
        self.team_status.value = "SPINNING..."
        self.team_status.color = TEXT_MUTED
        self.amount_status.value = "CALCULATING..."
        self.amount_status.color = TEXT_MUTED
        self.spin_button.update()
        self.team_status.update()
        self.amount_status.update()

        threading.Thread(target=self._animate, args=(result,), daemon=True).start()

    def _animate(self, result):
        # 0. 이전 위치 즉시 리셋 (역방향 방지)
        self.team_reel.reset_instant()
        self.amount_reel.reset_instant()
        time.sleep(0.08)  # 리셋 렌더링 대기

        # 결과 인덱스 계산
        team_names = [t["name"] for t in self._all_teams]
        target_team_idx = team_names.index(result["target_name"])
        team_target_index = 6 * len(team_names) + target_team_idx

        amount_labels = [
            format_won_man(a)
            for a in [500_000, 800_000, 1_000_000, 1_500_000, 2_000_000, 2_500_000, 3_000_000]
        ]
        amount_target_idx = amount_labels.index(format_won_man(result["penalty_amount"]))
        amount_target_index = 6 * len(amount_labels) + amount_target_idx

        # 1단계: 빠르게 (EASE_IN으로 가속감)
        self.team_reel.set_position(team_target_index - 6, duration_ms=1000, curve=ft.AnimationCurve.EASE_IN)
        self.amount_reel.set_position(amount_target_index - 8, duration_ms=1200, curve=ft.AnimationCurve.EASE_IN)
        time.sleep(1.1)

        # 2단계: 감속 정지
        self.team_reel.set_position(team_target_index, duration_ms=700, curve=ft.AnimationCurve.DECELERATE)
        time.sleep(0.4)
        self.amount_reel.set_position(amount_target_index, duration_ms=800, curve=ft.AnimationCurve.DECELERATE)
        time.sleep(0.9)

        # 결과 표시
        target_team = self.get_team_info(result["target_team_id"])
        self.team_status.value = f"🎯 {result['target_name']}팀"
        self.team_status.color = ACCENT_RED
        self.amount_status.value = f"💸 {format_won(result['penalty_amount'])} 차감!"
        self.amount_status.color = ACCENT_RED

        # 버튼 재활성화
        self.is_spinning = False
        self.spin_button.content = ft.Text(
            f"🎲 SPIN!  ({format_won_man(SPIN_COST)})",
            color=TEXT_LIGHT, size=20, weight=ft.FontWeight.W_500
        )
        self.spin_button.bgcolor = ACCENT_RED

        try:
            self.controls[2] = self._build_recent()
            self.controls[0] = self._build_header()
            self.spin_button.update()
            self.team_status.update()
            self.amount_status.update()
            self.update()

            _snack(self.page, f"🎰 {result['target_name']}팀 {format_won(result['penalty_amount'])} 차감!", ACCENT_RED)

            if target_team and target_team["current_balance"] <= 0 and self.on_bankrupt:
                time.sleep(0.8)
                self.on_bankrupt(target_team["name"])
        except Exception:
            pass
