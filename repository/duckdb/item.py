"""repository/duckdb/item.py"""
import pandas as pd
from typing import Optional
from ..interfaces import IItemRepository

class DuckDBItemRepository(IItemRepository):
    def create_table(self) -> None:
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS item (
                id            INTEGER   PRIMARY KEY,
                name          VARCHAR   NOT NULL UNIQUE,
                category_name VARCHAR   NOT NULL,
                price         INTEGER   NOT NULL CHECK (price >= 0),
                image_path    VARCHAR,
                is_new        BOOLEAN   NOT NULL DEFAULT FALSE,
                FOREIGN KEY (category_name) REFERENCES category (name)
            )
        """)
    def count(self) -> int:
        return self._con.execute("SELECT COUNT(*) FROM item").fetchone()[0]
    def save(self, df: pd.DataFrame) -> None:
        self._con.execute(
            "INSERT INTO item (id, name, category_name, price, image_path, is_new) "
            "SELECT id, name, category_name, price, image_path, is_new FROM df"
        )
    def find_by_id(self, item_id: int) -> Optional[dict]:
        row = self._con.execute(
            "SELECT id, name, category_name, price, image_path, is_new FROM item WHERE id = ?",
            [item_id],
        ).fetchone()
        if row is None:
            return None
        return {"id": row[0], "name": row[1], "category_name": row[2],
                "price": row[3], "image_path": row[4], "is_new": row[5]}
    def find_all(self) -> pd.DataFrame:
        return self._con.execute("""
            SELECT i.id, i.name, c.name AS category, i.price, i.image_path, i.is_new
            FROM item i INNER JOIN category c ON i.category_name = c.name ORDER BY i.id
        """).fetchdf()
    def find_by_category(self, category_name: str) -> pd.DataFrame:
        return self._con.execute("""
            SELECT i.id, i.name, c.name AS category, i.price, i.image_path, i.is_new
            FROM item i INNER JOIN category c ON i.category_name = c.name
            WHERE i.category_name = ? ORDER BY i.id
        """, [category_name]).fetchdf()
    def find_new_items(self) -> pd.DataFrame:
        return self._con.execute("""
            SELECT i.id, i.name, c.name AS category, i.price, i.image_path, i.is_new
            FROM item i INNER JOIN category c ON i.category_name = c.name
            WHERE i.is_new = TRUE ORDER BY i.id
        """).fetchdf()
    def save_one(self, name: str, category_name: str, price: int, image_path) -> int:
        new_id = self._con.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM item").fetchone()[0]
        self._con.execute(
            "INSERT INTO item (id, name, category_name, price, image_path, is_new) VALUES (?, ?, ?, ?, ?, TRUE)",
            [new_id, name, category_name, price, image_path],
        )
        return int(new_id)
    def update(self, df: pd.DataFrame) -> None:
        for _, r in df.iterrows():
            self._con.execute(
                "UPDATE item SET name=?, category_name=?, price=?, image_path=?, is_new=? WHERE id=?",
                [r["name"], r["category_name"], r["price"], r["image_path"], r["is_new"], r["id"]],
            )
    def delete_by_id(self, item_id: int) -> bool:
        self._con.execute("DELETE FROM item WHERE id = ?", [item_id])
        return True
