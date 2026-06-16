"""repository/duckdb/category.py"""
import pandas as pd
from ..interfaces import ICategoryRepository

class DuckDBCategoryRepository(ICategoryRepository):
    def create_table(self) -> None:
        self._con.execute("CREATE TABLE IF NOT EXISTS category (name VARCHAR PRIMARY KEY)")
    def count(self) -> int:
        return self._con.execute("SELECT COUNT(*) FROM category").fetchone()[0]
    def save(self, df: pd.DataFrame) -> None:
        self._con.execute("INSERT INTO category (name) SELECT name FROM df")
    def find_all(self) -> pd.DataFrame:
        return self._con.execute("SELECT * FROM category").fetchdf()
    def delete_by_name(self, name: str) -> bool:
        self._con.execute("DELETE FROM category WHERE name = ?", [name])
        return True
