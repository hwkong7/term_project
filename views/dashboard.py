"""
views/dashboard.py
대시보드 화면 (4.6).

게임의 메인 허브 역할을 하는 화면.
요약 카드(거래수/스핀수/총자산), 팀별 상태 카드, 잔액 그래프,
거래소·룰렛·기록 화면으로 이동하는 메뉴 버튼을 표시한다.

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
    ACCENT_ORANGE,
    TEAM_COLORS,
    TEAM_CARD_BG,
    format_won,
    format_won_man,
)
from service import DashboardService


class DashboardView(ft.Column):
    """
    대시보드 화면 최상위 뷰 위젯.

    구성 섹션 (위에서부터 순서대로):
      1. 헤더        : 게임 타이틀 + 라운드 정보 + 내 팀 배지 + 새 게임 버튼
      2. 요약 카드   : TOTAL TRADES / ROULETTE SPINS / TOTAL GOLD
      3. 팀 상황     : 팀별 카드(잔액 변동, HP 게이지, 파산 여부)
      4. 잔액 그래프 : 팀별 잔액을 가로 막대그래프로 시각화
      5. 메뉴 버튼   : 거래소 / 룰렛돌리기 / 기록보기 이동 버튼
    """

    def __init__(
        self,
        dashboard_service: DashboardService,
        current_team_id: int,
        on_goto_marketplace,
        on_goto_roulette,
        on_goto_history,
        on_change_team,
        on_reset_game,
    ):
        super().__init__(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        # 의존성 및 콜백 저장
        self.svc = dashboard_service
        self.current_team_id = current_team_id
        self.on_goto_marketplace = on_goto_marketplace
        self.on_goto_roulette = on_goto_roulette
        self.on_goto_history = on_goto_history
        self.on_change_team = on_change_team
        self.on_reset_game = on_reset_game
        self._build()

    def _build(self):
        """
        화면 전체를 빌드한다.
        DashboardService에서 summary(집계 데이터)와
        teams(파생 컬럼 포함 팀 DataFrame)를 한 번씩 조회한 뒤
        각 섹션 빌드 메서드에 전달한다.
        """
        self.controls.clear()
        summary = self.svc.get_summary()  # 집계 데이터 (거래수, 스핀수, 총 잔액)
        teams = (
            self.svc.get_teams_with_status()
        )  # 파생 컬럼(balance_delta 등) 포함 팀 DataFrame

        self.controls.append(self._build_header(summary))
        self.controls.append(self._build_summary_cards(summary))
        self.controls.append(self._section_label("팀 상황"))
        self.controls.append(self._build_team_cards(teams))
        self.controls.append(self._section_label("BALANCE GRAPH"))
        self.controls.append(self._build_balance_graph(teams))
        self.controls.append(self._build_menu_buttons())

    def _build_header(self, summary):
        """
        상단 헤더를 구성한다.
        좌측: 게임 아이콘 + 타이틀 + 현재 라운드 번호
        우측: 내 팀 배지(색상+이름) + 팀 변경 버튼 + 새 게임(초기화) 버튼
        """
        # 현재 플레이어가 선택한 팀의 최신 정보를 직접 조회
        # (DashboardService가 team_repo를 속성으로 노출하므로 바로 접근 가능)
        my_team = self.svc.team_repo.find_by_id(self.current_team_id)
        return ft.Container(
            content=ft.Row(
                [
                    # 좌측: 게임 아이콘 박스
                    ft.Container(
                        content=ft.Text("📦", size=32),
                        width=56,
                        height=56,
                        bgcolor="#8B5A2B",
                        border=ft.Border.all(3, BG_PANEL),
                        alignment=ft.Alignment.CENTER,
                    ),
                    # 타이틀 + 현재 라운드 정보
                    ft.Column(
                        [
                            ft.Text(
                                "파산게임 시뮬레이터",
                                size=22,
                                weight=ft.FontWeight.W_500,
                                color=TEXT_LIGHT,
                            ),
                            ft.Text(
                                f"ROUND {summary['round_no']} / 진행중",
                                size=11,
                                weight=ft.FontWeight.W_500,
                                color=TEXT_GOLD,
                            ),
                        ],
                        spacing=2,
                    ),
                    ft.Container(
                        expand=True
                    ),  # 가운데 빈 공간 — 우측 요소를 오른쪽 끝으로 밀어냄
                    # 내 팀 정보 배지 (색상 아이콘 + 팀명 + 팀 변경 버튼)
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Text("내 팀:", color=TEXT_MUTED, size=11),
                                # 내 팀 색상을 보여주는 작은 정사각형
                                ft.Container(
                                    width=20,
                                    height=20,
                                    bgcolor=TEAM_COLORS[my_team["color_code"]],
                                    border=ft.Border.all(2, TEXT_DARK),
                                ),
                                ft.Text(
                                    my_team["name"],
                                    color=TEXT_LIGHT,
                                    size=14,
                                    weight=ft.FontWeight.W_500,
                                ),
                                # 팀 변경 버튼 — 클릭 시 팀 선택 화면으로 이동
                                ft.IconButton(
                                    icon=ft.Icons.SWAP_HORIZ,
                                    icon_color=TEXT_GOLD,
                                    icon_size=18,
                                    tooltip="팀 변경",
                                    on_click=lambda e: self.on_change_team(),
                                ),
                            ],
                            spacing=8,
                        ),
                        bgcolor="#5A3F1F",
                        border=ft.Border.all(2, TEXT_GOLD),
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                    ),
                    # 새 게임(초기화) 버튼 — 클릭 시 게임 데이터를 모두 리셋
                    ft.IconButton(
                        icon=ft.Icons.REFRESH,
                        icon_color=TEXT_LIGHT,
                        tooltip="새 게임 (초기화)",
                        on_click=lambda e: self.on_reset_game(),
                    ),
                ],
                spacing=12,
            ),
            bgcolor=BG_PANEL,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        )

    def _build_summary_cards(self, summary):
        """
        요약 카드 3개를 가로로 배치한다.
        각 카드는 _summary_card() 헬퍼로 동일한 레이아웃을 재사용해 생성한다.
        """
        return ft.Container(
            content=ft.Row(
                [
                    self._summary_card(
                        "TOTAL TRADES", str(summary["total_trades"]), TEXT_LIGHT
                    ),
                    self._summary_card(
                        "ROULETTE SPINS", str(summary["roulette_spins"]), TEXT_LIGHT
                    ),
                    # 총 자산은 만원 단위로 축약 표시하고 황금색으로 강조
                    self._summary_card(
                        "TOTAL GOLD", format_won_man(summary["total_gold"]), TEXT_GOLD
                    ),
                ],
                spacing=12,
            ),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _summary_card(self, label, value, value_color):
        """
        단일 요약 카드 컴포넌트.
        상단에 라벨(작은 황금색 텍스트), 하단에 값(큰 텍스트)을 세로로 배치한다.
        expand=True로 3개 카드가 균등하게 가로 폭을 나눠 갖는다.
        """
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        label, size=11, weight=ft.FontWeight.W_500, color=TEXT_GOLD
                    ),
                    ft.Text(
                        value, size=24, weight=ft.FontWeight.W_500, color=value_color
                    ),
                ],
                spacing=4,
            ),
            bgcolor=BG_PANEL,
            border=ft.Border.all(2, BG_PANEL),
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            expand=True,
        )

    def _section_label(self, text):
        """
        섹션 구분용 라벨 ('팀 상황', 'BALANCE GRAPH' 등).
        좌측에 짧은 세로 강조 바를 두어 시각적으로 섹션 시작점을 표시한다.
        """
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(width=4, height=20, bgcolor=TEXT_DARK),  # 좌측 강조 바
                    ft.Text(text, size=15, weight=ft.FontWeight.W_500, color=TEXT_DARK),
                ],
                spacing=8,
            ),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _build_team_cards(self, teams):
        """
        전체 팀의 카드를 가로 스크롤 Row로 배치한다.
        teams는 DashboardService.get_teams_with_status()가 반환한 DataFrame이며,
        iterrows()로 각 행(팀)을 _team_card()에 전달해 카드로 변환한다.
        """
        cards = [self._team_card(t) for _, t in teams.iterrows()]
        return ft.Container(
            content=ft.Row(cards, spacing=10, scroll=ft.ScrollMode.AUTO),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _team_card(self, t):
        """
        단일 팀 카드 컴포넌트.

        표시 정보:
          - 팀 이름 (+ 내 팀이면 '★ ME' 표시)
          - 현재 잔액
          - 잔액 변동(▲/▼/─)
          - HP 게이지 (파산 임박 또는 파산 시에만 표시)
          - 슬로건

        강조 규칙:
          - is_me(내 팀)        → 황금색 굵은 테두리
          - imminent(파산 임박)  → 빨간색 테두리
          - 그 외                → 일반 테두리
        """
        cc = t["color_code"]
        delta = int(t["balance_delta"])  # 잔액 변동 (현재 - 초기)
        hp = int(t["hp_percent"])  # HP 비율 (0~100)
        imminent = bool(t["is_bankrupt_imminent"])  # HP < 30% 여부
        is_me = int(t["id"]) == self.current_team_id  # 현재 플레이어의 팀인지 여부

        # 잔액 변동 방향에 따라 텍스트와 색상을 분기
        if delta > 0:
            # 잔액 증가 — 초록색 상승 화살표
            delta_text = ft.Text(
                f"▲ +{format_won_man(delta)}",
                size=11,
                color=ACCENT_GREEN_DARK,
                weight=ft.FontWeight.W_500,
            )
        elif delta < 0:
            # 잔액 감소 — 빨간색 하락 화살표 (format_won_man이 이미 '-' 부호를 포함)
            delta_text = ft.Text(
                f"▼ {format_won_man(delta)}",
                size=11,
                color=ACCENT_RED,
                weight=ft.FontWeight.W_500,
            )
        else:
            # 잔액 변동 없음
            delta_text = ft.Text("─ 변동 없음", size=11, color=TEXT_MUTED)

        is_bankrupt = int(t["current_balance"]) <= 0  # 잔액이 0 이하면 파산 상태

        # HP 게이지 영역 — 파산 또는 파산 임박 상태일 때만 추가로 표시
        hp_section = []
        if is_bankrupt:
            # 잔액 0원 이하 → 완전 파산 처리된 팀: HP 게이지를 빈 막대로 표시
            hp_section = [
                ft.Text(
                    "💀 파산", size=11, color=ACCENT_RED, weight=ft.FontWeight.W_500
                ),
                ft.Row(
                    [
                        # 채워진 부분(2px)과 빈 부분으로 구성된 게이지 바 — HP 0%를 시각적으로 표현
                        ft.Container(width=2, height=12, bgcolor=ACCENT_RED),
                        ft.Container(
                            width=max(140 - 2, 2), height=12, bgcolor="#5A3F1F"
                        ),
                    ],
                    spacing=0,
                ),
                ft.Text("HP 0%", size=10, color=TEXT_MUTED),
            ]
        elif imminent:
            # 잔액 > 0 이지만 HP < 30% → 파산 임박 경고 상태
            hp_section = [
                ft.Text(
                    "▼ 파산임박!", size=11, color=ACCENT_RED, weight=ft.FontWeight.W_500
                ),
                ft.Row(
                    [
                        # hp 비율에 비례하여 채워진 부분과 빈 부분의 너비를 계산
                        # 1.4를 곱해 0~100 범위의 hp를 약 140px 폭의 게이지로 변환
                        ft.Container(
                            width=max(hp * 1.4, 2), height=12, bgcolor=ACCENT_RED
                        ),
                        ft.Container(
                            width=max((100 - hp) * 1.4, 2), height=12, bgcolor="#5A3F1F"
                        ),
                    ],
                    spacing=0,
                ),
                ft.Text(f"HP {hp}%", size=10, color=TEXT_MUTED),
            ]
            # is_bankrupt도 imminent도 아닌 일반 상태에서는 hp_section을 표시하지 않음
            # (HP가 30% 이상인 정상 팀은 굳이 게이지를 보여주지 않아 카드를 간결하게 유지)

        # 팀 이름 행 — 내 팀일 경우 '★ ME' 라벨을 추가
        name_row = [
            ft.Text(t["name"], color=TEXT_LIGHT, size=13, weight=ft.FontWeight.W_500)
        ]
        if is_me:
            name_row.append(
                ft.Text("★ ME", color=TEXT_GOLD, size=11, weight=ft.FontWeight.W_500)
            )

        return ft.Container(
            content=ft.Column(
                [
                    # ── 카드 헤더: 팀 이름 (+ ME 표시), 팀 색상 배경 ──
                    ft.Container(
                        content=ft.Row(name_row, spacing=6),
                        bgcolor=TEAM_COLORS[cc],
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                    ),
                    # ── 카드 본문: 아바타 + 잔액 + 변동 + HP + 슬로건 ──
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        # 팀 색상으로 채워진 아바타 박스
                                        ft.Container(
                                            content=ft.Text(
                                                ":)", size=18, color=TEXT_DARK
                                            ),
                                            width=44,
                                            height=44,
                                            bgcolor=TEAM_COLORS[cc],
                                            border=ft.Border.all(2, TEXT_DARK),
                                            alignment=ft.Alignment.CENTER,
                                        ),
                                        # 현재 잔액 (만원 단위로 축약 표시)
                                        ft.Text(
                                            format_won_man(int(t["current_balance"])),
                                            size=16,
                                            weight=ft.FontWeight.W_500,
                                            color=TEXT_DARK,
                                        ),
                                    ],
                                    spacing=10,
                                ),
                                delta_text,  # 잔액 변동 표시
                                *hp_section,  # HP 게이지 (파산/임박 시에만 존재)
                                ft.Text(
                                    f'"{t.get("slogan", "")}"',
                                    size=10,
                                    italic=True,
                                    color=TEXT_MUTED,
                                ),
                            ],
                            spacing=4,
                        ),
                        padding=10,
                    ),
                ],
                spacing=0,
            ),
            bgcolor=TEAM_CARD_BG[cc],
            # 테두리 두께와 색상을 상태에 따라 분기:
            #   내 팀(is_me)이 최우선 → 가장 두꺼운 황금색 테두리
            #   파산 임박(imminent) → 빨간색 테두리
            #   일반 상태            → 기본 테두리
            border=ft.Border.all(
                4 if is_me else (3 if imminent else 2),
                TEXT_GOLD if is_me else (ACCENT_RED if imminent else TEXT_DARK),
            ),
            width=200,
        )

    def _build_balance_graph(self, teams):
        """
        팀별 잔액을 가로 막대그래프로 시각화한다.
        막대의 길이는 전체 팀 중 최댓값(max_balance)에 대한 비율로 계산된다.
        파산 임박 팀의 잔액 텍스트는 빨간색으로 강조된다.
        """
        if len(teams) == 0:
            return ft.Container()  # 팀이 없으면 빈 컨테이너 반환

        # 막대 길이 계산 기준이 되는 최댓값 (0으로 나누는 사고를 방지하기 위해 최소 1)
        max_balance = max(int(teams["current_balance"].max()), 1)
        bars = []
        for _, t in teams.iterrows():
            balance = int(t["current_balance"])
            ratio = balance / max_balance  # 0.0 ~ 1.0 사이의 비율
            color = TEAM_COLORS[t["color_code"]]
            # 파산 임박 팀은 잔액 텍스트도 빨간색으로 강조
            text_color = ACCENT_RED if t["is_bankrupt_imminent"] else TEXT_DARK
            bars.append(
                ft.Row(
                    [
                        # 팀 이름 (고정 너비로 정렬)
                        ft.Container(
                            content=ft.Text(
                                t["name"],
                                size=12,
                                weight=ft.FontWeight.W_500,
                                color=text_color,
                            ),
                            width=60,
                        ),
                        # 막대 그래프 — Row의 expand 속성으로 비율에 따른 너비 배분
                        # ratio*100과 (1-ratio)*100을 정수 expand 값으로 사용해
                        # 채워진 부분과 빈 부분의 상대적 너비를 결정
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Container(
                                        expand=max(int(ratio * 100), 1),
                                        height=18,
                                        bgcolor=color,
                                    ),
                                    ft.Container(
                                        expand=max(int((1 - ratio) * 100), 1),
                                        height=18,
                                        bgcolor="#5A3F1F",
                                    ),
                                ],
                                spacing=0,
                            ),
                            expand=True,
                        ),
                        # 잔액 텍스트 (고정 너비로 정렬, 만원 단위 축약 표시)
                        ft.Container(
                            content=ft.Text(
                                format_won_man(balance),
                                size=12,
                                weight=ft.FontWeight.W_500,
                                color=text_color,
                            ),
                            width=100,
                        ),
                    ],
                    spacing=10,
                )
            )
        return ft.Container(
            content=ft.Container(
                content=ft.Column(bars, spacing=8),
                bgcolor="#F5EDD8",  # 양피지 느낌의 배경
                border=ft.Border.all(2, TEXT_DARK),
                padding=12,
            ),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _build_menu_buttons(self):
        """
        하단 메뉴 버튼 3개(거래소/룰렛돌리기/기록보기)를 가로로 배치한다.
        내부 btn() 헬퍼 함수로 동일한 레이아웃의 버튼을 반복 생성한다.
        """

        def btn(emoji, label, color, handler):
            """단일 메뉴 버튼을 생성하는 내부 헬퍼. 클릭 시 handler() 콜백을 호출한다."""
            return ft.Container(
                content=ft.Row(
                    [
                        ft.Text(emoji, size=20),
                        ft.Text(
                            label, color=TEXT_LIGHT, size=16, weight=ft.FontWeight.W_500
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=8,
                ),
                bgcolor=color,
                border=ft.Border.all(3, TEXT_DARK),
                height=52,
                expand=True,  # 3개 버튼이 가로 폭을 균등 분배
                alignment=ft.Alignment.CENTER,
                on_click=lambda e: handler(),
            )

        return ft.Container(
            content=ft.Row(
                [
                    # 각 버튼은 main.py에서 전달된 화면 전환 콜백을 그대로 연결
                    btn("🛒", "거래소", ACCENT_ORANGE, self.on_goto_marketplace),
                    btn("🎰", "룰렛돌리기", ACCENT_RED, self.on_goto_roulette),
                    btn("📜", "기록보기", "#888888", self.on_goto_history),
                ],
                spacing=12,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
        )
