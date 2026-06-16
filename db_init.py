"""
db_init.py
DDL 및 마스터 데이터 SQL 상수.
기존 db.py의 SCHEMA_DDL, MASTER_DATA_SQL을 분리하여
service/finance_service.py에서 import해 사용한다.
"""

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
    ('WINNER',   'assets/winner.png',   '우승 알림 이미지'),
    ('BANKRUPT', 'assets/bankrupt.png', '파산 알림 이미지');

INSERT INTO item (id, name, category_name, price, image_path, is_new) VALUES
    (1, '다이아몬드', '광물',  50000, 'assets/diamond.png',  FALSE),
    (2, '철괴',       '광물',   5000, 'assets/iron.png',     FALSE),
    (3, '에메랄드',   '광물', 100000, 'assets/emerald.png',  FALSE),
    (4, '금괴',       '광물',  30000, 'assets/gold.png',     FALSE),
    (5, '수박',       '식량',   2000, 'assets/melon.png',    FALSE),
    (6, '호박파이',   '식량',  32000, 'assets/pie.png',      FALSE),
    (7, '감자',       '식량',   1000, 'assets/potato.png',   FALSE),
    (8, '황금사과',   '식량',  50000, 'assets/gapple.png',   FALSE);
"""
