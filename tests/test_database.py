import os
import sqlite3
import pytest
from src.database.db_manager import get_db_connection, init_db
from src.config import SQLITE_DB_PATH

def test_db_initialization():
    """
    Verifies that the database and its structures are correctly initialized.
    """
    # Ensure tables initialized
    init_db()
    
    # Confirm DB file path is created
    assert os.path.exists(SQLITE_DB_PATH)
    
    # Test connection and schema structure
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query details of created tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    assert "users" in tables
    assert "quiz_history" in tables
    conn.close()
