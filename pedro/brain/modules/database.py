# Internal
from typing import Any, Dict, List

# External
from tinydb import TinyDB, Query

class Database:
    def __init__(self, db_path: str = "pedro_database.json"):
        self.db_path = db_path
        self.db = TinyDB(db_path)
        self.query = Query()
    
    def insert(self, table_name: str, data: Dict[str, Any]) -> int:
        table = self.db.table(table_name)
        return table.insert(data)
    
    def get_all(self, table_name: str) -> List[Dict[str, Any]]:
        table = self.db.table(table_name)
        return table.all()
    
    def search(self, table_name: str, condition: Dict[str, Any]) -> List[Dict[str, Any]]:
        table = self.db.table(table_name)
        query = self.query

        query_obj = None
        for key, value in condition.items():
            if query_obj is None:
                query_obj = (query[key] == value)
            else:
                query_obj &= (query[key] == value)
        
        return table.search(query_obj) if query_obj else []
    
    def update(self, table_name: str, data: Dict[str, Any], condition: Dict[str, Any]) -> List[int]:
        table = self.db.table(table_name)
        query = self.query

        query_obj = None
        for key, value in condition.items():
            if query_obj is None:
                query_obj = (query[key] == value)
            else:
                query_obj &= (query[key] == value)
        
        return table.update(data, query_obj) if query_obj else []
    
    def remove(self, table_name: str, condition: Dict[str, Any]) -> List[int]:
        table = self.db.table(table_name)
        query = self.query
        
        # Build query dynamically based on condition
        query_obj = None
        for key, value in condition.items():
            if query_obj is None:
                query_obj = (query[key] == value)
            else:
                query_obj &= (query[key] == value)
        
        return table.remove(query_obj) if query_obj else []
    
    def close(self) -> None:
        self.db.close()
