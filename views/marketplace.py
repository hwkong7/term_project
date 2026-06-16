"""
views/marketplace.py
거래소 화면 (4.1 + 4.3) — NEW탭 커스텀 아이템 추가 포함.

플레이어가 보유한 아이템을 판매해 잔액을 늘리는 화면.
탭 구성:
  전체  : 모든 기본 아이템 표시
  광물  : 광물 카테고리 아이템만 표시
  식량  : 식량 카테고리 아이템만 표시
  NEW   : 커스텀 아이템 추가 폼 + 추가된 커스텀 아이템 목록

ItemCard: 아이템 1개를 표시하는 카드 컴포넌트 (이미지/이모지 + 이름 + 가격 + 판매 폼)
MarketplaceView: 탭 전환 + 아이템 그리드 + 헤더(잔액 표시) 포함 전체 화면 뷰
"""

import flet as ft
from typing import Callable

from theme import (
    BG_PANEL,
    BG_BUTTON,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    TEXT_GOLD,
    ACCENT_RED,
    ACCENT_GREEN_DARK,
    ACCENT_ORANGE,
    TEAM_COLORS,
    ITEM_EMOJIS,
    format_won,
)
from service import ItemService, TradeService, TradeError
from views._helpers import _snack


# 거래소 탭 목록 (순서가 UI에 그대로 표시됨)
CATEGORY_TABS = ["전체", "광물", "식량", "NEW"]


