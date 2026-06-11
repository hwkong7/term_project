"""
views/dialogs.py
파산 다이얼로그.
"""
import flet as ft
from typing import Callable, Optional

from theme import (
    TEXT_LIGHT,
    TEXT_GOLD,
    TEXT_DARK,
    TEXT_MUTED,
    ACCENT_RED,
    TEAM_COLORS,
    BG_PANEL,
    format_won,
)


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


def show_winner_dialog(
    page: ft.Page,
    team_name: str,
    final_balance: int,
    winner_image_path: Optional[str],
    on_new_game: Callable = None,
):
    """마지막 생존 팀에게 표시되는 우승 축하 다이얼로그.
    system_image 테이블의 key='WINNER' 경로 이미지를 표시한다."""

    def close_and_new_game(e):
        dlg.open = False
        page.update()
        if on_new_game:
            on_new_game()

    if winner_image_path:
        image_widget = ft.Image(
            src=winner_image_path,
            width=500,
            height=320,
            fit=ft.BoxFit.CONTAIN,
            error_content=ft.Text(
                "🏆 우승!", size=48, weight=ft.FontWeight.BOLD, color=TEXT_GOLD
            ),
        )
    else:
        image_widget = ft.Text(
            "🏆 우승!", size=48, weight=ft.FontWeight.BOLD, color=TEXT_GOLD
        )

    dlg = ft.AlertDialog(
        modal=True,
        bgcolor="#1A1A1A",
        content=ft.Container(
            content=ft.Column(
                [
                    image_widget,
                    ft.Container(height=8),
                    ft.Text(
                        f"🏆 {team_name}팀 우승!",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_GOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        f"최종 잔액: {format_won(final_balance)}",
                        size=16,
                        color=TEXT_LIGHT,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "모든 팀을 파산시키고 최후의 생존자가 되었습니다!",
                        size=12,
                        color=TEXT_MUTED,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
            width=560,
            padding=20,
        ),
        actions=[
            ft.Container(
                content=ft.Text(
                    "새 게임 시작", color=TEXT_DARK, size=16, weight=ft.FontWeight.W_500
                ),
                bgcolor=TEXT_GOLD,
                border=ft.Border.all(3, TEXT_DARK),
                padding=ft.Padding.symmetric(horizontal=40, vertical=12),
                on_click=close_and_new_game,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )
    page.show_dialog(dlg)
