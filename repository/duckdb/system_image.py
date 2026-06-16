"""repository/duckdb/system_image.py"""
import pandas as pd
from typing import Optional
from ..interfaces import ISystemImageRepository

class DuckDBSystemImageRepository(ISystemImageRepository):
    def find_by_key(self, key: str) -> Optional[dict]:
        row = self._con.execute(
            "SELECT key, image_path, description FROM system_image WHERE key = ?", [key]
        ).fetchone()
        if row is None:
            return None
        return {"key": row[0], "image_path": row[1], "description": row[2]}
    def find_all(self) -> pd.DataFrame:
        return self._con.execute("SELECT * FROM system_image").fetchdf()
