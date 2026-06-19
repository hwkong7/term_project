"""
views/team_registration.py
팀 등록 화면 (4.2).

게임 시작 전 2~6팀의 정보(이름, 색상, 슬로건, 초기 잔액)를 입력받는 화면.
각 팀 정보는 TeamCard 컴포넌트로 표현되며,
'게임 시작' 버튼을 누르면 TeamService.create_teams()가 호출되어 DB에 저장된다.
"""

import flet as ft
from typing import Callable, List

from theme import (
    BG_PANEL,
    BG_BUTTON,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    TEXT_GOLD,
    ACCENT_RED,
    ACCENT_GREEN_DARK,
    TEAM_COLORS,
    TEAM_COLOR_LABELS,
    TEAM_CARD_BG,
    DEFAULT_INITIAL_BALANCE,
    MIN_TEAMS,
    MAX_TEAMS,
)
from service import TeamService, TeamRegistrationError
from views._helpers import _snack


# 팀 등록 화면에서 기본으로 채워지는 6팀 프리셋
# 파산게임 유튜브 컨텐츠에서 실제로 등장하는 팀 이름을 사용
DEFAULT_PRESETS = [
    {"name": "양띵", "color": "YELLOW", "slogan": "우승하자!"},
    {"name": "콩콩", "color": "BLUE", "slogan": "콩콩이팀"},
    {"name": "신혜원", "color": "PINK", "slogan": "끝까지간다"},
    {"name": "악어", "color": "GREEN", "slogan": "악어다!"},
    {"name": "팀5", "color": "PURPLE", "slogan": "도전!"},
    {"name": "팀6", "color": "ORANGE", "slogan": "파이팅!"},
]


