"""
views/team_selection.py
팀 선택 화면.

팀 등록이 완료된 후, 같은 기기를 여러 명이 공유할 때
각 플레이어가 '본인이 어느 팀인지'를 선택하는 화면이다.
선택된 팀 ID가 state['current_team_id']에 저장되어
이후 거래소·룰렛·자금 흐름에서 '내 팀' 기준으로 동작한다.
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
    """
    게임 시작 후 본인이 어느 팀인지 선택하는 화면.

    DB에서 불러온 팀 목록(teams)을 카드 그리드로 표시하고,
    클릭 시 on_select(team_id) 콜백을 호출한다.
    '팀 등록으로 돌아가기' 버튼은 on_back 콜백을 호출한다.
    """

    def __init__(
        self, teams: list, on_select: Callable[[int], None], on_back: Callable
    ):
        """
        Args:
            teams    : 전체 팀 정보 dict 목록 (team_repo.find_all().to_dict('records'))
            on_select: 팀 카드 클릭 시 호출되는 콜백 (team_id: int 인자 전달)
            on_back  : 뒤로가기(팀 등록 화면으로) 버튼 콜백
        """
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
        """화면 구성요소를 빌드하고 controls에 추가한다."""
        self.controls.clear()
        self.controls.append(self._build_header())
        self.controls.append(ft.Container(height=20))  # 헤더 아래 여백
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
        self.controls.append(ft.Container(height=10))  # 설명 아래 여백
        self.controls.append(self._build_team_grid())
        self.controls.append(ft.Container(height=10))  # 그리드 아래 여백
        self.controls.append(self._build_back_button())

    def _build_header(self):
        """
        상단 헤더: 게임 타이틀 + 'PLAYER SELECT / 내 팀 선택' 부제목.
        팀 등록 화면과 동일한 헤더 레이아웃을 사용한다.
        """
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
            width=10000,  # 전체 너비 확장 (Row 내에서 stretch 효과)
        )

    def _build_team_grid(self):
        """
        각 팀의 선택 카드를 wrap=True Row로 배치한다.
        팀 수가 많을 때 자동으로 다음 줄로 넘어간다.
        """
        cards = [self._team_card(t) for t in self.teams]
        return ft.Container(
            content=ft.Row(
                cards,
                spacing=16,
                wrap=True,  # 카드가 많으면 다음 줄로 넘김
                alignment=ft.MainAxisAlignment.CENTER,
                run_spacing=16,  # 줄 사이 간격
            ),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _team_card(self, team):
        """
        팀 정보를 보여주는 선택 카드 컴포넌트.

        카드 상단: 팀 색상 배경 + 팀 이름
        카드 하단: 아바타(':)') + 슬로건 + 현재 잔액
        클릭 이벤트: _on_team_click → on_select(team_id)
        """
        cc = team["color_code"]  # 팀 색상 코드 (예: 'YELLOW')
        return ft.Container(
            content=ft.Column(
                [
                    # ── 카드 상단: 팀 이름 헤더 (팀 색상 배경) ──
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
                    # ── 카드 하단: 아바타 + 슬로건 + 잔액 ──
                    ft.Container(
                        content=ft.Column(
                            [
                                # 팀 아바타 (픽셀 아트 스타일 ':)' 이모티콘)
                                ft.Container(
                                    content=ft.Text(":)", size=44, color=TEXT_DARK),
                                    width=100,
                                    height=100,
                                    bgcolor=TEAM_COLORS[cc],
                                    border=ft.Border.all(3, TEXT_DARK),
                                    alignment=ft.Alignment.CENTER,
                                ),
                                ft.Container(height=8),
                                # 팀 슬로건 (이탤릭 + 따옴표)
                                ft.Text(
                                    f'"{team.get("slogan", "")}"',
                                    size=12,
                                    italic=True,
                                    color=TEXT_MUTED,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                # 현재 잔액 (정확한 원화 표시)
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
            bgcolor=TEAM_CARD_BG[cc],  # 카드 배경: 팀 색상의 연한 버전
            border=ft.Border.all(2, TEXT_DARK),
            border_radius=4,
            width=200,
            ink=True,  # 클릭 시 잉크 효과
            data=team["id"],  # 카드에 team_id를 data로 저장
            on_click=self._on_team_click,
        )

    def _on_team_click(self, e):
        """팀 카드 클릭 시 해당 팀의 id를 on_select 콜백에 전달한다."""
        self.on_select(e.control.data)  # e.control.data = team["id"]

    def _build_back_button(self):
        """'팀 등록으로 돌아가기' 버튼. 클릭 시 on_back 콜백을 호출한다."""
        return ft.Container(
            content=ft.Text(
                "↺ 팀 등록으로 돌아가기",
                color=TEXT_LIGHT,
                size=13,
                weight=ft.FontWeight.W_500,
            ),
            bgcolor="#9A9A9A",  # 회색 — 보조 동작
            border=ft.Border.all(2, TEXT_DARK),
            width=240,
            height=40,
            alignment=ft.Alignment.CENTER,
            on_click=lambda e: self.on_back(),
        )
