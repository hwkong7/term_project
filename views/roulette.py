"""
views/roulette.py
룰렛 화면 (4.4) — async 슬롯머신 애니메이션.

[설계 배경]
초기 구현에서는 threading + time.sleep 방식으로 슬롯 애니메이션을 구현했으나,
Flet의 UI 스레드와 충돌하여 화면이 멈추거나(freeze) 업데이트가 반영되지 않는
문제가 발생했다. 이를 해결하기 위해 asyncio + page.run_task() 방식으로 전면 교체했다.

[동작 원리]
1. 사용자가 SPIN 버튼 클릭 → _on_spin_click (async 이벤트 핸들러) 호출
2. RouletteService.execute_spin()으로 즉시 결과 확정 (DB 기록 포함)
3. _animate()로 슬롯머신 시각 효과 재생 (결과는 이미 확정된 상태)
4. 애니메이션 종료 후 파산 체크 → 우승 판정 순으로 콜백 호출

[애니메이션 전략]
- _ReelDisplay: 텍스트를 교체하며 사이클링하는 슬롯 릴(reel) 위젯
- 총 30프레임, easeOut 커브(t²)로 감속 → 자연스럽고 짜릿한 연출
- 마지막 5프레임은 확정 결과값으로 서서히 수렴
- 확정 후 3회 깜빡임 효과로 결과를 강조
"""

import asyncio                      # async 애니메이션 루프에 사용 (time.sleep 대체)
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
from service import RouletteService, RouletteError, SPIN_COST
from views._helpers import _snack

# 룰렛 차감 금액 목록 — services.PENALTY_AMOUNTS와 동일한 값
# 슬롯 애니메이션 중 표시할 금액 라벨을 생성하는 데 사용
_AMOUNTS = [500_000, 800_000, 1_000_000, 1_500_000, 2_000_000, 2_500_000, 3_000_000]


# ===========================================================
# _ReelDisplay — 슬롯머신 릴(Reel) 위젯
# ===========================================================

class _ReelDisplay(ft.Container):
    """
    슬롯머신 한 칸(릴)을 표현하는 위젯.

    내부 Text 위젯의 value를 교체하는 방식으로 사이클링 효과를 구현한다.
    animate_position 같은 Flet 내장 애니메이션 대신 텍스트 교체를 선택한 이유:
    - 내장 위치 애니메이션은 0.85.x에서 스레드 안전성 문제가 있었음
    - asyncio + set_value() 조합이 이벤트 루프와 안전하게 공존함
    - 팀 이름·금액 문자열만 교체하면 되므로 충분한 시각 효과 달성

    주요 메서드:
        set_value(text, color): 표시 텍스트와 색상을 즉시 변경
        flash(color):           배경색을 일시적으로 변경 (깜빡임 시작)
        unflash():              배경색을 기본값으로 복원 (깜빡임 종료)
    """

    def __init__(self, width: int):
        # 릴 중앙에 표시되는 큰 텍스트 라벨 — 팀 이름 또는 금액이 들어감
        self._label = ft.Text(
            "???",                              # 초기값: 아직 결과 미확정 상태 표시
            size=38,
            weight=ft.FontWeight.BOLD,
            color=TEXT_DARK,
            text_align=ft.TextAlign.CENTER,
        )

        # 외부 Container: 정해진 크기와 테두리로 슬롯머신 칸 외형 구성
        super().__init__(
            content=ft.Container(
                content=self._label,
                alignment=ft.Alignment.CENTER,  # 텍스트를 정중앙에 배치
            ),
            width=width,
            height=100,                         # 슬롯 칸의 고정 높이
            bgcolor="#D4C4A0",                  # 기본 배경: 양피지 느낌의 연한 갈색
            border=ft.Border.all(3, TEXT_GOLD), # 황금색 테두리로 슬롯머신 느낌 강조
            alignment=ft.Alignment.CENTER,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,  # 텍스트가 칸 밖으로 넘치지 않도록
        )

    def set_value(self, text: str, color: str = TEXT_DARK):
        """
        릴에 표시되는 텍스트와 색상을 변경한다.
        _animate() 루프에서 매 프레임마다 호출되어 슬롯 회전 효과를 만든다.

        Args:
            text:  표시할 문자열 (팀 이름 또는 금액 문자열)
            color: 텍스트 색상 (기본값: TEXT_DARK, 확정 시: TEXT_GOLD 또는 ACCENT_RED)
        """
        self._label.value = text
        self._label.color = color
        self._label.update()    # Flet에 즉시 렌더링 요청

    def flash(self, color: str):
        """
        배경색을 지정한 색으로 변경한다 (깜빡임 효과 ON).
        결과 확정 후 강조 연출 시 사용한다.
        """
        self.bgcolor = color
        self.update()

    def unflash(self):
        """배경색을 기본값(양피지색)으로 복원한다 (깜빡임 효과 OFF)."""
        self.bgcolor = "#D4C4A0"
        self.update()


