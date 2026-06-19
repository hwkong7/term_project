"""
repository/__init__.py
.env 파일의 DB_TYPE 설정에 따른 Repository 클래스 동적 할당.

[동작 원리]
프로그램 실행 시 .env 파일을 읽어 DB_TYPE 환경 변수를 확인한다.
DB_TYPE에 해당하는 DBMS 구현체를 import하여 공통 이름(DatabaseManager, TeamRepository 등)으로
외부에 노출한다. main.py는 DB_TYPE이 무엇인지 알 필요 없이 항상 같은 이름으로 import한다.

[확장 방법]
MySQL 또는 Oracle을 지원하려면:
  1. repository/mysql/ 또는 repository/oracle/ 폴더에 구현체 파일을 작성한다.
  2. 아래 elif 블록의 주석을 해제하고 import 경로를 작성한다.
  3. .env 파일의 DB_TYPE 값을 변경하면 즉시 전환된다.
  4. service/ 계층과 views/ 계층은 수정하지 않아도 된다.

[현재 지원 DBMS]
  - DUCKDB (기본값)
"""

import os
from dotenv import load_dotenv

# .env 파일 로드 (파일이 없으면 시스템 환경 변수 사용)
load_dotenv()
# DB_TYPE을 대문자로 정규화. 기본값은 DUCKDB
DB_TYPE = os.getenv("DB_TYPE", "DUCKDB").upper()

# ===========================================================
# DB_TYPE에 따른 실제 구현체 매핑
# ===========================================================

if DB_TYPE == "DUCKDB":
    # DuckDB 구현체: repository/duckdb/ 폴더의 각 파일에서 import
    from .duckdb.connection import DuckDBManager as DatabaseManager
    from .duckdb.team_color import DuckDBTeamColorRepository as TeamColorRepository
    from .duckdb.category import DuckDBCategoryRepository as CategoryRepository
    from .duckdb.item import DuckDBItemRepository as ItemRepository
    from .duckdb.team import DuckDBTeamRepository as TeamRepository
    from .duckdb.trade import DuckDBTradeRepository as TradeRepository
    from .duckdb.roulette import DuckDBRouletteRepository as RouletteRepository
    from .duckdb.history import DuckDBHistoryQueryRepository as HistoryQueryRepository
    from .duckdb.system_image import DuckDBSystemImageRepository as SystemImageRepository

# elif DB_TYPE == "MYSQL":
#     # MySQL 구현체 (추후 확장 시 주석 해제)
#     from .mysql.connection import MySQLManager as DatabaseManager
#     ...

# elif DB_TYPE == "ORACLE":
#     # Oracle 구현체 (추후 확장 시 주석 해제)
#     from .oracle.connection import OracleManager as DatabaseManager
#     ...

else:
    raise ValueError(f"지원하지 않는 DB_TYPE 설정입니다: {DB_TYPE}")

# ===========================================================
# 활성화된 DB 환경 정보 출력
# ===========================================================
print(f"[INFO] Database: {DB_TYPE}")

# ===========================================================
# 패키지 외부 노출 심볼 목록
# ===========================================================
__all__ = [
    "DatabaseManager",
    "TeamColorRepository",
    "CategoryRepository",
    "ItemRepository",
    "TeamRepository",
    "TradeRepository",
    "RouletteRepository",
    "HistoryQueryRepository",
    "SystemImageRepository",
]
