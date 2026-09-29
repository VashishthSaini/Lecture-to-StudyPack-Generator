import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "database.db"))


def get_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(database_path=None):
    """Initialize the database with required tables."""
    global DATABASE_PATH
    if database_path is not None:
        DATABASE_PATH = database_path
    conn = get_connection()
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create lectures table (new schema with user_id)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lectures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Create lecture_chunks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lecture_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lecture_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lecture_id) REFERENCES lectures(id)
        )
    """)

    # Create study_packs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_packs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lecture_id INTEGER NOT NULL,
            summary TEXT,
            notes TEXT,
            questions TEXT,
            mcqs TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lecture_id) REFERENCES lectures(id)
        )
    """)

    # Migration: add user_id column to lectures if it doesn't exist
    cursor.execute("PRAGMA table_info(lectures)")
    columns = [row[1] for row in cursor.fetchall()]
    if "user_id" not in columns:
        # Add user_id column as nullable first
        cursor.execute("ALTER TABLE lectures ADD COLUMN user_id INTEGER")
        # Create a default user for existing lectures
        cursor.execute("""
            INSERT OR IGNORE INTO users (id, username, email, password_hash)
            VALUES (1, 'default_user', 'default@example.com', 'dummy_hash')
        """)
        # Assign existing lectures to default user
        cursor.execute("UPDATE lectures SET user_id = 1 WHERE user_id IS NULL")
        # Now make user_id NOT NULL (SQLite doesn't support ALTER COLUMN, so we recreate)
        # For simplicity, we'll leave it as is - the FK constraint will be enforced on new inserts

    conn.commit()
    conn.close()
    print("Database initialized successfully.")


def create_user(username, email, password):
    """Create a new user with hashed password. Returns user ID."""
    password_hash = generate_password_hash(password)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash)
        )
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def find_user_by_username(username):
    """Find a user by username. Returns user row or None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user


def find_user_by_email(email):
    """Find a user by email. Returns user row or None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user


def verify_password(user, password):
    """Verify a password against user's password_hash."""
    return check_password_hash(user["password_hash"], password)


def create_lecture(user_id, title, content):
    """Insert a new lecture for a specific user. Returns the new lecture ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO lectures (user_id, title, content) VALUES (?, ?, ?)",
        (user_id, title, content)
    )
    lecture_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return lecture_id


def get_lecture_by_id(lecture_id, user_id):
    """Get a lecture by ID, only if it belongs to the user. Returns lecture row or None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM lectures WHERE id = ? AND user_id = ?",
        (lecture_id, user_id)
    )
    lecture = cursor.fetchone()
    conn.close()
    return lecture


def get_lectures_by_user(user_id):
    """Get all lectures belonging to a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM lectures WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    lectures = cursor.fetchall()
    conn.close()
    return lectures


def update_lecture(lecture_id, user_id, title, content):
    """Update a lecture if it belongs to the user. Returns True if updated, False if not found."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE lectures SET title = ?, content = ? WHERE id = ? AND user_id = ?",
        (title, content, lecture_id, user_id)
    )
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def delete_lecture(lecture_id, user_id):
    """Delete a lecture if it belongs to the user. Returns True if deleted, False if not found."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM lectures WHERE id = ? AND user_id = ?",
        (lecture_id, user_id)
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def create_lecture_chunks(lecture_id, chunks):
    """
    Store lecture chunks in the database.

    Args:
        lecture_id: ID of the lecture
        chunks: List of dicts with 'chunk_index' and 'chunk_text'

    Returns:
        Number of chunks created
    """
    if not chunks:
        return 0

    conn = get_connection()
    cursor = conn.cursor()

    # Delete existing chunks for this lecture (in case of re-chunking)
    cursor.execute("DELETE FROM lecture_chunks WHERE lecture_id = ?", (lecture_id,))

    for chunk in chunks:
        cursor.execute(
            "INSERT INTO lecture_chunks (lecture_id, chunk_index, chunk_text) VALUES (?, ?, ?)",
            (lecture_id, chunk["chunk_index"], chunk["chunk_text"])
        )

    conn.commit()
    conn.close()
    return len(chunks)


def get_lecture_chunks(lecture_id, user_id):
    """
    Get all chunks for a lecture, only if the lecture belongs to the user.

    Args:
        lecture_id: ID of the lecture
        user_id: ID of the user (for ownership verification)

    Returns:
        List of chunk dicts or None if lecture not found/owned
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Verify lecture ownership
    cursor.execute(
        "SELECT id FROM lectures WHERE id = ? AND user_id = ?",
        (lecture_id, user_id)
    )
    lecture = cursor.fetchone()

    if not lecture:
        conn.close()
        return None

    cursor.execute(
        "SELECT chunk_index, chunk_text FROM lecture_chunks WHERE lecture_id = ? ORDER BY chunk_index",
        (lecture_id,)
    )
    chunks = [{"chunk_index": row["chunk_index"], "chunk_text": row["chunk_text"]} for row in cursor.fetchall()]

    conn.close()
    return chunks


