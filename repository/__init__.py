"""
repository/__init__.py
.env 파일의 DB_TYPE 설정에 따른 Repository 클래스 동적 할당.
"""

import os
from dotenv import load_dotenv

load_dotenv()
DB_TYPE = os.getenv("DB_TYPE", "DUCKDB").upper()

if DB_TYPE == "DUCKDB":
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
#     from .mysql.connection import MySQLManager as DatabaseManager
#     ...

else:
    raise ValueError(f"지원하지 않는 DB_TYPE 설정입니다: {DB_TYPE}")

print(f"[INFO] Database: {DB_TYPE}")

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
