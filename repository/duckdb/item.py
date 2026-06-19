"""
repository/duckdb/item.py
아이템(상품) DuckDB 구현체.

IItemRepository 인터페이스를 구현한다.
item 테이블은 거래소에서 판매 가능한 상품 목록을 저장한다.

[주요 쿼리]
  find_all()        : item ⨝ category (INNER JOIN으로 카테고리명 포함)
  find_by_category(): WHERE category_name = ? 필터링
  find_new_items()  : WHERE is_new = TRUE (커스텀 추가 아이템만)
  save_one()        : MAX(id) + 1로 새 id를 직접 계산하여 INSERT
                      (item 테이블은 시퀀스 미사용, 기본 아이템 id를 1~8로 고정)
"""

import pandas as pd
from typing import Optional
from ..interfaces import IItemRepository


class DuckDBItemRepository(IItemRepository):
    """item 테이블 DuckDB 구현체."""

    def create_table(self) -> None:
        """item 테이블이 없으면 생성한다."""
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS item (
                id            INTEGER   PRIMARY KEY,               -- 아이템 고유 번호
                name          VARCHAR   NOT NULL UNIQUE,           -- 아이템 이름
                category_name VARCHAR   NOT NULL,                  -- 카테고리 (FK)
                price         INTEGER   NOT NULL CHECK (price >= 0), -- 단가
                image_path    VARCHAR,                             -- 이미지 경로 (선택)
                is_new        BOOLEAN   NOT NULL DEFAULT FALSE,    -- 커스텀 추가 여부
                FOREIGN KEY (category_name) REFERENCES category (name)
            )
        """)

    def count(self) -> int:
        """item 테이블의 전체 행 수를 반환한다."""
        return self._con.execute("SELECT COUNT(*) FROM item").fetchone()[0]

    def save(self, df: pd.DataFrame) -> None:
        """아이템 목록을 일괄 INSERT한다 (마스터 데이터 초기 적재용)."""
        self._con.execute(
            "INSERT INTO item (id, name, category_name, price, image_path, is_new) "
            "SELECT id, name, category_name, price, image_path, is_new FROM df"
        )

    def find_by_id(self, item_id: int) -> Optional[dict]:
        """
        PK(id)로 아이템 단건을 조회한다.
        없으면 None, 있으면 딕셔너리(id, name, category_name, price, image_path, is_new)를 반환한다.
        """
        row = self._con.execute(
            "SELECT id, name, category_name, price, image_path, is_new "
            "FROM item WHERE id = ?",
            [item_id],
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0], "name": row[1], "category_name": row[2],
            "price": row[3], "image_path": row[4], "is_new": row[5],
        }

    def find_all(self) -> pd.DataFrame:
        """
        전체 아이템 목록을 category와 INNER JOIN하여 반환한다.
        반환 컬럼: id, name, category(카테고리명), price, image_path, is_new
        """
        return self._con.execute("""
            SELECT i.id, i.name, c.name AS category, i.price, i.image_path, i.is_new
            FROM item i INNER JOIN category c ON i.category_name = c.name ORDER BY i.id
        """).fetchdf()

    def find_by_category(self, category_name: str) -> pd.DataFrame:
        """특정 카테고리의 아이템만 필터링하여 category JOIN 포함 DataFrame으로 반환한다."""
        return self._con.execute("""
            SELECT i.id, i.name, c.name AS category, i.price, i.image_path, i.is_new
            FROM item i INNER JOIN category c ON i.category_name = c.name
            WHERE i.category_name = ? ORDER BY i.id
        """, [category_name]).fetchdf()

    def find_new_items(self) -> pd.DataFrame:
        """is_new=TRUE인 커스텀 추가 아이템만 반환한다."""
        return self._con.execute("""
            SELECT i.id, i.name, c.name AS category, i.price, i.image_path, i.is_new
            FROM item i INNER JOIN category c ON i.category_name = c.name
            WHERE i.is_new = TRUE ORDER BY i.id
        """).fetchdf()

    def save_one(self, name: str, category_name: str, price: int, image_path) -> int:
        """
        커스텀 아이템 1건을 INSERT하고 새로 부여된 id를 반환한다.
        COALESCE(MAX(id), 0) + 1 으로 현재 최대 id보다 1 큰 값을 새 id로 사용한다.
        """
        new_id = self._con.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM item"
        ).fetchone()[0]
        self._con.execute(
            "INSERT INTO item (id, name, category_name, price, image_path, is_new) "
            "VALUES (?, ?, ?, ?, ?, TRUE)",
            [new_id, name, category_name, price, image_path],
        )
        return int(new_id)

    def update(self, df: pd.DataFrame) -> None:
        """DataFrame의 각 행에 대해 아이템 정보를 UPDATE한다."""
        for _, r in df.iterrows():
            self._con.execute(
                "UPDATE item SET name=?, category_name=?, price=?, "
                "image_path=?, is_new=? WHERE id=?",
                [r["name"], r["category_name"], r["price"],
                 r["image_path"], r["is_new"], r["id"]],
            )

    def delete_by_id(self, item_id: int) -> bool:
        """PK(id)로 아이템 1건을 DELETE한다."""
        self._con.execute("DELETE FROM item WHERE id = ?", [item_id])
        return True
