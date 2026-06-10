"""
db.py
DuckDB 연결 관리 및 스키마 초기화.
설계서 6장 Logical Design의 DDL을 구현한다.
"""

import duckdb
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = str(DATA_DIR / "bankruptcy.duckdb")


SCHEMA_DDL = """
CREATE SEQUENCE IF NOT EXISTS seq_team_id START 1;
CREATE SEQUENCE IF NOT EXISTS seq_trade_id START 1;
CREATE SEQUENCE IF NOT EXISTS seq_roulette_id START 1;

CREATE TABLE IF NOT EXISTS team_color (
    code VARCHAR PRIMARY KEY,
    hex_value VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS category (
    name VARCHAR PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS system_image (
    key VARCHAR PRIMARY KEY,
    image_path VARCHAR NOT NULL,
    description VARCHAR
);

CREATE TABLE IF NOT EXISTS team (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_team_id'),
    name VARCHAR NOT NULL UNIQUE,
    color_code VARCHAR NOT NULL UNIQUE,
    slogan VARCHAR,
    icon_path VARCHAR,
    initial_balance INTEGER NOT NULL CHECK (initial_balance > 0),
    current_balance INTEGER NOT NULL,
    hp_percent INTEGER NOT NULL DEFAULT 100
        CHECK (hp_percent BETWEEN 0 AND 100),
    registered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (color_code) REFERENCES team_color (code)
);

CREATE TABLE IF NOT EXISTS item (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    category_name VARCHAR NOT NULL,
    price INTEGER NOT NULL CHECK (price >= 0),
    image_path VARCHAR,
    is_new BOOLEAN NOT NULL DEFAULT FALSE,
    is_custom BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (category_name) REFERENCES category (name)
);

CREATE TABLE IF NOT EXISTS trade (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_trade_id'),
    team_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price INTEGER NOT NULL CHECK (unit_price >= 0),
    traded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES team (id),
    FOREIGN KEY (item_id) REFERENCES item (id)
);

CREATE TABLE IF NOT EXISTS roulette_spin (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_roulette_id'),
    spinner_team_id INTEGER NOT NULL,
    target_team_id INTEGER NOT NULL,
    penalty_amount INTEGER NOT NULL CHECK (penalty_amount >= 0),
    spin_cost INTEGER NOT NULL DEFAULT 100000,
    spun_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (spinner_team_id) REFERENCES team (id),
    FOREIGN KEY (target_team_id) REFERENCES team (id)
);
"""

MASTER_DATA_SQL = """
INSERT INTO team_color (code, hex_value) VALUES
    ('YELLOW', '#D4A537'),
    ('BLUE',   '#4A90D9'),
    ('PINK',   '#D96BA0'),
    ('GREEN',  '#7BC242'),
    ('PURPLE', '#A65BE2'),
    ('ORANGE', '#E27A3C');

INSERT INTO category (name) VALUES ('광물'), ('식량');

INSERT INTO system_image (key, image_path, description) VALUES
    ('BANKRUPT', 'assets/bankrupt.png', '파산 알림 이미지');

INSERT INTO item (id, name, category_name, price, image_path, is_new) VALUES
    (1, '다이아몬드', '광물',  50000, 'assets/diamond.png',  FALSE),
    (2, '철괴',       '광물',   5000, 'assets/iron.png',     FALSE),
    (3, '에메랄드',   '광물', 100000, 'assets/emerald.png',  FALSE),
    (4, '금괴',       '광물',  30000, 'assets/gold.png',     FALSE),
    (5, '수박',       '식량',   2000, 'assets/melon.png',    FALSE),
    (6, '호박파이',   '식량',  32000, 'assets/pie.png',      TRUE),
    (7, '감자',       '식량',   1000, 'assets/potato.png',   FALSE),
    (8, '황금사과',   '식량',  50000, 'assets/gapple.png',   TRUE);
"""


class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(DB_PATH)
        self._init_schema_if_needed()
        self._initialized = True

    def _init_schema_if_needed(self):
        result = self.conn.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'team_color'
        """).fetchone()
        is_first_run = result[0] == 0

        self.conn.execute(SCHEMA_DDL)

        if is_first_run:
            self.conn.execute(MASTER_DATA_SQL)
            print("[DB] 스키마 및 마스터 데이터 초기화 완료")
        else:
            print("[DB] 기존 DB 연결")

        # 마이그레이션: is_custom 컬럼이 없으면 추가
        try:
            self.conn.execute("SELECT is_custom FROM item LIMIT 0")
        except Exception:
            self.conn.execute(
                "ALTER TABLE item ADD COLUMN is_custom BOOLEAN DEFAULT FALSE"
            )

    def reset_game_data(self):
        self.conn.execute("DELETE FROM roulette_spin")
        self.conn.execute("DELETE FROM trade")
        self.conn.execute("DELETE FROM team")
        for seq in ("seq_team_id", "seq_trade_id", "seq_roulette_id"):
            self.conn.execute(f"DROP SEQUENCE IF EXISTS {seq}")
            self.conn.execute(f"CREATE SEQUENCE {seq} START 1")
        print("[DB] 게임 데이터 초기화 완료")


db = Database()
