"""theme.py — 색상/포맷 상수 (픽셀 아트 스타일 팔레트)"""

BG_MAIN = "#BDBDBD"
BG_PANEL = "#3E2A14"
BG_BUTTON = "#7E5A2E"

TEXT_DARK = "#3E2A14"
TEXT_LIGHT = "#FFFFFF"
TEXT_MUTED = "#5A4632"
TEXT_GOLD = "#E0B84A"

ACCENT_RED = "#B8421C"
ACCENT_GREEN_DARK = "#5A8F2E"
ACCENT_ORANGE = "#C8761F"

TEAM_COLORS = {
    "YELLOW": "#D4A537", "BLUE": "#4A90D9", "PINK": "#D96BA0",
    "GREEN": "#7BC242", "PURPLE": "#A65BE2", "ORANGE": "#E27A3C",
}
TEAM_COLOR_LABELS = {
    "YELLOW": "노랑", "BLUE": "파랑", "PINK": "분홍",
    "GREEN": "초록", "PURPLE": "보라", "ORANGE": "주황",
}
TEAM_CARD_BG = {
    "YELLOW": "#F0E6CC", "BLUE": "#E6EFFA", "PINK": "#FAE7EE",
    "GREEN": "#ECF5DC", "PURPLE": "#F0E6F8", "ORANGE": "#FAEADD",
}
ITEM_EMOJIS = {
    "다이아몬드": "💎", "철괴": "⬜", "에메랄드": "🟢", "금괴": "🟨",
    "수박": "🍉", "호박파이": "🥧", "감자": "🥔", "황금사과": "🍎",
}

DEFAULT_INITIAL_BALANCE = 10_000_000
MIN_TEAMS = 2
MAX_TEAMS = 6


def format_won(amount: int) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}₩{abs(amount):,}"


def format_won_man(amount: int) -> str:
    if amount == 0:
        return "0원"
    sign = "-" if amount < 0 else ""
    a = abs(amount)
    if a >= 10000:
        return f"{sign}{a // 10000:,}만 원"
    return f"{sign}{a:,}원"
