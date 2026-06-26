import sqlite3
import logging
import bcrypt
import secrets
import json
from src.config import SQLITE_DB_PATH

logger = logging.getLogger(__name__)

def get_db_connection():
    """
    Establishes and returns a connection to the SQLite database.
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except Exception as e:
        logger.error(f"SQLite connection failed: {e}", exc_info=True)
        raise RuntimeError(f"Database connection error: {e}")

def init_db():
    """
    Initializes database tables if they do not exist.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                security_question TEXT NOT NULL,
                security_answer_hash TEXT NOT NULL,
                remember_token TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Create uploaded_documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # 3. Create chat_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_user INTEGER NOT NULL, -- 1 for User, 0 for Assistant
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # 4. Create quiz_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                document_name TEXT NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # 5. Create notes_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 6. Create user_gamification table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_gamification (
                user_id INTEGER PRIMARY KEY,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                current_streak INTEGER DEFAULT 0,
                last_active_date TEXT DEFAULT '',
                badges TEXT DEFAULT '[]',
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 7. Create user_study_planner table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_study_planner (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                exam_date TEXT NOT NULL,
                daily_hours REAL NOT NULL,
                difficulty TEXT NOT NULL,
                goals TEXT,
                plan_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 8. Create exam_records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exam_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                document_name TEXT NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                time_taken_seconds INTEGER NOT NULL,
                taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 9. Create flashcards table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                document_name TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                learned INTEGER DEFAULT 0, -- 1 for learned, 0 for active
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("SQLite database tables initialized successfully.")
    except Exception as e:
        logger.error(f"SQLite initialization failed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to initialize database: {e}")

# ==========================================
# USER & AUTHENTICATION METHODS
# ==========================================

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password: str, hashed: str) -> bool:
    """Verifies a password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def register_user(username: str, password: str, security_question: str, security_answer: str) -> bool:
    """
    Registers a new user with hashed credentials.
    """
    if not username.strip() or not password.strip() or not security_answer.strip():
        return False
    
    hashed_pwd = hash_password(password)
    # Store security answers in lowercase to avoid casing mismatch during recovery
    hashed_ans = hash_password(security_answer.strip().lower())
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, password_hash, security_question, security_answer_hash)
            VALUES (?, ?, ?, ?)
        """, (username.strip(), hashed_pwd, security_question.strip(), hashed_ans))
        user_id = cursor.lastrowid
        
        # Initialize gamification for new user
        cursor.execute("""
            INSERT INTO user_gamification (user_id, xp, level, current_streak, last_active_date, badges)
            VALUES (?, 0, 1, 0, '', '[]')
        """, (user_id,))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"Registration failed: username '{username}' already exists.")
        return False
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        return False

def authenticate_user(username: str, password: str) -> dict:
    """
    Authenticates user, returns user dict if successful, else None.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username.strip(),))
        row = cursor.fetchone()
        conn.close()
        
        if row and check_password(password, row['password_hash']):
            return {"id": row['id'], "username": row['username']}
        return None
    except Exception as e:
        logger.error(f"Auth error: {e}", exc_info=True)
        return None

def get_user_by_id(user_id: int) -> dict:
    """
    Retrieves user record by ID.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, security_question FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"id": row['id'], "username": row['username'], "security_question": row['security_question']}
        return None
    except Exception as e:
        logger.error(f"Get user by id failed: {e}", exc_info=True)
        return None