class TeamCard(ft.Container):
    """
    팀 정보 입력 카드 컴포넌트.

    각 팀마다 하나씩 생성되며, 다음 입력 필드를 포함한다:
      - name_field   : 팀 이름 TextField
      - slogan_field : 슬로건 TextField
      - balance_field: 초기 잔액 TextField (숫자 키보드)
      - 색상 선택 버튼 행 (6가지 색상 중 1개 선택)

    색상 선택 시 on_color_change 콜백을 통해
    다른 TeamCard와 색상이 중복되지 않도록 교환 처리한다.
    """

    def __init__(self, index, preset, on_color_change):
        """
        Args:
            index          : 팀 순서 인덱스 (0부터 시작)
            preset         : 기본값 딕셔너리 {'name', 'color', 'slogan'}
            on_color_change: 색상 선택 시 호출되는 콜백 (idx, old_color, new_color)
        """
        self.index = index
        self.selected_color = preset["color"]  # 현재 선택된 색상 코드
        self.on_color_change = on_color_change

        # ── 입력 필드 생성 ──
        self.name_field = ft.TextField(
            value=preset["name"],
            label="팀 이름",
            text_size=14,
            border_color=TEXT_DARK,
            bgcolor=ft.Colors.WHITE,
            color=TEXT_DARK,
            label_style=ft.TextStyle(color=TEXT_MUTED, size=11),
        )
        self.slogan_field = ft.TextField(
            value=preset["slogan"],
            label="슬로건",
            text_size=13,
            border_color=TEXT_DARK,
            bgcolor=ft.Colors.WHITE,
            color=TEXT_DARK,
            label_style=ft.TextStyle(color=TEXT_MUTED, size=11),
        )
        self.balance_field = ft.TextField(
            value=str(DEFAULT_INITIAL_BALANCE),  # 기본값: 1,000만 원
            label="초기 잔액 (원)",
            text_size=13,
            keyboard_type=ft.KeyboardType.NUMBER,  # 숫자 키보드
            border_color=TEXT_DARK,
            bgcolor=ft.Colors.WHITE,
            color=TEXT_DARK,
            label_style=ft.TextStyle(color=TEXT_MUTED, size=11),
        )

        # ── 색상 선택 버튼 행 빌드 ──
        self.color_buttons_row = self._build_color_buttons()

        # ── 카드 헤더 (팀 번호 + 팀 색상 배경) ──
        self.header = ft.Container(
            content=ft.Text(
                f"팀 {index + 1}", size=14, weight=ft.FontWeight.W_500, color=TEXT_LIGHT
            ),
            bgcolor=TEAM_COLORS[self.selected_color],  # 선택된 팀 색상으로 배경 설정
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        )

        # ── 부모 Container 초기화 ──
        # 이 클래스 자체가 ft.Container이므로 __init__ 마지막에 super().__init__()으로
        # 카드 전체 레이아웃(헤더 + 입력 폼)을 구성한다
        super().__init__(
            content=ft.Column(
                [
                    self.header,
                    ft.Container(
                        content=ft.Column(
                            [
                                self.name_field,
                                self.slogan_field,
                                ft.Text(
                                    "대표 색상",
                                    size=11,
                                    weight=ft.FontWeight.W_500,
                                    color=TEXT_MUTED,
                                ),
                                self.color_buttons_row,  # 6개 색상 선택 버튼
                                self.balance_field,
                            ],
                            spacing=10,
                        ),
                        padding=12,
                    ),
                ],
                spacing=0,
            ),
            bgcolor=TEAM_CARD_BG[self.selected_color],  # 카드 배경: 팀 색상의 연한 버전
            border=ft.Border.all(2, TEXT_DARK),
            border_radius=4,
            width=240,
        )

    def _build_color_buttons(self):
        """
        6가지 팀 색상 선택 버튼을 Row로 빌드한다.
        현재 선택된 색상의 버튼은 테두리가 두껍게(3px) 표시된다.
        """
        buttons = []
        for code, hex_val in TEAM_COLORS.items():
            sel = code == self.selected_color
            buttons.append(
                ft.Container(
                    content=ft.Container(width=24, height=24, bgcolor=hex_val),
                    border=ft.Border.all(
                        3 if sel else 1, TEXT_DARK
                    ),  # 선택된 색상: 두꺼운 테두리
                    padding=2,
                    tooltip=TEAM_COLOR_LABELS[code],  # 마우스 오버 시 한글 색상명 표시
                    data=code,  # 버튼에 색상 코드를 data로 저장
                    on_click=self._on_color_click,
                )
            )
        return ft.Row(buttons, spacing=6)

    def _on_color_click(self, e):
        """
        색상 버튼 클릭 이벤트 핸들러.
        1. 현재 카드의 선택 색상을 업데이트하고 헤더·배경색을 변경한다.
        2. on_color_change 콜백으로 다른 카드에 색상 중복 교환을 요청한다.
        """
        new_c = e.control.data  # 클릭된 버튼의 색상 코드
        old_c = self.selected_color

        # 선택된 색상 코드 갱신
        self.selected_color = new_c

        # 카드 헤더 색상 변경
        self.header.bgcolor = TEAM_COLORS[new_c]

        # 카드 배경색 변경 (연한 버전)
        self.bgcolor = TEAM_CARD_BG[new_c]

        # 색상 선택 버튼들의 테두리 두께 갱신 (선택된 것만 굵게)
        for btn in self.color_buttons_row.controls:
            btn.border = ft.Border.all(3 if btn.data == new_c else 1, TEXT_DARK)

        # 다른 카드와의 색상 중복 교환 요청
        self.on_color_change(self.index, old_c, new_c)

        self.update()  # UI 갱신

    def to_dict(self):
        """
        현재 카드의 입력값을 딕셔너리로 변환해 반환한다.
        TeamRegistrationView._on_start_click() 에서 TeamService.create_teams()에 전달.
        잔액 파싱 실패 시 0으로 처리 (서비스 계층에서 유효성 검사 후 오류 발생).
        """
        try:
            balance = int(self.balance_field.value or 0)
        except ValueError:
            balance = 0  # 숫자가 아닌 문자열이 입력된 경우 0으로 처리
        return {
            "name": (self.name_field.value or "").strip(),
            "color_code": self.selected_color,
            "slogan": (self.slogan_field.value or "").strip(),
            "icon_path": None,  # 아이콘 이미지 경로 (현재 미구현)
            "initial_balance": balance,
        }


