# 파산게임 시뮬레이터

마인크래프트 / 양띠 파산게임을 모티프로 만든 데스크톱 시뮬레이터.  
Python + Flet + DuckDB 기반으로 구현되었으며, 계층형 아키텍처(Repository / Service / View)를 적용했다.

---

## 🗂️ 프로젝트 구조

```
term_project/
├── main.py                    # Controller 및 Entry point, 화면 라우팅
├── db_init.py                 # DDL 및 마스터 데이터 SQL 상수
├── theme.py                   # 색상·포맷 상수
│
├── repository/                # 데이터 저장소 계층
│   ├── __init__.py            # DB_TYPE 설정에 따른 Repository 클래스 동적 할당
│   ├── interfaces.py          # Repository 인터페이스 (ABC)
│   └── duckdb/                # DuckDB 구현체
│       ├── connection.py      # DuckDB 연결 관리
│       ├── team_color.py
│       ├── category.py
│       ├── item.py
│       ├── team.py
│       ├── trade.py
│       ├── roulette.py
│       ├── history.py         # ★ 4개 테이블 JOIN + UNION ALL
│       └── system_image.py
│
├── service/                   # 비즈니스 로직 계층
│   ├── __init__.py
│   └── finance_service.py     # TeamService / ItemService / TradeService 등
│
├── views/                     # Flet UI 계층
│   ├── __init__.py
│   ├── _helpers.py
│   ├── dialogs.py             # 파산·우승 다이얼로그
│   ├── team_registration.py   # UC-01 팀 등록
│   ├── team_selection.py      # UC-02 팀 선택
│   ├── dashboard.py           # UC-03 대시보드
│   ├── marketplace.py         # UC-04 아이템 거래소
│   ├── roulette.py            # UC-05 룰렛
│   └── history.py             # UC-06 자금 흐름
│
├── assets/                    # 이미지 파일
├── data/                      # DuckDB 파일 저장 위치
├── .env                       # 환경 설정 (git 제외)
├── .env.example               # 환경 설정 예시
├── pyproject.toml
└── requirements.txt
```

---

## 🛠️ uv 설치 (최초 1회)

이미 설치되어 있다면 건너뜀

Windows
```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS / Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## ⚙️ .env 파일 생성

프로젝트 폴더에 있는 `.env.example`을 복사해 `.env` 파일 생성

```bash
cp .env.example .env
```

현재 DuckDB만 지원하므로 기본값 그대로 사용 가능  
추후 MySQL / Oracle 확장 시 `.env`의 `DB_TYPE` 값만 변경

---

## 🏗️ 의존성 설치

```bash
uv sync
```

`.venv`가 자동 생성되고 패키지가 설치됨

---

## ▶️ 실행

```bash
uv run flet run main.py
```

핫 리로드 (코드 변경 시 자동 재시작)

```bash
uv run flet run -r --ignore data/ main.py
```

브라우저 모드로 실행 (문제 발생 시)

```bash
uv run flet run --web -r --ignore data/ main.py
```

---

## 🎮 게임 진행 방법

1. **팀 등록** — 팀 이름, 색상, 슬로건, 초기 잔액 설정 후 게임 시작
2. **팀 선택** — 내 팀을 선택해 대시보드 진입
3. **거래소** — 아이템을 판매해 잔액 획득. 커스텀 아이템 추가 가능
4. **룰렛** — ₩100,000 비용으로 룰렛 돌리기. 무작위 팀에게 패널티 부과
5. **자금 흐름** — 판매·룰렛 이벤트 이력 조회
6. **우승 조건** — 다른 팀이 모두 파산(잔액 0원)하면 최후 생존팀 우승

---

## 🏛️ 아키텍처 설계 원칙

| 원칙 | 적용 내용 |
|------|-----------|
| DIP (의존성 역전) | Service는 Repository 인터페이스(ABC)에만 의존 |
| OCP (개방-폐쇄) | DB 교체 시 `duckdb/` 폴더만 추가, Service 수정 불필요 |
| SRP (단일 책임) | Repository(SQL) / Service(비즈니스 로직) / View(UI) 완전 분리 |
| Strategy Pattern | `.env`의 `DB_TYPE`으로 런타임에 구현체 동적 선택 |

---

## 🛠️ 기술 스택

| 항목 | 버전 |
|------|------|
| Python | 3.13 |
| Flet | 0.85.2 |
| DuckDB | 1.5.3 |
| pandas | 3.0.3 |
| python-dotenv | 1.0.0 이상 |
| 패키지 매니저 | uv |