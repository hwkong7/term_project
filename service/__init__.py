"""
service/__init__.py
service 패키지 외부 노출.

finance_service.py에 정의된 모든 서비스 클래스와 관련 예외·상수를
패키지 레벨에서 직접 import할 수 있도록 re-export한다.

사용 예:
    from service import TeamService, TradeService, TradeError
    from service import FinanceService, SPIN_COST
"""

from .finance_service import (
    FinanceService,           # DB 초기화 및 게임 데이터 리셋 담당
    TeamService,              # 팀 등록 및 색상 조회
    ItemService,              # 아이템 조회 및 커스텀 추가
    TradeService,             # 아이템 판매 거래 처리
    TradeError,               # 거래 비즈니스 규칙 위반 예외
    RouletteService,          # 룰렛 스핀 실행
    RouletteError,            # 룰렛 비즈니스 규칙 위반 예외
    HistoryService,           # 자금 흐름 이력 조회
    DashboardService,         # 대시보드 집계 데이터 제공
    TeamRegistrationError,    # 팀 등록 유효성 검사 실패 예외
    SPIN_COST,                # 룰렛 1회 스핀 비용 상수
)

__all__ = [
    "FinanceService",
    "TeamService",
    "ItemService",
    "TradeService",
    "TradeError",
    "RouletteService",
    "RouletteError",
    "HistoryService",
    "DashboardService",
    "TeamRegistrationError",
    "SPIN_COST",
]