# ===========================================================
# RouletteView — 룰렛 메인 화면
# ===========================================================

class RouletteView(ft.Column):
    """
    룰렛 화면 전체를 구성하는 최상위 뷰 위젯.

    구성 섹션:
        [0] 헤더 (_build_header):  BACK 버튼 + 현재 팀 정보 + 잔액
        [1] 패널 (_build_panel):   슬롯머신 2개(팀·금액) + SPIN 버튼
        [2] 최근 결과 (_build_recent): 최근 룰렛 결과 3건

    상태:
        is_spinning: 애니메이션 진행 중 여부 — True이면 중복 클릭 무시
        _team_names: 생존 팀 이름 목록 — 애니메이션 중 릴에 순환 표시
        _amount_labels: 차감 금액 문자열 목록 — 애니메이션 중 릴에 순환 표시
    """

    def __init__(
        self,
        roulette_service: RouletteService,
        current_team_id,                    # 현재 룰렛을 돌리는 팀의 ID
        get_team_info,                      # team_id → 팀 dict 반환 콜백
        get_all_teams,                      # 전체 팀 목록(list[dict]) 반환 콜백
        on_back,                            # 대시보드로 돌아가는 콜백
        on_bankrupt: Callable = None,       # 팀 파산 시 호출할 콜백 (team_name 전달)
        on_winner: Callable = None,         # 우승 팀 결정 시 호출할 콜백 (name, balance 전달)
    ):
        super().__init__(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

        # 의존성 저장
        self.svc = roulette_service
        self.current_team_id = current_team_id
        self.get_team_info = get_team_info
        self.get_all_teams = get_all_teams
        self.on_back = on_back
        self.on_bankrupt = on_bankrupt
        self.on_winner = on_winner

        # 애니메이션 잠금 플래그 — 스핀 중 중복 클릭 방지
        self.is_spinning = False

        # 슬롯 릴에 순환 표시할 데이터 목록 (생존 팀만 포함)
        self._all_teams = get_all_teams()
        self._team_names = [t["name"] for t in self._all_teams]
        self._amount_labels = [format_won_man(a) for a in _AMOUNTS]

        # 슬롯머신 릴 위젯 (패널에 배치됨)
        self.team_reel = _ReelDisplay(300)      # 좌측 릴: 타겟 팀 표시
        self.amount_reel = _ReelDisplay(300)    # 우측 릴: 차감 금액 표시

        # 릴 아래 상태 텍스트 ("READY" → 결과 확정 후 팀명/금액으로 교체)
        self.team_status = ft.Text("READY", size=15, color=TEXT_MUTED)
        self.amount_status = ft.Text("READY", size=15, color=TEXT_MUTED)

        # 화면 구성
        self._build()

    def _build(self):
        """controls 목록을 초기화하고 3개 섹션을 순서대로 추가한다."""
        self.controls.clear()
        self.controls.append(self._build_header())   # controls[0]
        self.controls.append(self._build_panel())    # controls[1]
        self.controls.append(self._build_recent())   # controls[2]

    # -----------------------------------------------------------
    # 헤더 섹션
    # -----------------------------------------------------------

    def _build_header(self):
        """
        상단 헤더를 구성한다.
        - 좌측: BACK 버튼 (대시보드로 복귀)
        - 중앙: '🎰 룰렛 시스템' 제목
        - 우측: 현재 팀 색상 아이콘 + 팀명 + 현재 잔액
        잔액은 스핀 후 헤더를 재빌드할 때마다 최신 값으로 갱신된다.
        """
        # DB에서 현재 팀의 최신 정보를 조회 (스핀 후 잔액 반영)
        team = self.get_team_info(self.current_team_id)

        return ft.Container(
            content=ft.Row(
                [
                    # BACK 버튼: 클릭 시 on_back() 콜백 호출
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
                    # 화면 제목
                    ft.Text(
                        "🎰 룰렛 시스템",
                        color=TEXT_LIGHT,
                        size=20,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.Container(expand=True),  # 가운데 공백 — 우측 정보를 오른쪽으로 밀어냄
                    # 현재 팀 정보 뱃지
                    ft.Container(
                        content=ft.Row(
                            [
                                # 팀 색상 미니 아이콘
                                ft.Container(
                                    content=ft.Text(":)", size=14, color=TEXT_DARK),
                                    width=28,
                                    height=28,
                                    bgcolor=TEAM_COLORS[team["color_code"]],
                                    border=ft.Border.all(2, TEXT_DARK),
                                    alignment=ft.Alignment.CENTER,
                                ),
                                # 팀 이름
                                ft.Text(
                                    f"{team['name']}팀",
                                    color=TEXT_LIGHT,
                                    size=14,
                                    weight=ft.FontWeight.W_500,
                                ),
                                ft.Text("잔액", color=TEXT_MUTED, size=12),
                                # 현재 잔액 (스핀 비용 차감 후 최신값)
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
                        padding=ft.Padding(left=12, right=12, top=8, bottom=8),
                    ),
                ],
                spacing=12,
            ),
            bgcolor=BG_PANEL,
            padding=ft.Padding(left=16, right=16, top=12, bottom=12),
        )

    # -----------------------------------------------------------
    # 슬롯머신 패널 섹션
    # -----------------------------------------------------------

    def _build_panel(self):
        """
        슬롯머신 패널을 구성한다.
        - '★ 파산 룰렛 ★' 제목
        - 팀 릴과 금액 릴을 나란히 배치 (_slot 헬퍼 사용)
        - SPIN 버튼 (spin_button): 클릭 시 _on_spin_click 호출
        패널 전체는 어두운 배경(#2A2A2A)과 황금 테두리로 카지노 분위기를 연출한다.
        """
        # SPIN 버튼 — 인스턴스 변수로 저장해 애니메이션 중 비활성화/재활성화에 사용
        self.spin_button = ft.Container(
            content=ft.Text(
                f"🎲 SPIN!  ({format_won_man(SPIN_COST)})",  # 비용을 버튼에 표시
                color=TEXT_LIGHT,
                size=20,
                weight=ft.FontWeight.W_500,
            ),
            bgcolor=ACCENT_RED,                         # 빨간 배경으로 클릭 욕구 자극
            border=ft.Border.all(3, TEXT_GOLD),
            height=60,
            alignment=ft.Alignment.CENTER,
            on_click=self._on_spin_click,               # async 이벤트 핸들러
        )

        return ft.Container(
            content=ft.Column(
                [
                    # 패널 제목
                    ft.Text(
                        "★ 파산 룰렛 ★",
                        color=TEXT_GOLD,
                        size=20,
                        weight=ft.FontWeight.W_500,
                    ),
                    # 슬롯 릴 2개를 가로로 배치
                    ft.Row(
                        [
                            # 좌측: 걸릴 팀 릴
                            self._slot("걸릴 팀", self.team_reel, self.team_status),
                            # 우측: 차감 금액 릴
                            self._slot("차감 금액", self.amount_reel, self.amount_status),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=20,
                    ),
                    # SPIN 버튼
                    self.spin_button,
                ],
                spacing=20,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="#2A2A2A",                  # 카지노 느낌의 어두운 배경
            border=ft.Border.all(3, TEXT_GOLD),
            padding=20,
            margin=ft.Margin(left=16, right=16, top=0, bottom=0),
        )

    def _slot(self, title: str, reel: _ReelDisplay, status: ft.Text):
        """
        단일 슬롯(제목 + 릴 + 상태 텍스트)을 수직으로 배치하는 헬퍼 메서드.

        Args:
            title:  슬롯 상단에 표시할 라벨 ('걸릴 팀' 또는 '차감 금액')
            reel:   _ReelDisplay 인스턴스
            status: 릴 하단의 상태 텍스트 위젯
        """
        return ft.Column(
            [
                # 슬롯 제목 라벨
                ft.Container(
                    content=ft.Text(
                        title, color=TEXT_GOLD, size=14, weight=ft.FontWeight.W_500
                    ),
                    bgcolor="#2A1C0E",           # 제목 배경: 매우 어두운 갈색
                    padding=ft.Padding(left=0, right=0, top=8, bottom=8),
                    alignment=ft.Alignment.CENTER,
                    width=300,
                ),
                reel,                           # 슬롯 릴 위젯
                # 상태 텍스트 영역 (READY → 결과 확정 후 내용으로 교체)
                ft.Container(
                    content=status,
                    padding=ft.Padding(left=0, right=0, top=6, bottom=6),
                    alignment=ft.Alignment.CENTER,
                ),
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    # -----------------------------------------------------------
    # 최근 결과 섹션
    # -----------------------------------------------------------

    def _build_recent(self):
        """
        최근 룰렛 결과 최대 3건을 목록으로 표시한다.
        스핀 완료 후 controls[2]를 이 메서드의 반환값으로 교체해 목록을 갱신한다.
        기록이 없으면 '아직 룰렛 기록이 없습니다.' 안내 문구를 표시한다.
        """
        # DB에서 최근 3건 조회 (spinner/target 팀 이름·색상 포함)
        recent = self.svc.find_recent_results(3)
        rows = []

        if len(recent) == 0:
            # 아직 한 번도 스핀하지 않은 경우
            rows.append(
                ft.Text("아직 룰렛 기록이 없습니다.", size=13, color=TEXT_MUTED)
            )
        else:
            # 결과 목록 행 생성 (가장 최신 결과가 '방금'으로 표시됨)
            labels = ["방금", "1분전", "3분전"]
            for i, (_, r) in enumerate(recent.iterrows()):
                rows.append(self._result_row(labels[i] if i < 3 else f"{i}회전", r))

        # 배경 패널(양피지색)에 결과 목록을 감쌈
        return ft.Container(
            content=ft.Container(
                content=ft.Column(
                    [
                        # 섹션 제목 (수직 강조 바 + 텍스트)
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
                        *rows,  # 결과 행들을 펼쳐서 삽입
                    ],
                    spacing=8,
                ),
                bgcolor="#F5EDD8",              # 양피지 느낌의 배경
                border=ft.Border.all(2, TEXT_DARK),
                padding=12,
            ),
            padding=ft.Padding(left=16, right=16, top=0, bottom=0),
        )

    def _result_row(self, label: str, r) -> ft.Container:
        """
        룰렛 결과 한 행을 구성한다.

        표시 형식:
            [시간 라벨] [스피너 색상] 스피너이름 → [타겟 색상] 타겟이름   -₩penalty

        Args:
            label: '방금' / '1분전' 등 상대 시간 문자열
            r:     find_recent_results()가 반환한 DataFrame의 한 행
        """
        return ft.Container(
            content=ft.Row(
                [
                    # 시간 라벨 (고정 너비로 정렬)
                    ft.Container(
                        content=ft.Text(label, size=11, color=TEXT_MUTED), width=50
                    ),
                    # 스피너(룰렛 돌린 팀) 색상 정사각형
                    ft.Container(
                        width=16,
                        height=16,
                        bgcolor=TEAM_COLORS.get(r["spinner_color"], "#999"),
                    ),
                    # 스피너 팀 이름
                    ft.Text(
                        r["spinner_name"],
                        size=13,
                        weight=ft.FontWeight.W_500,
                        color=TEXT_DARK,
                    ),
                    ft.Text("→", size=14, color=TEXT_MUTED),   # 화살표
                    # 타겟(피해를 입은 팀) 색상 정사각형
                    ft.Container(
                        width=16,
                        height=16,
                        bgcolor=TEAM_COLORS.get(r["target_color"], "#999"),
                    ),
                    # 타겟 팀 이름
                    ft.Text(
                        r["target_name"],
                        size=13,
                        weight=ft.FontWeight.W_500,
                        color=TEXT_DARK,
                    ),
                    ft.Container(expand=True),  # 우측으로 금액 밀어냄
                    # 차감 금액 (음수로 표시하여 손실 강조)
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
            padding=ft.Padding(left=12, right=12, top=8, bottom=8),
        )

    # -----------------------------------------------------------
    # 이벤트 핸들러 — SPIN 버튼 클릭
    # -----------------------------------------------------------

    async def _on_spin_click(self, e):
        """
        SPIN 버튼 클릭 이벤트 핸들러 (async).

        처리 순서:
            1. 이미 스핀 중이면 즉시 반환 (중복 클릭 방지)
            2. 생존 팀 목록 갱신 (파산팀은 릴 애니메이션에서 제외)
            3. RouletteService.execute_spin()으로 결과 즉시 확정 (DB 기록)
            4. 버튼 비활성화 + 상태 초기화
            5. _animate()로 슬롯머신 시각 효과 재생
        """
        # 중복 스핀 방지
        if self.is_spinning:
            return

        # 스핀 전 생존팀 목록 갱신 — 파산팀(잔액 <= 0)은 애니메이션에서 제외
        # 이렇게 하면 이미 파산한 팀이 릴 애니메이션에 나타나지 않음
        all_teams = self.get_all_teams()
        self._team_names = [t["name"] for t in all_teams if t["current_balance"] > 0]
        if not self._team_names:
            # 만약 모두 파산했다면 전체 팀 이름 사용 (방어 처리)
            self._team_names = [t["name"] for t in all_teams]

        # 서비스 레이어에서 스핀 결과 확정
        # - 스핀 비용(₩100,000) 차감
        # - 타겟 팀 무작위 선정 (파산팀 제외)
        # - 패널티 금액 무작위 선정
        # - DB에 roulette_spin 레코드 저장
        try:
            result = self.svc.execute_spin(self.current_team_id)
        except RouletteError as ex:
            # 잔액 부족, 팀 수 부족 등 비즈니스 규칙 위반
            _snack(self.page, f"⚠ {ex}", ACCENT_RED)
            return
        except Exception as ex:
            # 예상치 못한 오류
            _snack(self.page, f"⚠ 오류: {ex}", ACCENT_RED)
            return

        # 스핀 시작 — 잠금 + UI 비활성화
        self.is_spinning = True
        self.spin_button.bgcolor = "#444444"        # 버튼을 회색으로 변경하여 비활성 표시
        self.spin_button.content = ft.Text(
            "⏳ SPINNING...", color="#AAAAAA", size=18, weight=ft.FontWeight.W_500
        )
        # 이전 결과 상태 텍스트 초기화
        self.team_status.value = ""
        self.amount_status.value = ""
        self.spin_button.update()
        self.team_status.update()
        self.amount_status.update()

        # 애니메이션 실행 (결과는 이미 result에 담겨 있음)
        await self._animate(result)

    # -----------------------------------------------------------
    # 슬롯머신 애니메이션
    # -----------------------------------------------------------

    async def _animate(self, result: dict):
        """
        async 슬롯머신 애니메이션을 실행한다.

        [애니메이션 단계]
        Phase 1 — 사이클링 (0 ~ TOTAL-SETTLE-1 프레임):
            팀 이름과 금액 라벨을 빠르게 순환 표시.
            easeOut 커브(t²)로 프레임 간격을 점진적으로 늘려 감속 효과 연출.

        Phase 2 — 수렴 (TOTAL-SETTLE ~ TOTAL-1 프레임):
            확정 결과값(target_name, penalty_amount)을 표시하며 서서히 정지.

        Phase 3 — 확정 깜빡임 (3회):
            결과를 황금/빨강 색으로 3번 깜빡여 당첨 결과를 시각적으로 강조.

        Phase 4 — 사후 처리:
            상태 텍스트 업데이트 → 버튼 재활성화 → 최근 결과 갱신
            → 파산 체크 → 우승 판정

        Args:
            result: RouletteService.execute_spin()이 반환한 결과 dict
                {
                  "target_name":      str,   # 피해 팀 이름
                  "target_color":     str,   # 피해 팀 색상 코드
                  "target_team_id":   int,
                  "penalty_amount":   int,   # 차감 금액
                  "spin_cost":        int,   # 스핀 비용
                  ...
                }
        """
        TOTAL = 30      # 전체 애니메이션 프레임 수
        SETTLE = 5      # 마지막 N프레임은 결과값을 고정하여 수렴 효과

        # --- Phase 1 & 2: 순환 → 수렴 ---
        for i in range(TOTAL):
            # easeOut 커브: t = 0(시작) → 1(끝), delay는 0.04s → 0.26s로 증가
            t = i / (TOTAL - 1)
            delay = 0.04 + (t ** 2) * 0.22     # 제곱 함수로 자연스러운 감속

            if i < TOTAL - SETTLE:
                # Phase 1: 빠르게 순환 — 모듈러 연산으로 목록을 반복 순환
                team_val = self._team_names[i % len(self._team_names)]
                amt_val = self._amount_labels[i % len(self._amount_labels)]
                self.team_reel.set_value(team_val, TEXT_DARK)
                self.amount_reel.set_value(amt_val, TEXT_DARK)
            else:
                # Phase 2: 수렴 — 확정 결과값으로 고정
                self.team_reel.set_value(result["target_name"], TEXT_DARK)
                self.amount_reel.set_value(
                    format_won_man(result["penalty_amount"]), TEXT_DARK
                )

            await asyncio.sleep(delay)  # Flet 이벤트 루프를 블로킹하지 않고 대기

        # --- Phase 3: 깜빡임 (3회) — 결과 확정 연출 ---
        for _ in range(3):
            # 황금/빨강으로 강조
            self.team_reel.set_value(result["target_name"], TEXT_GOLD)
            self.amount_reel.set_value(
                format_won_man(result["penalty_amount"]), ACCENT_RED
            )
            await asyncio.sleep(0.18)   # 강조 유지 시간

            # 어두운 색으로 복귀
            self.team_reel.set_value(result["target_name"], TEXT_DARK)
            self.amount_reel.set_value(
                format_won_man(result["penalty_amount"]), TEXT_DARK
            )
            await asyncio.sleep(0.12)   # 어두운 상태 유지 시간

        # 최종 색상 확정 (황금 + 빨강으로 고정)
        self.team_reel.set_value(result["target_name"], TEXT_GOLD)
        self.amount_reel.set_value(format_won_man(result["penalty_amount"]), ACCENT_RED)

        # --- Phase 4: 상태 텍스트 업데이트 ---
        self.team_status.value = f"🎯 {result['target_name']}팀"
        self.team_status.color = TEXT_GOLD
        self.amount_status.value = f"💸 {format_won(result['penalty_amount'])} 차감!"
        self.amount_status.color = ACCENT_RED
        self.team_status.update()
        self.amount_status.update()

        # SPIN 버튼 재활성화 (다음 스핀 가능 상태로 복귀)
        self.is_spinning = False
        self.spin_button.content = ft.Text(
            f"🎲 SPIN!  ({format_won_man(SPIN_COST)})",
            color=TEXT_LIGHT,
            size=20,
            weight=ft.FontWeight.W_500,
        )
        self.spin_button.bgcolor = ACCENT_RED   # 빨간 배경으로 복귀
        self.spin_button.update()

        # 최근 결과 목록 + 헤더 잔액 갱신
        # controls[2] = 최근 결과 섹션, controls[0] = 헤더
        self.controls[2] = self._build_recent()
        self.controls[0] = self._build_header()
        self.update()   # 전체 Column 업데이트

        # 스낵바로 결과 요약 알림
        _snack(
            self.page,
            f"🎰 {result['target_name']}팀 {format_won(result['penalty_amount'])} 차감!",
            ACCENT_RED,
        )

        # --- 파산 체크 ---
        # 타겟 팀의 최신 잔액을 DB에서 재조회하여 파산 여부 확인
        target_team = self.get_team_info(result["target_team_id"])
        if target_team and target_team["current_balance"] <= 0 and self.on_bankrupt:
            await asyncio.sleep(0.8)        # 스낵바 확인 여유 시간
            self.on_bankrupt(target_team["name"])   # 파산 다이얼로그 표시 (동기 콜백)
            # on_bankrupt는 동기 함수이므로 다이얼로그를 열고 즉시 반환됨
            # 사용자가 '확인' 버튼을 누를 시간을 주기 위해 잠시 대기
            await asyncio.sleep(0.5)

        # --- 우승 판정 ---
        # 생존 팀(잔액 > 0)이 정확히 1팀만 남으면 우승 처리
        # 파산 다이얼로그 이후에 실행되어 올바른 표시 순서를 보장
        all_teams = self.get_all_teams()
        surviving = [t for t in all_teams if t["current_balance"] > 0]
        if len(surviving) == 1 and self.on_winner:
            winner = surviving[0]
            await asyncio.sleep(0.5)    # 파산 다이얼로그 닫힌 후 여유 시간
            # 우승 다이얼로그 표시 (팀명, 최종 잔액 전달)
            self.on_winner(winner["name"], int(winner["current_balance"]))
