"""
repository/duckdb/category.py
아이템 카테고리 마스터 DuckDB 구현체.

ICategoryRepository 인터페이스를 구현한다.
category 테이블은 아이템이 속하는 분류(광물, 식량)를 저장하는 마스터 테이블이다.
거래소 화면에서 카테고리 탭 목록을 동적으로 구성할 때 사용된다.
"""

import pandas as pd
from ..interfaces import ICategoryRepository


class DuckDBCategoryRepository(ICategoryRepository):
    """category 테이블 DuckDB 구현체."""

    def create_table(self) -> None:
        """category 테이블이 없으면 생성한다."""
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS category (name VARCHAR PRIMARY KEY)"
        )

    def count(self) -> int:
        """category 테이블의 전체 행 수를 반환한다."""
        return self._con.execute("SELECT COUNT(*) FROM category").fetchone()[0]

    def save(self, df: pd.DataFrame) -> None:
        """카테고리 데이터를 INSERT한다."""
        self._con.execute("INSERT INTO category (name) SELECT name FROM df")

    def find_all(self) -> pd.DataFrame:
        """전체 카테고리 목록을 DataFrame으로 반환한다."""
        return self._con.execute("SELECT * FROM category").fetchdf()

    def delete_by_name(self, name: str) -> bool:
        """카테고리명으로 1건을 삭제한다. 성공 여부를 True로 반환한다."""
        self._con.execute("DELETE FROM category WHERE name = ?", [name])
        return True
