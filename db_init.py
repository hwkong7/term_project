"""
db_init.py
DDL 및 마스터 데이터 SQL 상수 모음.

기존 db.py에 통합되어 있던 스키마 정의와 초기 마스터 데이터를
별도 모듈로 분리하여 관리한다.
service/finance_service.py의 FinanceService.initialize()에서
이 모듈을 import하여 데이터베이스 초기화에 사용한다.

[테이블 구성]
  team_color    : 팀 색상 마스터 (6가지 색상 코드 및 HEX 값)
  category      : 아이템 카테고리 마스터 (광물, 식량)
  system_image  : 파산/우승 다이얼로그에 표시되는 이미지 경로
  team          : 게임 참여 팀 정보 (잔액, HP 등)
  item          : 거래소 아이템 목록
  trade         : 아이템 판매 거래 기록
  roulette_spin : 룰렛 스핀 기록

[시퀀스]
  seq_team_id, seq_trade_id, seq_roulette_id
  각 테이블의 기본 키(PK)를 자동 증가시키는 DuckDB 시퀀스 객체
"""

# ===========================================================
# 스키마 DDL
# ===========================================================

SCHEMA_DDL = """
CREATE SEQUENCE IF NOT EXISTS seq_team_id START 1;
CREATE SEQUENCE IF NOT EXISTS seq_trade_id START 1;
CREATE SEQUENCE IF NOT EXISTS seq_roulette_id START 1;

CREATE TABLE IF NOT EXISTS team_color (
    code VARCHAR PRIMARY KEY,   -- 색상 코드 (예: YELLOW, BLUE)
    hex_value VARCHAR NOT NULL  -- HEX 색상값 (예: #D4A537)
);

CREATE TABLE IF NOT EXISTS category (
    name VARCHAR PRIMARY KEY  -- 카테고리명 (예: 광물, 식량)
);

CREATE TABLE IF NOT EXISTS system_image (
    key VARCHAR PRIMARY KEY,       -- 이미지 식별 키 (예: WINNER, BANKRUPT)
    image_path VARCHAR NOT NULL,   -- assets/ 기준 상대 경로
    description VARCHAR            -- 이미지 설명
);

CREATE TABLE IF NOT EXISTS team (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_team_id'),  -- 팀 대리 키 (자동 증가)
    name VARCHAR NOT NULL UNIQUE,      -- 팀 이름 (중복 불가)
    color_code VARCHAR NOT NULL UNIQUE,-- 팀 대표 색상 코드 (중복 불가)
    slogan VARCHAR,                    -- 팀 슬로건
    icon_path VARCHAR,                 -- 팀 아이콘 이미지 경로 (선택)
    initial_balance INTEGER NOT NULL CHECK (initial_balance > 0),  -- 초기 잔액
    current_balance INTEGER NOT NULL,  -- 현재 잔액
    hp_percent INTEGER NOT NULL DEFAULT 100
        CHECK (hp_percent BETWEEN 0 AND 100),  -- HP 비율 (0~100)
    registered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- 등록 시각
    FOREIGN KEY (color_code) REFERENCES team_color (code)
);

CREATE TABLE IF NOT EXISTS item (
    id INTEGER PRIMARY KEY,             -- 아이템 고유 번호
    name VARCHAR NOT NULL UNIQUE,       -- 아이템 이름 (중복 불가)
    category_name VARCHAR NOT NULL,     -- 카테고리 (FK → category.name)
    price INTEGER NOT NULL CHECK (price >= 0),  -- 단가 (0원 이상)
    image_path VARCHAR,                 -- 아이템 이미지 경로 (선택)
    is_new BOOLEAN NOT NULL DEFAULT FALSE,      -- 커스텀 추가 여부
    FOREIGN KEY (category_name) REFERENCES category (name)
);

CREATE TABLE IF NOT EXISTS trade (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_trade_id'),  -- 거래 고유 번호
    team_id INTEGER NOT NULL,     -- 판매한 팀 (FK → team.id)
    item_id INTEGER NOT NULL,     -- 판매한 아이템 (FK → item.id)
    quantity INTEGER NOT NULL CHECK (quantity > 0),   -- 판매 수량
    unit_price INTEGER NOT NULL CHECK (unit_price >= 0),  -- 판매 단가
    traded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- 거래 시각
    FOREIGN KEY (team_id) REFERENCES team (id),
    FOREIGN KEY (item_id) REFERENCES item (id)
);

CREATE TABLE IF NOT EXISTS roulette_spin (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_roulette_id'),  -- 스핀 고유 번호
    spinner_team_id INTEGER NOT NULL,  -- 룰렛을 돌린 팀 (FK → team.id)
    target_team_id INTEGER NOT NULL,   -- 패널티를 받은 팀 (FK → team.id)
    penalty_amount INTEGER NOT NULL CHECK (penalty_amount >= 0),  -- 차감 금액
    spin_cost INTEGER NOT NULL DEFAULT 100000,  -- 스핀 비용 (기본 ₩100,000)
    spun_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- 스핀 시각
    FOREIGN KEY (spinner_team_id) REFERENCES team (id),
    FOREIGN KEY (target_team_id) REFERENCES team (id)
);
"""

# ===========================================================
# 마스터 데이터 초기 INSERT SQL
# ===========================================================

MASTER_DATA_SQL = """
-- 팀 색상 마스터 (6가지 색상)
INSERT INTO team_color (code, hex_value) VALUES
    ('YELLOW', '#D4A537'),
    ('BLUE',   '#4A90D9'),
    ('PINK',   '#D96BA0'),
    ('GREEN',  '#7BC242'),
    ('PURPLE', '#A65BE2'),
    ('ORANGE', '#E27A3C');

-- 아이템 카테고리 마스터
INSERT INTO category (name) VALUES ('광물'), ('식량');

-- 시스템 이미지 마스터 (파산/우승 다이얼로그용)
INSERT INTO system_image (key, image_path, description) VALUES
    ('WINNER',   'assets/winner.png',   '우승 알림 이미지'),
    ('BANKRUPT', 'assets/bankrupt.png', '파산 알림 이미지');

-- 기본 아이템 마스터 (8종)
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
