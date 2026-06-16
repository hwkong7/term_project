"""
views/history.py
자금 흐름 화면 (4.5).

[화면 개요]
파산게임 진행 중 각 팀의 자금 변동 이력(판매 수익, 룰렛 차감)을
시간 역순으로 조회하고 시각화하는 화면이다.

[구성 요소]
- 헤더: BACK 버튼 + 팀 탭 목록 + 현재 잔액
- 필터 버튼: 전체 / 판매만 / 룰렛만
- 이력 목록: 각 이벤트를 카드 형태로 표시

[이벤트 타입]
- TRADE        : 아이템 판매 수익 (양수)
- ROULETTE_COST: 룰렛 돌린 비용 (음수, 스핀 비용 ₩100,000)
- ROULETTE_LOSS: 룰렛에 걸려 차감된 금액 (음수, 패널티 금액)

[필터 동작]
- 전체  → TRADE + ROULETTE_COST + ROULETTE_LOSS 모두 표시
- 판매만 → TRADE만 표시
- 룰렛만 → ROULETTE_COST + ROULETTE_LOSS 표시

[상태 관리]
selected_team_id와 active_filter를 인스턴스 변수로 유지하며,
탭/필터 클릭 시 _build()를 재호출하여 전체 화면을 다시 그린다.
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
from service import HistoryService

# 필터 버튼에 표시될 선택지 목록 (순서 유지)
EVENT_FILTERS = ["전체", "판매만", "룰렛만"]

# 이벤트 타입별 아이콘과 좌측 컬러 바 색상 정의
# ROULETTE_COST와 ROULETTE_LOSS는 모두 빨간색 계열로 차감임을 직관적으로 표현
EVENT_META = {
    "TRADE":         {"icon": "📦", "bar": ACCENT_GREEN_DARK},  # 판매: 초록색 (수익)
    "ROULETTE_COST": {"icon": "🎲", "bar": ACCENT_RED},          # 스핀 비용: 빨간색 (지출)
    "ROULETTE_LOSS": {"icon": "🎲", "bar": ACCENT_RED},          # 패널티 손실: 빨간색 (지출)
}


class HistoryView(ft.Column):
    """
    자금 흐름 화면 최상위 뷰 위젯.

    [탭 전환 방식]
    팀 탭 클릭 시 selected_team_id를 갱신하고 _build()를 재호출한다.
    별도 상태 머신 없이 단순 재빌드로 구현해 코드를 간결하게 유지한다.

    [필터 전환 방식]
    필터 버튼 클릭 시 active_filter를 갱신하고 _build()를 재호출한다.
    HistoryService가 필터 값에 따라 적절한 쿼리를 실행해 데이터를 반환한다.
    """

    def __init__(
        self,
        history_service: HistoryService,    # 자금 흐름 데이터 조회 서비스
        teams: list,                         # 전체 팀 목록 (탭 생성에 사용)
        current_team_id: int,                # 초기 선택 팀 ID
        on_back: Callable,                   # 대시보드 복귀 콜백
    ):
        super().__init__(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

        # 의존성 및 초기 상태 저장
        self.svc = history_service
        self.teams = teams
        self.selected_team_id = current_team_id    # 현재 선택된 팀 (탭 클릭 시 변경)
        self.active_filter = "전체"                # 현재 활성 필터 (필터 클릭 시 변경)
        self.on_back = on_back

        # 초기 화면 구성
        self._build()

    def _build(self):
        """
        화면 전체를 다시 구성한다.
        탭 또는 필터 변경 시 이 메서드를 재호출하여 최신 상태를 반영한다.
        """
        self.controls.clear()
        self.controls.append(self._build_header())   # 상단: 팀 탭 + 잔액
        self.controls.append(self._build_filters())  # 필터 버튼 행
        self.controls.append(self._build_list())     # 이력 카드 목록

    # -----------------------------------------------------------
    # 헤더 섹션 (팀 탭 + 잔액 표시)
    # -----------------------------------------------------------

    def _build_header(self):
        """
        헤더를 구성한다.

        상단 행: BACK 버튼 | '📜 자금 흐름' 제목 | (공백) | 현재 잔액
        하단 행: 팀별 탭 버튼 목록 (가로 스크롤 가능)

        선택된 팀의 탭은 팀 컬러 배경 + 황금 테두리로 강조된다.
        선택되지 않은 탭은 어두운 갈색 배경 + 일반 테두리로 표시된다.
        """
        # 팀 탭 버튼 목록 생성
        team_tabs = []
        for t in self.teams:
            sel = (t["id"] == self.selected_team_id)    # 현재 선택된 팀 여부
            team_tabs.append(
                ft.Container(
                    content=ft.Row(
                        [
                            # 팀 색상 미니 아이콘 (24×24 정사각형)
                            ft.Container(
                                content=ft.Text(":)", size=12, color=TEXT_DARK),
                                width=24,
                                height=24,
                                bgcolor=TEAM_COLORS[t["color_code"]],
                                border=ft.Border.all(2, TEXT_DARK),
                                alignment=ft.Alignment.CENTER,
                            ),
                            # 팀 이름 텍스트
                            ft.Text(
                                f"{t['name']}팀",
                                color=TEXT_LIGHT,
                                size=12,
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                        spacing=6,
                    ),
                    # 선택된 탭: 팀 컬러 배경 / 미선택 탭: 어두운 갈색 배경
                    bgcolor=TEAM_COLORS[t["color_code"]] if sel else "#5A4632",
                    # 선택된 탭: 황금 테두리 두껍게 / 미선택 탭: 얇은 일반 테두리
                    border=ft.Border.all(
                        2 if sel else 1,
                        TEXT_GOLD if sel else TEXT_DARK,
                    ),
                    padding=ft.Padding(left=10, right=10, top=6, bottom=6),
                    data=t["id"],               # 클릭 시 team_id를 이벤트 데이터로 전달
                    on_click=self._on_team_click,
                )
            )

        # 현재 선택된 팀의 잔액 조회 (헤더 우측에 표시)
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
                    # 첫 번째 행: BACK + 제목 + 잔액
                    ft.Row(
                        [
                            # BACK 버튼
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
                            # 화면 제목
                            ft.Text(
                                "📜 자금 흐름",
                                color=TEXT_LIGHT,
                                size=20,
                                weight=ft.FontWeight.W_500,
                            ),
                            ft.Container(expand=True),  # 우측 정보를 오른쪽으로 밀어냄
                            # 현재 잔액 라벨
                            ft.Text("현재 잔액", color=TEXT_MUTED, size=12),
                            # 현재 잔액 수치 (황금색 강조)
                            ft.Text(
                                balance_text,
                                color=TEXT_GOLD,
                                size=16,
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                        spacing=12,
                    ),
                    # 두 번째 행: 팀 탭 목록 (가로 스크롤)
                    ft.Row(team_tabs, spacing=8, scroll=ft.ScrollMode.AUTO),
                ],
                spacing=10,
            ),
            bgcolor=BG_PANEL,
            padding=ft.Padding(left=16, right=16, top=12, bottom=12),
        )

    # -----------------------------------------------------------
    # 필터 섹션
    # -----------------------------------------------------------

    def _build_filters(self):
        """
        이벤트 타입 필터 버튼 행을 구성한다.

        선택된 필터: 갈색 배경 (#5A3F1F) — 활성 상태임을 명시
        미선택 필터: 회색 배경 (#9A9A9A) — 비활성 상태
        우측에 '▼ 최신순' 정렬 안내 텍스트를 배치한다.
        """
        filters = []
        for f in EVENT_FILTERS:
            sel = (f == self.active_filter)     # 현재 활성 필터 여부
            filters.append(
                ft.Container(
                    content=ft.Text(
                        f, color=TEXT_LIGHT, size=13, weight=ft.FontWeight.W_500
                    ),
                    bgcolor="#5A3F1F" if sel else "#9A9A9A",  # 활성/비활성 배경 구분
                    border=ft.Border.all(2, TEXT_DARK),
                    width=100,
                    height=40,
                    alignment=ft.Alignment.CENTER,
                    data=f,                     # 클릭 시 필터 문자열을 이벤트 데이터로 전달
                    on_click=self._on_filter_click,
                )
            )

        return ft.Container(
            content=ft.Row(
                [
                    *filters,                               # 필터 버튼들 펼쳐서 삽입
                    ft.Container(expand=True),              # 정렬 텍스트를 우측으로 밀어냄
                    ft.Text("▼ 최신순", size=12, color=TEXT_MUTED),  # 정렬 방식 안내
                ],
                spacing=10,
            ),
            padding=ft.Padding(left=16, right=16, top=0, bottom=0),
        )

    # -----------------------------------------------------------
    # 이력 목록 섹션
    # -----------------------------------------------------------

    def _build_list(self):
        """
        현재 선택된 팀과 필터에 따른 자금 흐름 이력 목록을 구성한다.

        HistoryService.get_team_history()를 호출하여 DataFrame을 받고,
        각 행을 _history_card()로 변환하여 수직 목록으로 표시한다.
        기록이 없으면 안내 문구를 표시한다.
        """
        # 서비스 레이어에서 데이터 조회 (필터 적용됨)
        df = self.svc.get_team_history(self.selected_team_id, self.active_filter)
        rows = []

        if len(df) == 0:
            # 이력이 없는 경우 안내 문구
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
            # 각 이력 행을 카드로 변환
            for _, row in df.iterrows():
                rows.append(self._history_card(row))

        # 양피지 색 배경 패널에 카드 목록을 감쌈
        return ft.Container(
            content=ft.Container(
                content=ft.Column(rows, spacing=10),
                bgcolor="#F5EDD8",               # 양피지 느낌의 배경
                border=ft.Border.all(3, "#5A4632"),
                padding=16,
            ),
            padding=ft.Padding(left=16, right=16, top=0, bottom=0),
        )

    def _history_card(self, row) -> ft.Container:
        """
        자금 흐름 이력 한 건을 카드 형태로 구성한다.

        카드 레이아웃:
            [컬러 바] [이모지 아이콘] [이벤트 제목 + 시간] (공백) [금액]

        컬러 바: 이벤트 타입에 따라 초록(판매) 또는 빨강(룰렛)
        금액: 양수면 초록, 음수면 빨강으로 표시하여 직관적으로 구분

        Args:
            row: HistoryService.get_team_history()가 반환한 DataFrame의 한 행
                 필드: event_type, detail, quantity, amount, event_at
        """
        et = row["event_type"]                          # 이벤트 타입 문자열
        meta = EVENT_META.get(et, {"icon": "📦", "bar": "#999"})  # 타입별 메타 정보
        amount = int(row["amount"])                     # 금액 (TRADE: 양수, ROULETTE: 음수)

        # 이벤트 타입에 따라 카드 제목 생성
        if et == "TRADE":
            # 판매 이벤트: 아이템명과 수량 표시
            title = f"상품 판매 — {row['detail']} × {int(row['quantity'])}"
        elif et == "ROULETTE_COST":
            # 스핀 비용 이벤트: 내가 룰렛을 돌린 경우
            title = "룰렛 비용 — 직접 룰렛 돌림"
        else:
            # 패널티 손실 이벤트: 다른 팀이 돌린 룰렛에 걸린 경우 (detail = 스피너 팀명)
            title = f"룰렛 손실 — {row['detail']}"

        # 발생 시각 포맷팅 (Timestamp → 문자열)
        try:
            time_str = row["event_at"].strftime("%Y-%m-%d %H:%M")
        except Exception:
            # strftime 실패 시 문자열 변환으로 폴백
            time_str = str(row["event_at"])

        # 금액에 따라 색상 결정 (수익: 초록, 손실: 빨강)
        amount_color = ACCENT_GREEN_DARK if amount >= 0 else ACCENT_RED

        return ft.Container(
            content=ft.Row(
                [
                    # 좌측 컬러 바: 이벤트 타입을 색상으로 즉시 구분
                    ft.Container(width=6, height=60, bgcolor=meta["bar"]),

                    # 이벤트 아이콘 (이모지): 판매=📦, 룰렛=🎲
                    ft.Container(
                        content=ft.Text(meta["icon"], size=28),
                        width=56,
                        height=56,
                        bgcolor="#6B4F2E",           # 나무 질감 어두운 갈색 배경
                        border=ft.Border.all(2, "#3E2A14"),
                        alignment=ft.Alignment.CENTER,
                    ),

                    # 이벤트 제목과 발생 시각 (세로 배치)
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
                        expand=True,                # 남은 공간을 채워 금액을 오른쪽으로 밀어냄
                    ),

                    # 금액 표시 (양수: '+₩xxx,xxx', 음수: '-₩xxx,xxx')
                    ft.Text(
                        f"{'+' if amount >= 0 else ''}{format_won(amount)}",
                        size=18,
                        weight=ft.FontWeight.W_500,
                        color=amount_color,
                    ),
                ],
                spacing=12,
            ),
            bgcolor="#FBF4E0",                      # 카드 배경: 밝은 크림색
            border=ft.Border.all(2, "#C4B590"),     # 테두리: 연한 황토색
            padding=ft.Padding(left=12, right=12, top=10, bottom=10),
        )

    # -----------------------------------------------------------
    # 이벤트 핸들러
    # -----------------------------------------------------------

    def _on_team_click(self, e):
        """
        팀 탭 클릭 이벤트 핸들러.
        선택된 팀 ID를 갱신하고 화면 전체를 재빌드한다.
        """
        self.selected_team_id = e.control.data  # 클릭한 탭의 team_id
        self._build()
        self.update()

    def _on_filter_click(self, e):
        """
        필터 버튼 클릭 이벤트 핸들러.
        활성 필터를 갱신하고 화면 전체를 재빌드한다.
        필터가 변경되면 _build_list()에서 HistoryService를 재호출해 새 데이터를 가져온다.
        """
        self.active_filter = e.control.data     # 클릭한 필터 문자열 ('전체'/'판매만'/'룰렛만')
        self._build()
        self.update()