class ItemCard(ft.Container):
    """
    아이템 카드 컴포넌트 (거래소 그리드의 단일 항목).

    표시 내용:
      - 상단: 아이템 이미지 (없으면 이모지 폴백)
      - 아이템 이름 / 카테고리 / 단가
      - 수량 입력 TextField + 판매 버튼

    클릭 흐름:
      판매 버튼 → _on_sell_click → on_sell(item_id, item_name, qty)
                → MarketplaceView._on_sell → TradeService.create_trade
    """

    def __init__(self, item, on_sell):
        """
        Args:
            item   : 아이템 정보 딕셔너리 (id, name, category, price, image_path, is_new)
            on_sell: 판매 버튼 클릭 시 호출 콜백 (item_id, item_name, qty)
        """
        self.item    = item
        self.on_sell = on_sell

        # 이미지 경로가 있으면 ft.Image로 표시, 없으면 이모지 텍스트로 폴백
        image_path = item.get("image_path")
        if image_path:
            icon_widget = ft.Image(
                src=image_path,           # assets/ 기준 상대 경로
                width=80,
                height=80,
                fit=ft.BoxFit.CONTAIN,    # 비율 유지하며 박스에 맞춤
                error_content=ft.Text(    # 이미지 로드 실패 시 이모지로 폴백
                    ITEM_EMOJIS.get(item["name"], "📦"), size=44
                ),
            )
        else:
            # image_path가 None이면 이모지 텍스트로 직접 표시
            emoji       = ITEM_EMOJIS.get(item["name"], "📦")
            icon_widget = ft.Text(emoji, size=44)

        # 수량 입력 필드 (기본값 1, 숫자 키보드)
        self.qty_field = ft.TextField(
            value="1",
            width=80,
            height=40,
            text_size=13,
            text_align=ft.TextAlign.CENTER,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=TEXT_DARK,
            bgcolor=ft.Colors.WHITE,
            color=TEXT_DARK,
        )

        # 판매 버튼
        sell_btn = ft.Container(
            content=ft.Text(
                "판매", color=TEXT_LIGHT, size=13, weight=ft.FontWeight.W_500
            ),
            bgcolor=ACCENT_GREEN_DARK,             # 초록색 — 긍정적 행동
            border=ft.Border.all(2, TEXT_DARK),
            width=70,
            height=40,
            alignment=ft.Alignment.CENTER,
            on_click=self._on_sell_click,
        )

        # 카드 레이아웃 구성
        super().__init__(
            content=ft.Column(
                [
                    # 아이템 이미지 영역
                    ft.Container(
                        content=icon_widget,
                        bgcolor="#5A4632",                  # 어두운 갈색 배경
                        height=110,
                        alignment=ft.Alignment.CENTER,
                        border=ft.Border.all(1, TEXT_DARK),
                    ),
                    # 아이템 이름
                    ft.Text(
                        item["name"],
                        size=15,
                        weight=ft.FontWeight.W_500,
                        color=TEXT_DARK,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    # 카테고리 (대괄호로 감쌈)
                    ft.Text(
                        f"[{item['category']}]",
                        size=11,
                        color=TEXT_MUTED,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    # 단가
                    ft.Text(
                        format_won(int(item["price"])),
                        size=16,
                        weight=ft.FontWeight.W_500,
                        color=ACCENT_ORANGE,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    # 수량 입력 + 판매 버튼
                    ft.Row(
                        [self.qty_field, sell_btn],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6,
                    ),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="#E8DCC0",
            border=ft.Border.all(2, "#6B4F2E"),
            border_radius=4,
            padding=10,
            width=210,
        )

    def _on_sell_click(self, e):
        """
        판매 버튼 클릭 이벤트 핸들러.
        qty_field에서 수량을 파싱해 on_sell 콜백을 호출한다.
        수량 파싱 실패 시 0을 전달 (서비스 계층에서 '1 이상' 검증).
        """
        try:
            qty = int(self.qty_field.value or 0)
        except ValueError:
            qty = 0   # 숫자가 아닌 입력 시 0으로 처리
        self.on_sell(self.item["id"], self.item["name"], qty)


class MarketplaceView(ft.Column):
    """
    거래소 화면 전체 뷰.

    구성:
      1. 헤더: BACK 버튼 + '거래소' 제목 + 현재 팀 잔액 배지
      2. 카테고리 탭 (전체/광물/식량/NEW)
      3. 아이템 그리드 (선택된 탭 기준) 또는 NEW탭 폼
    """

    def __init__(
        self,
        item_service: ItemService,
        trade_service: TradeService,
        current_team_id,
        get_team_info,
        on_back,
    ):
        """
        Args:
            item_service    : 아이템 조회 및 커스텀 추가 서비스
            trade_service   : 판매 거래 처리 서비스
            current_team_id : 현재 플레이어의 팀 ID
            get_team_info   : team_id → 팀 정보 딕셔너리 콜백 (헤더 잔액 갱신용)
            on_back         : BACK 버튼 클릭 콜백 (→ 대시보드)
        """
        super().__init__(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        self.item_service    = item_service
        self.trade_service   = trade_service
        self.current_team_id = current_team_id
        self.get_team_info   = get_team_info
        self.on_back         = on_back
        self.active_category = "전체"        # 현재 활성화된 탭
        self._picked_image_path = None       # NEW탭에서 선택된 이미지 파일 경로
        self._build()

    def _build(self):
        """현재 active_category에 맞게 화면을 빌드한다."""
        self.controls.clear()
        self.controls.append(self._build_header())
        self.controls.append(self._build_category_tabs())
        if self.active_category == "NEW":
            # NEW 탭: 커스텀 아이템 추가 폼 + 목록
            self.controls.append(self._build_new_tab())
        else:
            # 일반 탭: 아이템 카드 그리드
            self.controls.append(self._build_item_grid())

    def _build_header(self):
        """
        헤더: BACK 버튼 + '🛒 거래소' 제목 + 현재 팀 배지(잔액 포함).
        판매 후 헤더만 갱신할 때 self.controls[0]을 이 메서드로 교체한다.
        """
        team = self.get_team_info(self.current_team_id)
        return ft.Container(
            content=ft.Row(
                [
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
                    ft.Text(
                        "🛒 거래소",
                        color=TEXT_LIGHT,
                        size=20,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.Container(expand=True),
                    self._team_badge(team),   # 현재 팀 잔액 배지
                ],
                spacing=12,
            ),
            bgcolor=BG_PANEL,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        )

    def _team_badge(self, team):
        """현재 팀 색상 + 이름 + 잔액을 표시하는 헤더 우측 배지."""
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Text(":)", size=14, color=TEXT_DARK),
                        width=28,
                        height=28,
                        bgcolor=TEAM_COLORS[team["color_code"]],
                        border=ft.Border.all(2, TEXT_DARK),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Text(
                        f"{team['name']}팀",
                        color=TEXT_LIGHT,
                        size=14,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.Text("잔액", color=TEXT_MUTED, size=12),
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
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        )

    def _build_category_tabs(self):
        """
        카테고리 탭 버튼 행 빌드.
        현재 active_category의 탭은 활성 색상(#5A3F1F)으로 표시된다.
        """
        tabs = []
        for cat in CATEGORY_TABS:
            sel = cat == self.active_category
            tabs.append(
                ft.Container(
                    content=ft.Text(
                        cat,
                        color=TEXT_LIGHT,
                        size=13,
                        weight=ft.FontWeight.W_500,
                    ),
                    bgcolor="#5A3F1F" if sel else "#9A9A9A",   # 선택: 활성색 / 미선택: 회색
                    border=ft.Border.all(2, TEXT_DARK),
                    width=80,
                    height=36,
                    alignment=ft.Alignment.CENTER,
                    data=cat,                        # 탭에 카테고리명을 data로 저장
                    on_click=self._on_tab_click,
                )
            )
        return ft.Container(
            content=ft.Row(tabs, spacing=10),
            padding=ft.Padding.symmetric(horizontal=16, vertical=4),
        )

    def _build_item_grid(self):
        """
        선택된 카테고리의 아이템 카드 그리드 빌드.
        ItemService.find_items(active_category)로 아이템을 조회하고
        각각 ItemCard로 변환해 Row(wrap=True)에 배치한다.
        """
        items = self.item_service.find_items(self.active_category)
        # DataFrame의 각 행을 ItemCard로 변환 (to_dict()로 딕셔너리 변환)
        cards = [ItemCard(it.to_dict(), self._on_sell) for _, it in items.iterrows()]
        grid  = ft.Row(cards, spacing=12, wrap=True, run_spacing=12)
        return ft.Container(
            content=ft.Container(
                content=grid,
                bgcolor="#8B6B45",
                border=ft.Border.all(3, "#3E2A14"),
                padding=16,
            ),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _build_new_tab(self):
        """
        NEW 탭 콘텐츠 빌드.
        상단: 커스텀 아이템 추가 폼 (이름, 카테고리, 가격, 이미지 선택)
        하단: 추가된 커스텀 아이템 목록 (ItemCard 그리드)
        """
        # DB에서 카테고리 목록 조회해 드롭다운 옵션 생성
        cats_df     = self.item_service.category_repo.find_all()
        cat_options = [ft.dropdown.Option(row["name"]) for _, row in cats_df.iterrows()]

        # 아이템 이름 입력 필드
        self._new_name_field = ft.TextField(
            label="아이템 이름",
            text_size=13,
            border_color=TEXT_DARK,
            bgcolor=ft.Colors.WHITE,
            color=TEXT_DARK,
            label_style=ft.TextStyle(color=TEXT_MUTED, size=11),
            width=200,
        )
        # 카테고리 드롭다운
        self._new_cat_dropdown = ft.Dropdown(
            label="카테고리",
            options=cat_options,
            value=cat_options[0].key if cat_options else None,   # 첫 번째 카테고리 선택
            width=150,
            text_size=13,
            border_color=TEXT_DARK,
            bgcolor=ft.Colors.WHITE,
            color=TEXT_DARK,
            label_style=ft.TextStyle(color=TEXT_MUTED, size=11),
        )
        # 가격 입력 필드 (숫자 키보드)
        self._new_price_field = ft.TextField(
            label="가격 (원)",
            text_size=13,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=TEXT_DARK,
            bgcolor=ft.Colors.WHITE,
            color=TEXT_DARK,
            label_style=ft.TextStyle(color=TEXT_MUTED, size=11),
            width=150,
        )
        # 선택된 이미지 파일명 표시 텍스트
        self._file_name_text = ft.Text(
            "선택된 파일 없음",
            size=12,
            color=TEXT_MUTED,
        )
        # 이미지 파일 선택 버튼
        pick_btn = ft.Container(
            content=ft.Text(
                "🖼 이미지 선택", color=TEXT_LIGHT, size=13, weight=ft.FontWeight.W_500
            ),
            bgcolor="#5A4632",
            border=ft.Border.all(2, TEXT_DARK),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            on_click=self._on_pick_file_click,
        )
        # 아이템 추가 버튼
        add_btn = ft.Container(
            content=ft.Text(
                "➕ 아이템 추가", color=TEXT_LIGHT, size=14, weight=ft.FontWeight.W_500
            ),
            bgcolor=ACCENT_GREEN_DARK,
            border=ft.Border.all(2, TEXT_DARK),
            padding=ft.Padding.symmetric(horizontal=20, vertical=10),
            on_click=self._on_add_item_click,
        )

        # 추가 폼 섹션
        form_section = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(width=4, height=20, bgcolor=TEXT_DARK),
                            ft.Text(
                                "커스텀 아이템 추가",
                                size=15,
                                weight=ft.FontWeight.W_500,
                                color=TEXT_DARK,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        [
                            self._new_name_field,
                            self._new_cat_dropdown,
                            self._new_price_field,
                        ],
                        spacing=12,
                        wrap=True,   # 창 너비가 좁을 때 자동 줄바꿈
                    ),
                    ft.Row(
                        [pick_btn, self._file_name_text],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    add_btn,
                ],
                spacing=12,
            ),
            bgcolor="#F5EDD8",
            border=ft.Border.all(2, TEXT_DARK),
            padding=16,
        )

        # 커스텀 아이템 목록 섹션
        custom_items = self.item_service.find_new_items()
        if len(custom_items) == 0:
            # 추가된 커스텀 아이템이 없을 때 안내 텍스트
            items_section_content = ft.Text(
                "추가된 커스텀 아이템이 없습니다.", size=13, color=TEXT_MUTED
            )
        else:
            # 커스텀 아이템들을 ItemCard 그리드로 표시
            cards = [
                ItemCard(it.to_dict(), self._on_sell)
                for _, it in custom_items.iterrows()
            ]
            items_section_content = ft.Row(cards, spacing=12, wrap=True, run_spacing=12)

        items_section = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(width=4, height=20, bgcolor=TEXT_DARK),
                            ft.Text(
                                "커스텀 아이템 목록",
                                size=15,
                                weight=ft.FontWeight.W_500,
                                color=TEXT_DARK,
                            ),
                        ],
                        spacing=8,
                    ),
                    items_section_content,
                ],
                spacing=12,
            ),
            bgcolor="#8B6B45",
            border=ft.Border.all(3, "#3E2A14"),
            padding=16,
        )

        return ft.Container(
            content=ft.Column(
                [form_section, items_section],
                spacing=16,
            ),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    async def _on_pick_file_click(self, e):
        """
        이미지 파일 선택 버튼 클릭 핸들러 (async).
        Flet 0.85.x 방식: await fp.pick_files()로 파일 피커를 호출한다.
        선택된 파일 경로를 _picked_image_path에 저장하고 파일명을 UI에 표시한다.
        허용 확장자: png, jpg, jpeg, gif, bmp
        """
        fp = ft.FilePicker()
        files = await fp.pick_files(
            allowed_extensions=["png", "jpg", "jpeg", "gif", "bmp"],
            allow_multiple=False,   # 단일 파일만 선택 가능
        )
        if files:
            # 선택된 파일 경로 및 이름 저장
            self._picked_image_path = files[0].path
            if hasattr(self, "_file_name_text"):
                self._file_name_text.value = files[0].name   # 파일명을 UI에 표시
                self._file_name_text.update()
        else:
            # 파일 선택 취소 시 초기화
            self._picked_image_path = None

    def _on_add_item_click(self, e):
        """
        '아이템 추가' 버튼 클릭 핸들러.
        폼 입력값(이름, 카테고리, 가격, 이미지 경로)을 수집해
        ItemService.add_custom_item()을 호출한다.
        성공 시 NEW탭을 재빌드하고, 실패 시 오류 스낵바를 표시한다.
        """
        # 폼 입력값 수집 (None 안전 처리)
        name = (
            getattr(self, "_new_name_field", None) and self._new_name_field.value or ""
        ).strip()
        cat = getattr(self, "_new_cat_dropdown", None) and self._new_cat_dropdown.value
        price_str = (
            getattr(self, "_new_price_field", None)
            and self._new_price_field.value
            or ""
        ).strip()

        # 가격 파싱 (실패 시 -1로 처리 → 서비스 계층에서 유효성 검사)
        try:
            price = int(price_str) if price_str else 0
        except ValueError:
            price = -1   # 잘못된 입력 → ItemService에서 오류 발생

        try:
            self.item_service.add_custom_item(
                name, cat or "", price, self._picked_image_path
            )
            _snack(self.page, f"✅ '{name}' 아이템 추가 완료!", ACCENT_GREEN_DARK)
            self._picked_image_path = None   # 이미지 경로 초기화

            # NEW탭을 새로 빌드해 추가된 아이템을 목록에 반영
            self.active_category = "NEW"
            self._build()
            self.update()
        except ValueError as ex:
            # ItemService의 유효성 검사 실패 (빈 이름, 음수 가격 등)
            _snack(self.page, f"⚠ {ex}", ACCENT_RED)
        except Exception as ex:
            # 예상치 못한 오류
            _snack(self.page, f"⚠ 오류: {ex}", ACCENT_RED)

    def _on_tab_click(self, e):
        """카테고리 탭 클릭 시 active_category를 변경하고 화면을 재빌드한다."""
        self.active_category = e.control.data   # e.control.data = 카테고리명
        self._build()
        self.update()

    def _on_sell(self, item_id, item_name, qty):
        """
        ItemCard의 '판매' 버튼에서 호출되는 콜백.
        TradeService.create_trade()로 거래를 처리하고
        성공 시 헤더 잔액을 갱신하며 스낵바로 결과를 알린다.
        """
        try:
            result = self.trade_service.create_trade(self.current_team_id, item_id, qty)
            _snack(
                self.page,
                f"✅ {item_name} {qty}개 판매! (+{format_won(result['total_amount'])})",
                ACCENT_GREEN_DARK,
            )
            # 헤더만 갱신 (잔액이 바뀌었으므로) — 전체 재빌드보다 효율적
            self.controls[0] = self._build_header()
            self.update()
        except TradeError as ex:
            # 수량 부족, 아이템 미존재 등 거래 오류
            _snack(self.page, f"⚠ {ex}", ACCENT_RED)
        except Exception as ex:
            # 예상치 못한 오류
            _snack(self.page, f"⚠ 오류: {ex}", ACCENT_RED)
