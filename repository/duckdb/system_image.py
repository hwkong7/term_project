"""
repository/duckdb/system_image.py
시스템 이미지 경로 DuckDB 구현체.

ISystemImageRepository 인터페이스를 구현한다.
system_image 테이블은 파산/우승 다이얼로그에 표시되는 이미지 파일 경로를 저장한다.

[사용 예]
  find_by_key('BANKRUPT') → {'key': 'BANKRUPT', 'image_path': 'assets/bankrupt.png', ...}
  find_by_key('WINNER')   → {'key': 'WINNER',   'image_path': 'assets/winner.png',   ...}

이미지 파일이 실제로 존재하지 않으면 views/dialogs.py에서 이모지로 폴백한다.
"""

import pandas as pd
from typing import Optional
from ..interfaces import ISystemImageRepository


class DuckDBSystemImageRepository(ISystemImageRepository):
    """system_image 테이블 DuckDB 구현체 (읽기 전용)."""

    def find_by_key(self, key: str) -> Optional[dict]:
        """
        key('WINNER', 'BANKRUPT' 등)로 이미지 경로 단건을 조회한다.
        없으면 None, 있으면 {'key': ..., 'image_path': ..., 'description': ...}를 반환한다.
        """
        row = self._con.execute(
            "SELECT key, image_path, description FROM system_image WHERE key = ?",
            [key]
        ).fetchone()
        if row is None:
            return None
        return {"key": row[0], "image_path": row[1], "description": row[2]}

    def find_all(self) -> pd.DataFrame:
        """전체 시스템 이미지 목록을 DataFrame으로 반환한다."""
        return self._con.execute("SELECT * FROM system_image").fetchdf()
