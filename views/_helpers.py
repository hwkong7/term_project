"""
views/_helpers.py
공통 헬퍼 함수.
"""

import flet as ft
from theme import TEXT_LIGHT


def _snack(page: ft.Page, msg: str, bgcolor: str):
    """flet 0.85 SnackBar"""
    page.show_dialog(
        ft.SnackBar(content=ft.Text(msg, color=TEXT_LIGHT), bgcolor=bgcolor)
    )