class TeamRegistrationView(ft.Column):
    """
    팀 등록 화면 전체 레이아웃.

    구성:
      1. 헤더 (게임 타이틀 + 부제목)
      2. 참여 팀 수 선택 버튼 (2~6팀)
      3. TeamCard 가로 스크롤 행
      4. 하단 버튼 (초기화 / 게임 시작)
    """

    def __init__(self, team_service: TeamService, on_register_success: Callable):
        """
        Args:
            team_service        : 팀 등록 비즈니스 로직 서비스
            on_register_success : 등록 성공 시 호출되는 콜백 (→ 팀 선택 화면)
        """
        super().__init__(spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)
        self.team_service = team_service
        self.on_register_success = on_register_success
        self.team_count = 4  # 기본 참여 팀 수: 4팀
        self.team_cards: List[TeamCard] = []  # 현재 표시 중인 TeamCard 목록
        self._build()

    def _build(self):
        """화면을 구성하는 모든 컨트롤을 빌드하고 controls에 추가한다."""
        self.controls.clear()
        self.controls.append(self._build_header())
        self.controls.append(self._build_team_count_selector())
        self.controls.append(self._build_team_cards_row())
        self.controls.append(self._build_bottom_buttons())

    def _build_header(self):
        """상단 헤더: 게임 타이틀(파산게임 시뮬레이터) + 부제목(GAME SETUP / 팀 등록)."""
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
                                "GAME SETUP / 팀 등록",
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
        )

    def _build_team_count_selector(self):
        """
        참여 팀 수 선택 버튼 행 (MIN_TEAMS=2 ~ MAX_TEAMS=6).
        현재 선택된 팀 수의 버튼은 활성 색상(BG_BUTTON)으로 표시되고
        체크 표시(✓)가 추가된다.
        """
        buttons = []
        for n in range(MIN_TEAMS, MAX_TEAMS + 1):
            sel = n == self.team_count
            buttons.append(
                ft.Container(
                    content=ft.Text(
                        f"{n}팀{'  ✓' if sel else ''}",  # 선택된 팀 수에는 ✓ 표시
                        color=TEXT_LIGHT,
                        size=14,
                        weight=ft.FontWeight.W_500,
                    ),
                    bgcolor=BG_BUTTON
                    if sel
                    else "#9A9A9A",  # 선택: 활성색 / 미선택: 회색
                    border=ft.Border.all(2, TEXT_DARK),
                    width=85,
                    height=36,
                    alignment=ft.Alignment.CENTER,
                    data=n,  # 버튼에 팀 수를 data로 저장
                    on_click=self._on_team_count_click,
                )
            )
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                width=4, height=20, bgcolor=TEXT_DARK
                            ),  # 왼쪽 강조 바
                            ft.Text(
                                "참여 팀 수",
                                size=15,
                                weight=ft.FontWeight.W_500,
                                color=TEXT_DARK,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Row(buttons, spacing=8),
                ],
                spacing=10,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
        )

    def _build_team_cards_row(self):
        """
        team_count 수만큼 TeamCard를 생성하고 가로 스크롤 Row로 배치한다.
        팀 수가 변경될 때마다 _build()가 호출되어 카드 목록이 재생성된다.
        """
        # team_count 수만큼 TeamCard 생성 (DEFAULT_PRESETS에서 순서대로 프리셋 적용)
        self.team_cards = [
            TeamCard(i, DEFAULT_PRESETS[i], self._on_color_change)
            for i in range(self.team_count)
        ]
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(width=4, height=20, bgcolor=TEXT_DARK),
                            ft.Text(
                                "팀 정보 입력",
                                size=15,
                                weight=ft.FontWeight.W_500,
                                color=TEXT_DARK,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        self.team_cards,
                        spacing=12,
                        scroll=ft.ScrollMode.AUTO,  # 카드가 많을 때 가로 스크롤
                    ),
                ],
                spacing=10,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
        )

    def _build_bottom_buttons(self):
        """
        하단 버튼 행 빌드:
          - 초기화(↺): 팀 수를 4로 되돌리고 프리셋 값으로 초기화
          - 게임 시작(▶): TeamService에 등록 요청
        """
        reset_btn = ft.Container(
            content=ft.Text(
                "↺ 초기화", color=TEXT_LIGHT, size=15, weight=ft.FontWeight.W_500
            ),
            bgcolor="#9A9A9A",  # 회색 — 덜 강조되는 보조 동작
            border=ft.Border.all(3, TEXT_DARK),
            height=52,
            expand=1,  # 1:2 비율로 너비 배분 (초기화:시작)
            alignment=ft.Alignment.CENTER,
            on_click=self._on_reset_click,
        )
        start_btn = ft.Container(
            content=ft.Text(
                "▶ 게임 시작", color=TEXT_LIGHT, size=17, weight=ft.FontWeight.W_500
            ),
            bgcolor=ACCENT_RED,  # 빨간색 — 주요 동작 강조
            border=ft.Border.all(3, TEXT_DARK),
            height=52,
            expand=2,  # 1:2 비율 중 더 넓은 쪽
            alignment=ft.Alignment.CENTER,
            on_click=self._on_start_click,
        )
        return ft.Container(
            content=ft.Row([reset_btn, start_btn], spacing=12),
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
        )

    def _on_team_count_click(self, e):
        """팀 수 선택 버튼 클릭 시 team_count를 갱신하고 화면을 재빌드한다."""
        if e.control.data == self.team_count:
            return  # 이미 선택된 팀 수를 다시 클릭한 경우 무시
        self.team_count = e.control.data
        self._build()
        self.update()

    def _on_color_change(self, idx, old_c, new_c):
        """
        팀 색상 교환 로직.
        팀 idx번이 new_c를 선택했을 때, 다른 팀 중 new_c를 사용 중인 팀을 찾아
        그 팀의 색상을 old_c로 교환한다 (색상 중복 방지).
        """
        for i, card in enumerate(self.team_cards):
            if i == idx:
                continue  # 자기 자신은 건너뜀
            if card.selected_color == new_c:
                # 새로운 색상(new_c)을 쓰던 팀을 이전 색상(old_c)으로 교체
                card.selected_color = old_c
                card.header.bgcolor = TEAM_COLORS[old_c]
                card.bgcolor = TEAM_CARD_BG[old_c]
                for btn in card.color_buttons_row.controls:
                    btn.border = ft.Border.all(3 if btn.data == old_c else 1, TEXT_DARK)
                card.update()
                break  # 색상은 중복되지 않으므로 하나 찾으면 종료

    def _on_reset_click(self, e):
        """초기화 버튼: 팀 수를 4로, 각 TeamCard를 DEFAULT_PRESETS로 초기화."""
        self.team_count = 4
        self._build()
        self.update()

    def _on_start_click(self, e):
        """
        게임 시작 버튼: 모든 TeamCard의 입력값을 수집해 TeamService에 전달한다.
        성공 시 on_register_success 콜백(→ 팀 선택 화면)을 호출한다.
        실패 시 오류 메시지를 스낵바로 표시한다.
        """
        # 각 TeamCard의 to_dict()로 입력값을 수집
        teams_data = [c.to_dict() for c in self.team_cards]
        try:
            self.team_service.create_teams(teams_data)  # DB에 저장
            _snack(
                self.page, f"✅ {len(teams_data)}개 팀 등록 완료!", ACCENT_GREEN_DARK
            )
            self.on_register_success()  # 팀 선택 화면으로 이동
        except TeamRegistrationError as ex:
            # 유효성 검사 실패 (이름 중복, 잔액 부족 등)
            _snack(self.page, f"⚠ {ex}", ACCENT_RED)
        except Exception as ex:
            # 예상치 못한 오류
            _snack(self.page, f"⚠ 오류: {ex}", ACCENT_RED)