def get_user_by_username(username: str) -> dict:
    """
    Retrieves user record by username (useful for password recovery lookup).
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, security_question, security_answer_hash FROM users WHERE username = ?", (username.strip(),))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "id": row['id'], 
                "username": row['username'], 
                "security_question": row['security_question'],
                "security_answer_hash": row['security_answer_hash']
            }
        return None
    except Exception as e:
        logger.error(f"Get user by username failed: {e}", exc_info=True)
        return None

def reset_password(user_id: int, new_password: str) -> bool:
    """
    Resets the password for a user.
    """
    if not new_password.strip():
        return False
    hashed_pwd = hash_password(new_password)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_pwd, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Reset password failed: {e}", exc_info=True)
        return False

def update_remember_token(user_id: int, generate: bool = True) -> str:
    """
    Generates or clears a remember token for a user.
    """
    token = secrets.token_hex(32) if generate else None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET remember_token = ? WHERE id = ?", (token, user_id))
        conn.commit()
        conn.close()
        return token
    except Exception as e:
        logger.error(f"Update remember token failed: {e}", exc_info=True)
        return None

def get_user_by_token(token: str) -> dict:
    """
    Validates a remember token and returns the user dict if valid.
    """
    if not token:
        return None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM users WHERE remember_token = ?", (token,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"id": row['id'], "username": row['username']}
        return None
    except Exception as e:
        logger.error(f"Get user by token failed: {e}", exc_info=True)
        return None


# ==========================================
# GAMIFICATION METHODS
# ==========================================

def get_gamification(user_id: int) -> dict:
    """
    Retrieves the user's gamification stats, initializing them if they do not exist.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_gamification WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("""
                INSERT OR IGNORE INTO user_gamification (user_id, xp, level, current_streak, last_active_date, badges)
                VALUES (?, 0, 1, 0, '', '[]')
            """, (user_id,))
            conn.commit()
            cursor.execute("SELECT * FROM user_gamification WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
        conn.close()
        return dict(row)
    except Exception as e:
        logger.error(f"Get gamification failed: {e}", exc_info=True)
        return {"user_id": user_id, "xp": 0, "level": 1, "current_streak": 0, "last_active_date": "", "badges": "[]"}

def update_gamification(user_id: int, xp: int, level: int, streak: int, last_active: str, badges_json: str) -> bool:
    """
    Updates the user's gamification records.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO user_gamification (user_id, xp, level, current_streak, last_active_date, badges)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, xp, level, streak, last_active, badges_json))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Update gamification failed: {e}", exc_info=True)
        return False


# ==========================================
# UPLOADED DOCUMENTS METHODS
# ==========================================

def add_uploaded_document(user_id: int, file_name: str, file_path: str, file_size: int) -> bool:
    """Logs an uploaded document in SQLite."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO uploaded_documents (user_id, file_name, file_path, file_size)
            VALUES (?, ?, ?, ?)
        """, (user_id, file_name, file_path, file_size))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to add document log: {e}", exc_info=True)
        return False

def get_user_documents(user_id: int) -> list:
    """Retrieves all uploaded documents for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, file_name, file_path, file_size, upload_time 
            FROM uploaded_documents 
            WHERE user_id = ? 
            ORDER BY upload_time DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Get user documents failed: {e}", exc_info=True)
        return []

def delete_uploaded_document(user_id: int, doc_id: int) -> dict:
    """Deletes a document log and returns its details (for deleting physical file)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT file_path, file_name FROM uploaded_documents WHERE id = ? AND user_id = ?", (doc_id, user_id))
        row = cursor.fetchone()
        if row:
            doc_data = dict(row)
            cursor.execute("DELETE FROM uploaded_documents WHERE id = ? AND user_id = ?", (doc_id, user_id))
            conn.commit()
            conn.close()
            return doc_data
        conn.close()
        return None
    except Exception as e:
        logger.error(f"Delete uploaded document failed: {e}", exc_info=True)
        return None


# ==========================================
# CHAT HISTORY METHODS
# ==========================================

def save_chat_message(user_id: int, message: str, is_user: bool) -> bool:
    """Saves a chat log in the history."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_history (user_id, message, is_user)
            VALUES (?, ?, ?)
        """, (user_id, message, 1 if is_user else 0))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Save chat message failed: {e}", exc_info=True)
        return False

def get_chat_history(user_id: int) -> list:
    """Retrieves chat logs for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT message, is_user, timestamp 
            FROM chat_history 
            WHERE user_id = ? 
            ORDER BY timestamp ASC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Get chat history failed: {e}", exc_info=True)
        return []

def clear_chat_history(user_id: int) -> bool:
    """Clears all chat history logs for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Clear chat history failed: {e}", exc_info=True)
        return False


# ==========================================
# QUIZ HISTORY METHODS
# ==========================================

def save_quiz_record(user_id: int, document_name: str, score: int, total_questions: int) -> bool:
    """Saves a quiz score record."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO quiz_history (user_id, document_name, score, total_questions)
            VALUES (?, ?, ?, ?)
        """, (user_id, document_name, score, total_questions))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Save quiz record failed: {e}", exc_info=True)
        return False

