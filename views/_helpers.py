"""
views/_helpers.py
공통 헬퍼 함수.

뷰 계층 전반에서 반복적으로 사용되는 유틸리티 함수를 모아 둔 모듈.
현재는 스낵바 표시 함수(_snack)만 포함되어 있으나,
향후 공통 UI 컴포넌트 생성 함수 등을 추가할 수 있다.
"""

import flet as ft
from theme import TEXT_LIGHT


def _snack(page: ft.Page, msg: str, bgcolor: str):
    """
    Flet 0.85.x 방식의 SnackBar(하단 알림 바)를 표시하는 헬퍼 함수.

    뷰 전반에서 성공·오류 메시지를 동일한 방식으로 표시하기 위해 사용된다.
    뷰 내부에서 직접 ft.SnackBar를 작성하는 대신 이 함수를 호출한다.

    Args:
        page   : 현재 Flet 페이지 객체 (page.show_dialog()를 통해 표시)
        msg    : 스낵바에 표시할 메시지 문자열
        bgcolor: 스낵바 배경색 (예: ACCENT_GREEN_DARK, ACCENT_RED)

    사용 예:
        _snack(self.page, "✅ 거래 완료!", ACCENT_GREEN_DARK)
        _snack(self.page, "⚠ 잔액 부족", ACCENT_RED)
    """
    page.show_dialog(
        ft.SnackBar(
            content=ft.Text(msg, color=TEXT_LIGHT),   # 흰색 텍스트
            bgcolor=bgcolor                            # 성공=초록, 오류=빨강 등
        )
    )
