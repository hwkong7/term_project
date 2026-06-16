"""
views/__init__.py
모든 public 심볼 re-export.

views 패키지 외부(main.py 등)에서 from views import ... 로 직접 접근할 수 있도록
하위 모듈의 클래스·함수를 한 곳에 모아 re-export한다.

이 파일 덕분에 main.py는 각 하위 파일 경로를 몰라도 되고,
패키지 내부 구조가 바뀌어도 외부 import 문을 수정하지 않아도 된다 (안정적인 공개 인터페이스).
"""

# 헬퍼 함수
from views._helpers import _snack

# 다이얼로그 (파산/우승 알림)
from views.dialogs import show_bankrupt_dialog, show_winner_dialog

# 팀 등록 화면 컴포넌트
from views.team_registration import TeamCard, TeamRegistrationView

# 팀 선택 화면
from views.team_selection import TeamSelectionView

# 대시보드 화면
from views.dashboard import DashboardView

# 거래소 화면 컴포넌트
from views.marketplace import ItemCard, MarketplaceView

# 룰렛 화면
from views.roulette import RouletteView

# 자금 흐름 화면
from views.history import HistoryView

# 패키지 외부에서 접근 가능한 심볼 목록 (명시적 공개 인터페이스)
__all__ = [
    "_snack",
    "show_bankrupt_dialog",
    "show_winner_dialog",
    "TeamCard",
    "TeamRegistrationView",
    "TeamSelectionView",
    "DashboardView",
    "ItemCard",
    "MarketplaceView",
    "RouletteView",
    "HistoryView",
]