def get_user_quiz_history(user_id: int) -> list:
    """Retrieves quiz history records for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, document_name, score, total_questions, taken_at 
            FROM quiz_history 
            WHERE user_id = ? 
            ORDER BY taken_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Get user quiz history failed: {e}", exc_info=True)
        return []


# ==========================================
# STUDY NOTES HISTORY METHODS
# ==========================================

def save_note(user_id: int, title: str, content: str) -> bool:
    """Saves generated notes to SQLite."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notes_history (user_id, title, content)
            VALUES (?, ?, ?)
        """, (user_id, title.strip(), content))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Save note failed: {e}", exc_info=True)
        return False

def get_user_notes(user_id: int) -> list:
    """Retrieves all saved notes for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, content, generated_at 
            FROM notes_history 
            WHERE user_id = ? 
            ORDER BY generated_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Get user notes failed: {e}", exc_info=True)
        return []

def delete_note(user_id: int, note_id: int) -> bool:
    """Deletes a saved note."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes_history WHERE id = ? AND user_id = ?", (note_id, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Delete note failed: {e}", exc_info=True)
        return False


# ==========================================
# STUDY PLANNER METHODS
# ==========================================

def save_study_plan(user_id: int, subject: str, exam_date: str, daily_hours: float, difficulty: str, goals: str, plan_json: str) -> bool:
    """Saves a generated study plan in SQLite."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_study_planner (user_id, subject, exam_date, daily_hours, difficulty, goals, plan_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, subject.strip(), exam_date, daily_hours, difficulty, goals.strip(), plan_json))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Save study plan failed: {e}", exc_info=True)
        return False

def get_study_plans(user_id: int) -> list:
    """Retrieves all study plans for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, subject, exam_date, daily_hours, difficulty, goals, plan_json, created_at
            FROM user_study_planner
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Get study plans failed: {e}", exc_info=True)
        return []

def delete_study_plan(user_id: int, plan_id: int) -> bool:
    """Deletes a study plan."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_study_planner WHERE id = ? AND user_id = ?", (plan_id, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Delete study plan failed: {e}", exc_info=True)
        return False


# ==========================================
# EXAM MODE METHODS
# ==========================================

def save_exam_record(user_id: int, document_name: str, score: int, total_questions: int, time_taken_seconds: int) -> bool:
    """Saves a timed exam mode session score."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO exam_records (user_id, document_name, score, total_questions, time_taken_seconds)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, document_name.strip(), score, total_questions, time_taken_seconds))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Save exam record failed: {e}", exc_info=True)
        return False

def get_exam_records(user_id: int) -> list:
    """Retrieves all exam records for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, document_name, score, total_questions, time_taken_seconds, taken_at
            FROM exam_records
            WHERE user_id = ?
            ORDER BY taken_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Get exam records failed: {e}", exc_info=True)
        return []


# ==========================================
# FLASHCARD METHODS
# ==========================================

def add_flashcard(user_id: int, document_name: str, question: str, answer: str) -> bool:
    """Adds a single generated flashcard."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO flashcards (user_id, document_name, question, answer, learned)
            VALUES (?, ?, ?, ?, 0)
        """, (user_id, document_name.strip(), question.strip(), answer.strip()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Add flashcard failed: {e}", exc_info=True)
        return False

def get_flashcards(user_id: int, document_name: str) -> list:
    """Retrieves flashcards for a specific document."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, question, answer, learned, created_at
            FROM flashcards
            WHERE user_id = ? AND document_name = ?
            ORDER BY id ASC
        """, (user_id, document_name.strip()))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Get flashcards failed: {e}", exc_info=True)
        return []

def mark_flashcard_learned(user_id: int, card_id: int, learned_status: int) -> bool:
    """Toggles the learned status of a card (1 for learned, 0 for active)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE flashcards
            SET learned = ?
            WHERE id = ? AND user_id = ?
        """, (learned_status, card_id, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Mark flashcard learned failed: {e}", exc_info=True)
        return False

def delete_all_flashcards(user_id: int, document_name: str) -> bool:
    """Clears all flashcards associated with a document (useful for re-generating)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM flashcards
            WHERE user_id = ? AND document_name = ?
        """, (user_id, document_name.strip()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Delete all flashcards failed: {e}", exc_info=True)
        return False