def search_lecture_chunks(user_id, query, top_k=5):
    """
    Search for relevant chunks across all of a user's lectures.

    Args:
        user_id: ID of the user
        query: Search query string
        top_k: Maximum number of chunks to return

    Returns:
        List of chunk dicts with lecture info and score
    """
    from services.rag_service import search_chunks

    conn = get_connection()
    cursor = conn.cursor()

    # Get all lectures for this user with their chunks
    cursor.execute("""
        SELECT l.id as lecture_id, l.title, lc.chunk_index, lc.chunk_text
        FROM lectures l
        JOIN lecture_chunks lc ON l.id = lc.lecture_id
        WHERE l.user_id = ?
        ORDER BY l.id, lc.chunk_index
    """, (user_id,))

    all_chunks = []
    for row in cursor.fetchall():
        all_chunks.append({
            "lecture_id": row["lecture_id"],
            "lecture_title": row["title"],
            "chunk_index": row["chunk_index"],
            "chunk_text": row["chunk_text"]
        })

    conn.close()

    if not all_chunks:
        return []

    # Use the search function from rag_service
    results = search_chunks(query, all_chunks, top_k)

    return results


def create_study_pack(lecture_id, task_type, content):
    """
    Save or update a study pack for a lecture.

    Args:
        lecture_id: ID of the lecture
        task_type: One of "summary", "notes", "questions", "mcqs"
        content: Generated study material content

    Returns:
        study_pack_id if successful, None otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Check if study pack exists for this lecture
    cursor.execute("SELECT id FROM study_packs WHERE lecture_id = ?", (lecture_id,))
    existing = cursor.fetchone()

    if existing:
        # Update the specific task field
        cursor.execute(
            f"UPDATE study_packs SET {task_type} = ?, created_at = CURRENT_TIMESTAMP WHERE lecture_id = ?",
            (content, lecture_id)
        )
        study_pack_id = existing["id"]
    else:
        # Create new study pack with the task content
        cursor.execute(
            f"INSERT INTO study_packs (lecture_id, {task_type}) VALUES (?, ?)",
            (lecture_id, content)
        )
        study_pack_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return study_pack_id


def get_study_pack(lecture_id):
    """Get the study pack for a lecture."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM study_packs WHERE lecture_id = ?", (lecture_id,))
    study_pack = cursor.fetchone()
    conn.close()
    return study_pack


def get_lectures_without_chunks(user_id):
    """
    Get all lectures for a user that have zero chunks.
    
    Args:
        user_id: ID of the user
        
    Returns:
        List of lecture dicts (id, title, content) that have zero chunks
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.id, l.title, l.content
        FROM lectures l
        LEFT JOIN lecture_chunks lc ON l.id = lc.lecture_id
        WHERE l.user_id = ? AND lc.id IS NULL
        ORDER BY l.created_at DESC
    """, (user_id,))
    lectures = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return lectures


def rebuild_missing_chunks(user_id):
    """
    Rebuild missing RAG chunks for all lectures belonging to a user.
    
    For each lecture that has zero chunks, this function will:
    1. Chunk the lecture content using the existing chunk_text logic
    2. Store the chunks in the lecture_chunks table
    
    Lectures that already have chunks are skipped (no duplicates created).
    
    Args:
        user_id: ID of the user whose lectures to process
        
    Returns:
        Dict with results: {
            "total_lectures_checked": int,
            "lectures_with_existing_chunks": int,
            "lectures_rebuilt": int,
            "total_chunks_created": int,
            "errors": list of error messages
        }
    """
    from services.rag_service import chunk_lecture
    
    lectures_without_chunks = get_lectures_without_chunks(user_id)
    
    if not lectures_without_chunks:
        return {
            "total_lectures_checked": 0,
            "lectures_with_existing_chunks": 0,
            "lectures_rebuilt": 0,
            "total_chunks_created": 0,
            "errors": []
        }
    
    # Get total lectures for this user to report lectures with existing chunks
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM lectures WHERE user_id = ?",
        (user_id,)
    )
    total_lectures = cursor.fetchone()[0]
    conn.close()
    
    lectures_with_chunks = total_lectures - len(lectures_without_chunks)
    
    results = {
        "total_lectures_checked": total_lectures,
        "lectures_with_existing_chunks": lectures_with_chunks,
        "lectures_rebuilt": 0,
        "total_chunks_created": 0,
        "errors": []
    }
    
    for lecture in lectures_without_chunks:
        try:
            lecture_id = lecture["id"]
            content = lecture["content"]
            
            if not content or not content.strip():
                results["errors"].append(f"Lecture {lecture_id} has empty content")
                continue
            
            # Chunk the lecture content
            chunks = chunk_lecture(lecture["id"], content)
            
            if chunks:
                created = create_lecture_chunks(lecture_id, chunks)
                results["lectures_rebuilt"] += 1
                results["total_chunks_created"] += len(chunks)
            else:
                results["errors"].append(f"Lecture {lecture_id} produced no chunks")
                
        except Exception as e:
            results["errors"].append(f"Lecture {lecture['id']}: {str(e)}")
    
    return results


if __name__ == "__main__":
    init_db()