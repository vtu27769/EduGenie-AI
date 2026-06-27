import os
import sqlite3
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
    assert "flashcards" in tables
    conn.close()

def test_flashcards_db_operations():
    """
    Tests flashcard-related database operations.
    """
    from src.database.db_manager import (
        add_flashcard, get_flashcards, mark_flashcard_learned, delete_all_flashcards,
        register_user, get_user_by_username
    )
    
    init_db()
    
    username = "test_flashcard_user_unique"
    # Clean up user if already exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    
    # Register user
    register_user(username, "password123", "question", "answer")
    user = get_user_by_username(username)
    user_id = user["id"]
    doc_name = "test_document.pdf"
    
    # Clean up any residual test data first
    delete_all_flashcards(user_id, doc_name)
    
    # 1. Test adding a flashcard
    success = add_flashcard(user_id, doc_name, "What is AI?", "Artificial Intelligence")
    assert success
    
    # 2. Test retrieving flashcards
    cards = get_flashcards(user_id, doc_name)
    assert len(cards) == 1
    card = cards[0]
    assert card["question"] == "What is AI?"
    assert card["answer"] == "Artificial Intelligence"
    assert card["learned"] == 0
    
    # 3. Test marking as learned
    success_mark = mark_flashcard_learned(user_id, card["id"], 1)
    assert success_mark
    
    cards_updated = get_flashcards(user_id, doc_name)
    assert cards_updated[0]["learned"] == 1
    
    # 4. Test deleting flashcards
    success_delete = delete_all_flashcards(user_id, doc_name)
    assert success_delete
    assert len(get_flashcards(user_id, doc_name)) == 0
    
    # Clean up user
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
