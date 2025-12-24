import sqlite3
import json
from abc import ABC, abstractmethod
from dataclasses import asdict
from typing import List
from DataTypes import Faculty


# --- Storage Interface (SoC) ---
class BaseStorage(ABC):
    @abstractmethod
    def save_faculty(self, faculty_list: List[Faculty]): pass
    
    @abstractmethod
    def search_cache(self, keyword: str) -> List[Faculty]: pass

# --- SQLite Implementation ---
class SQLiteStorage(BaseStorage):
    def __init__(self, db_path="db/faculty_cache.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS faculty (
                id TEXT PRIMARY KEY,
                name TEXT,
                h_index INTEGER,
                institution TEXT,
                data_json TEXT
            )
        """)
        # FTS5 for keyword-based retrieval without API
        try:
            self.conn.execute("""
                CREATE VIRTUAL TABLE faculty_search 
                USING fts5(id UNINDEXED, name, specialty, paper, content=faculty, content_rowid=id)
            """)
        except sqlite3.OperationalError:
            pass 

    def save_faculty(self, faculty_list: List[Faculty]):
        for f in faculty_list:
            self.conn.execute(
                "INSERT OR REPLACE INTO faculty (id, name, h_index, institution, data_json) VALUES (?, ?, ?, ?, ?)",
                (f.id, f.name, f.h_index, f.last_known_institution, json.dumps(asdict(f)))
            )
            self.conn.execute(
                "INSERT OR REPLACE INTO faculty_search (rowid, name, specialty, paper) VALUES ((SELECT rowid FROM faculty WHERE id=?), ?, ?, ?)",
                (f.id, f.name, f.specialty, f.top_paper)
            )
        self.conn.commit()

    def search_cache(self, keyword: str) -> List[Faculty]:
        cursor = self.conn.execute("""
            SELECT f.data_json FROM faculty f
            JOIN faculty_search fs ON f.id = fs.rowid
            WHERE faculty_search MATCH ?
        """, (keyword,))
        return [Faculty(**json.loads(row[0])) for row in cursor.fetchall()]
