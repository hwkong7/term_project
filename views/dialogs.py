"""
views/dialogs.py
파산 다이얼로그 + 우승 다이얼로그.

게임 중 특별한 상황(파산 또는 우승 확정)이 발생했을 때
화면 중앙에 모달 팝업으로 표시되는 다이얼로그 함수들을 정의한다.

다이얼로그에 표시할 이미지 경로는 system_image 테이블에서 가져오며,
이미지 파일이 없거나 경로가 None이면 이모지 텍스트로 대체된다(폴백 처리).
"""

import flet as ft
from typing import Callable, Optional

from theme import (
    TEXT_LIGHT,
    TEXT_GOLD,
    TEXT_DARK,
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
    """
    잔액이 0 이하가 된 팀에게 표시되는 파산 알림 다이얼로그.

    RouletteView._animate() → main.on_bankrupt → 이 함수 순으로 호출된다.
    '확인' 버튼을 누르면 on_confirm 콜백이 실행되고 다이얼로그가 닫힌다.

    Args:
        page               : 현재 Flet 페이지
        team_name          : 파산한 팀 이름 (다이얼로그 하단에 표시)
        bankrupt_image_path: DB에서 조회한 파산 이미지 경로 (없으면 None)
        on_confirm         : 확인 버튼 클릭 시 호출할 콜백 (선택)
    """

    def close_dialog(e):
        """'확인' 버튼 클릭 시 다이얼로그를 닫고 on_confirm을 실행한다."""
        dlg.open = False    # Flet 0.85.x: page.close() 대신 open=False + update()
        page.update()
        if on_confirm:
            on_confirm()

    # 이미지 경로가 있으면 ft.Image, 없으면 이모지 텍스트로 폴백
    if bankrupt_image_path:
        image_widget = ft.Image(
            src=bankrupt_image_path,     # assets/ 기준 상대 경로 (DB에서 조회)
            width=500,
            height=320,
            fit=ft.BoxFit.CONTAIN,       # 비율 유지하며 컨테이너에 맞춤
            error_content=ft.Text(       # 이미지 로드 실패 시 표시할 폴백 텍스트
                "💀 파산당했습니다.. 💀",
                size=32,
                weight=ft.FontWeight.BOLD,
                color=ACCENT_RED,
            ),
        )
    else:
        # 이미지 경로 자체가 없을 경우 이모지로 대체
        image_widget = ft.Text(
            "💀 파산당했습니다.. 💀",
            size=32,
            weight=ft.FontWeight.BOLD,
            color=ACCENT_RED,
        )

    # 파산 다이얼로그 정의
    dlg = ft.AlertDialog(
        modal=True,               # 모달: 다이얼로그 외부 클릭 불가
        bgcolor="#1A1A1A",        # 어두운 배경으로 심각한 분위기 연출
        content=ft.Container(
            content=ft.Column(
                [
                    image_widget,              # 파산 이미지 또는 이모지
                    ft.Container(height=12),   # 이미지와 텍스트 사이 여백
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
                tight=True,   # 컬럼 높이를 내용에 맞게 자동 조절
            ),
            width=540,
            padding=20,
        ),
        actions=[
            # '확인' 버튼 — 클릭 시 close_dialog 실행
            ft.Container(
                content=ft.Text(
                    "확인", color=TEXT_DARK, size=16, weight=ft.FontWeight.W_500
                ),
                bgcolor=TEAM_COLORS["YELLOW"],        # 노란색 버튼으로 주목도 높임
                border=ft.Border.all(3, TEXT_DARK),
                padding=ft.Padding.symmetric(horizontal=40, vertical=12),
                on_click=close_dialog,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,   # 버튼 중앙 정렬
    )
    page.show_dialog(dlg)   # 다이얼로그 표시


def show_winner_dialog(
    page: ft.Page,
    team_name: str,
    final_balance: int,
    winner_image_path: Optional[str],
    on_new_game: Callable = None,
):
    """
    마지막 생존 팀에게 표시되는 우승 축하 다이얼로그.
    system_image 테이블에서 key='WINNER'로 조회한 이미지 경로를 사용한다.

    RouletteView._animate() → main.on_winner → 이 함수 순으로 호출된다.
    '새 게임 시작' 버튼을 누르면 main.reset_game()이 실행된다.

    Args:
        page              : 현재 Flet 페이지
        team_name         : 우승 팀 이름
        final_balance     : 우승 팀의 최종 잔액 (원 단위)
        winner_image_path : DB에서 조회한 우승 이미지 경로 (없으면 None)
        on_new_game       : '새 게임 시작' 버튼 클릭 시 호출할 콜백 (선택)
    """

    def close_dialog(e):
        """'새 게임 시작' 버튼 클릭 시 다이얼로그를 닫고 on_new_game을 실행한다."""
        dlg.open = False   # Flet 0.85.x: open=False + update()로 닫음
        page.update()
        if on_new_game:
            on_new_game()   # 새 게임 시작 (DB 초기화 → 팀 등록 화면)

    # 이미지 경로가 있으면 ft.Image, 없으면 이모지 텍스트로 폴백
    if winner_image_path:
        image_widget = ft.Image(
            src=winner_image_path,   # DB에서 조회한 경로 (assets/winner.png 등)
            width=500,
            height=320,
            fit=ft.BoxFit.CONTAIN,   # 비율 유지하며 컨테이너에 맞춤
            error_content=ft.Text(   # 이미지 로드 실패 시 폴백
                "🏆 우승!",
                size=48,
                weight=ft.FontWeight.BOLD,
                color=TEXT_GOLD,
            ),
        )
    else:
        # 이미지 경로가 None이면 이모지로 대체
        image_widget = ft.Text(
            "🏆 우승!",
            size=48,
            weight=ft.FontWeight.BOLD,
            color=TEXT_GOLD,
        )

    # 우승 다이얼로그 정의
    dlg = ft.AlertDialog(
        modal=True,          # 모달: 다이얼로그 외부 클릭 불가
        bgcolor="#1A1A1A",   # 어두운 배경
        content=ft.Container(
            content=ft.Column(
                [
                    image_widget,              # 우승 이미지 또는 이모지
                    ft.Container(height=12),   # 여백
                    ft.Text(
                        f"🏆 {team_name}팀 우승!",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_GOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        f"최종 잔액: {format_won(final_balance)}",   # 정확한 금액 표시
                        size=16,
                        color=TEXT_LIGHT,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "모든 팀을 파산시키고 최후의 생존자가 되었습니다!",
                        size=13,
                        color="#AAAAAA",   # 흐린 회색 — 부가 설명
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
            width=540,
            padding=20,
        ),
        actions=[
            # '새 게임 시작' 버튼 — 클릭 시 close_dialog → on_new_game(reset_game) 실행
            ft.Container(
                content=ft.Text(
                    "새 게임 시작", color=TEXT_DARK, size=16, weight=ft.FontWeight.W_500
                ),
                bgcolor=TEXT_GOLD,              # 황금색 버튼으로 우승 분위기 연출
                border=ft.Border.all(3, TEXT_DARK),
                padding=ft.Padding.symmetric(horizontal=40, vertical=12),
                on_click=close_dialog,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )
    page.show_dialog(dlg)   # 다이얼로그 표시
