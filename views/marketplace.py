"""
views/marketplace.py
거래소 화면 (4.1 + 4.3) — NEW탭 커스텀 아이템 추가 포함.
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
from services import ItemService, TradeService, TradeError
from views._helpers import _snack


CATEGORY_TABS = ["전체", "광물", "식량", "NEW"]


class ItemCard(ft.Container):
    def __init__(self, item, on_sell):
        self.item = item
        self.on_sell = on_sell
        # image_path가 있으면 이미지, 없으면 이모지
        image_path = item.get("image_path")
        if image_path:
            icon_widget = ft.Image(
                src=image_path,
                width=80,
                height=80,
                fit=ft.BoxFit.CONTAIN,
                error_content=ft.Text(
                    ITEM_EMOJIS.get(item["name"], "📦"), size=44
                ),
            )
        else:
            emoji = ITEM_EMOJIS.get(item["name"], "📦")
            icon_widget = ft.Text(emoji, size=44)

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
        sell_btn = ft.Container(
            content=ft.Text(
                "판매", color=TEXT_LIGHT, size=13, weight=ft.FontWeight.W_500
            ),
            bgcolor=ACCENT_GREEN_DARK,
            border=ft.Border.all(2, TEXT_DARK),
            width=70,
            height=40,
            alignment=ft.Alignment.CENTER,
            on_click=self._on_sell_click,
        )
        super().__init__(
            content=ft.Column(
                [
                    ft.Container(
                        content=icon_widget,
                        bgcolor="#5A4632",
                        height=110,
                        alignment=ft.Alignment.CENTER,
                        border=ft.Border.all(1, TEXT_DARK),
                    ),
                    ft.Text(
                        item["name"],
                        size=15,
                        weight=ft.FontWeight.W_500,
                        color=TEXT_DARK,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        f"[{item['category']}]",
                        size=11,
                        color=TEXT_MUTED,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        format_won(int(item["price"])),
                        size=16,
                        weight=ft.FontWeight.W_500,
                        color=ACCENT_ORANGE,
                        text_align=ft.TextAlign.CENTER,
                    ),
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
        try:
            qty = int(self.qty_field.value or 0)
        except ValueError:
            qty = 0
        self.on_sell(self.item["id"], self.item["name"], qty)


class MarketplaceView(ft.Column):
    def __init__(
        self, item_service: ItemService, trade_service: TradeService,
        current_team_id, get_team_info, on_back
    ):
        super().__init__(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        self.item_service = item_service
        self.trade_service = trade_service
        self.current_team_id = current_team_id
        self.get_team_info = get_team_info
        self.on_back = on_back
        self.active_category = "전체"
        self._file_picker = None
        self._picked_image_path = None
        self._build()

    def did_mount(self):
        self._file_picker = ft.FilePicker()
        self._file_picker.on_result = self._on_file_picked
        self.page.overlay.append(self._file_picker)
        self.page.update()

    def will_unmount(self):
        if self._file_picker and self._file_picker in self.page.overlay:
            self.page.overlay.remove(self._file_picker)
            self.page.update()

    def _build(self):
        self.controls.clear()
        self.controls.append(self._build_header())
        self.controls.append(self._build_category_tabs())
        if self.active_category == "NEW":
            self.controls.append(self._build_new_tab())
        else:
            self.controls.append(self._build_item_grid())

    def _build_header(self):
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
                    self._team_badge(team),
                ],
                spacing=12,
            ),
            bgcolor=BG_PANEL,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        )

    def _team_badge(self, team):
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
        tabs = []
        for cat in CATEGORY_TABS:
            sel = cat == self.active_category
            tabs.append(
                ft.Container(
                    content=ft.Text(
                        cat, color=TEXT_LIGHT, size=14, weight=ft.FontWeight.W_500
                    ),
                    bgcolor=BG_BUTTON if sel else "#9A9A9A",
                    border=ft.Border.all(2, TEXT_DARK),
                    width=110,
                    height=44,
                    alignment=ft.Alignment.CENTER,
                    data=cat,
                    on_click=self._on_tab_click,
                )
            )
        return ft.Container(
            content=ft.Row(tabs, spacing=10),
            padding=ft.Padding.symmetric(horizontal=16, vertical=4),
        )

    def _build_item_grid(self):
        items = self.item_service.find_items(self.active_category)
        cards = [ItemCard(it.to_dict(), self._on_sell) for _, it in items.iterrows()]
        grid = ft.Row(cards, spacing=12, wrap=True, run_spacing=12)
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
        # 카테고리 목록
        cats_df = self.item_service.category_repo.find_all()
        cat_options = [ft.dropdown.Option(row["name"]) for _, row in cats_df.iterrows()]

        self._new_name_field = ft.TextField(
            label="아이템 이름",
            text_size=13,
            border_color=TEXT_DARK,
            bgcolor=ft.Colors.WHITE,
            color=TEXT_DARK,
            label_style=ft.TextStyle(color=TEXT_MUTED, size=11),
            width=200,
        )
        self._new_cat_dropdown = ft.Dropdown(
            label="카테고리",
            options=cat_options,
            value=cat_options[0].key if cat_options else None,
            width=150,
            text_size=13,
            border_color=TEXT_DARK,
            bgcolor=ft.Colors.WHITE,
            color=TEXT_DARK,
            label_style=ft.TextStyle(color=TEXT_MUTED, size=11),
        )
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
        self._file_name_text = ft.Text(
            "선택된 파일 없음",
            size=12,
            color=TEXT_MUTED,
        )
        pick_btn = ft.Container(
            content=ft.Text(
                "🖼 이미지 선택", color=TEXT_LIGHT, size=13, weight=ft.FontWeight.W_500
            ),
            bgcolor="#5A4632",
            border=ft.Border.all(2, TEXT_DARK),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            on_click=self._on_pick_file_click,
        )
        add_btn = ft.Container(
            content=ft.Text(
                "➕ 아이템 추가", color=TEXT_LIGHT, size=14, weight=ft.FontWeight.W_500
            ),
            bgcolor=ACCENT_GREEN_DARK,
            border=ft.Border.all(2, TEXT_DARK),
            padding=ft.Padding.symmetric(horizontal=20, vertical=10),
            on_click=self._on_add_item_click,
        )

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
                        [self._new_name_field, self._new_cat_dropdown, self._new_price_field],
                        spacing=12,
                        wrap=True,
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

        # 커스텀 아이템 목록
        custom_items = self.item_service.find_custom_items()
        if len(custom_items) == 0:
            items_section_content = ft.Text(
                "추가된 커스텀 아이템이 없습니다.", size=13, color=TEXT_MUTED
            )
        else:
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

    def _on_pick_file_click(self, e):
        if self._file_picker:
            self._file_picker.pick_files(
                allowed_extensions=["png", "jpg", "jpeg", "gif", "bmp"],
                allow_multiple=False,
            )

    def _on_file_picked(self, e):
        if e.files:
            self._picked_image_path = e.files[0].path
            if hasattr(self, "_file_name_text"):
                self._file_name_text.value = e.files[0].name
                self._file_name_text.update()
        else:
            self._picked_image_path = None

    def _on_add_item_click(self, e):
        name = (getattr(self, "_new_name_field", None) and self._new_name_field.value or "").strip()
        cat = getattr(self, "_new_cat_dropdown", None) and self._new_cat_dropdown.value
        price_str = (getattr(self, "_new_price_field", None) and self._new_price_field.value or "").strip()
        try:
            price = int(price_str) if price_str else 0
        except ValueError:
            price = -1

        try:
            self.item_service.add_custom_item(name, cat or "", price, self._picked_image_path)
            _snack(self.page, f"✅ '{name}' 아이템 추가 완료!", ACCENT_GREEN_DARK)
            self._picked_image_path = None
            # NEW탭 rebuild
            self.active_category = "NEW"
            self._build()
            self.update()
        except ValueError as ex:
            _snack(self.page, f"⚠ {ex}", ACCENT_RED)
        except Exception as ex:
            _snack(self.page, f"⚠ 오류: {ex}", ACCENT_RED)

    def _on_tab_click(self, e):
        self.active_category = e.control.data
        self._build()
        self.update()

    def _on_sell(self, item_id, item_name, qty):
        try:
            result = self.trade_service.create_trade(self.current_team_id, item_id, qty)
            _snack(
                self.page,
                f"✅ {item_name} {qty}개 판매! (+{format_won(result['total_amount'])})",
                ACCENT_GREEN_DARK,
            )
            self.controls[0] = self._build_header()
            self.update()
        except TradeError as ex:
            _snack(self.page, f"⚠ {ex}", ACCENT_RED)
        except Exception as ex:
            _snack(self.page, f"⚠ 오류: {ex}", ACCENT_RED)
