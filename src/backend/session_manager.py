"""
SessionManager - SQLite-backed session management with TTL expiry

Mathematical Properties Implemented:
- UUID Uniqueness: ∀ sessions s1,s2: s1.id ≠ s2.id
- TTL Monotonicity: session.created_at ≤ session.expires_at  
- Data Persistence: get(create(data)) = data
- Session Isolation: update(s1) ∄ affects(s2)
- Thread Safety: Concurrent operations maintain consistency

Implementation follows TDD Green phase - minimal but correct functionality.
"""

import sqlite3
import json
import uuid
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union


class SessionManager:
    """
    SQLite-backed session management with TTL expiry and thread safety.
    
    Core Operations:
    - create_session(data) → session_id
    - get_session(session_id) → session_data | None
    - update_session(session_id, data) → bool
    - cleanup_expired_sessions() → int
    """
    
    def __init__(self, db_path: str = ":memory:", default_ttl: int = 3600):
        """
        Initialize SessionManager with SQLite database.
        
        Args:
            db_path: SQLite database path (:memory: for in-memory)
            default_ttl: Default session TTL in seconds (1 hour default)
        """
        self.db_path = db_path
        self.default_ttl = default_ttl
        self._lock = threading.Lock()  # Thread safety
        
        # For in-memory database, we need to keep a persistent connection
        if db_path == ":memory:":
            self._persistent_conn = sqlite3.Connection(db_path, timeout=30.0, check_same_thread=False)
            self._persistent_conn.row_factory = sqlite3.Row
        else:
            self._persistent_conn = None
        
        # Initialize database schema
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database schema with sessions table."""
        # Use lock to ensure thread-safe initialization
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            ''')
            # Index for efficient expiry cleanup
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_expires_at 
                ON sessions(expires_at)
            ''')
            conn.commit()
            
            # Only close if it's not persistent connection
            if self._persistent_conn is None:
                conn.close()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get SQLite database connection."""
        if self._persistent_conn is not None:
            # Use persistent connection for in-memory database
            return self._persistent_conn
        else:
            # Create new connection for file-based database
            conn = sqlite3.Connection(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row  # Dict-like access
            return conn
    
    def create_session(self, data: Dict[str, Any]) -> str:
        """
        Create new session with unique UUID and TTL expiry.
        
        Mathematical Property: create: SessionData → UUID × State
        
        Args:
            data: Session data dictionary (must not be None)
            
        Returns:
            session_id: Unique UUID string
            
        Raises:
            TypeError: If data is None
            ValueError: If data cannot be serialized
        """
        if data is None:
            raise TypeError("Session data cannot be None")
        
        # Generate unique UUID
        session_id = str(uuid.uuid4())
        
        # Calculate timestamps
        now = time.time()
        expires_at = now + self.default_ttl
        
        # Serialize data to JSON
        try:
            json_data = json.dumps(data, default=str)  # Handle datetime objects
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot serialize session data: {e}")
        
        # Thread-safe database insertion
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sessions (session_id, data, created_at, expires_at)
                VALUES (?, ?, ?, ?)
            ''', (session_id, json_data, now, expires_at))
            conn.commit()
            
            # Only close if it's not persistent connection
            if self._persistent_conn is None:
                conn.close()
        
        return session_id
    
    def get_session(self, session_id: str, flat_format: bool = False) -> Optional[Dict[str, Any]]:
        """
        Retrieve session by ID if not expired.
        
        Mathematical Property: get: UUID → SessionData ∪ {None}
        
        Args:
            session_id: Session UUID string
            flat_format: If True, return session data directly; if False, return structured format
            
        Returns:
            Session data dict with metadata or None if not found/expired
            
        Raises:
            TypeError: If session_id is None
        """
        if session_id is None:
            raise TypeError("session_id cannot be None")
        
        if not session_id or not isinstance(session_id, str):
            return None
        
        # Validate UUID format
        try:
            uuid.UUID(session_id)
        except (ValueError, TypeError):
            return None
        
        now = time.time()
        
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT session_id, data, created_at, expires_at
                FROM sessions 
                WHERE session_id = ? AND expires_at > ?
            ''', (session_id, now))
            
            row = cursor.fetchone()
            
            # Only close if it's not persistent connection
            if self._persistent_conn is None:
                conn.close()
            
            if row is None:
                return None
            
            # Deserialize JSON data
            try:
                session_data = json.loads(row['data'])
            except (json.JSONDecodeError, TypeError):
                return None
            
            # Return session with metadata or flat format
            if flat_format:
                # Return session data directly for test compatibility
                return session_data
            else:
                # Return structured format with metadata
                return {
                    'session_id': row['session_id'],
                    'data': session_data,
                    'created_at': datetime.fromtimestamp(row['created_at']).isoformat(),
                    'expires_at': datetime.fromtimestamp(row['expires_at']).isoformat()
                }
    
    def update_session(self, session_id_or_data: Union[str, Dict[str, Any]], data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update existing session data.
        
        Mathematical Property: update: UUID × SessionData → Bool
        
        Args:
            session_id_or_data: Either session UUID string or session data dict (for EventHandler compatibility)
            data: New session data (optional if first arg is dict)
            
        Returns:
            True if updated successfully, False if session not found
            
        Raises:
            TypeError: If session_id or data is None
        """
        # Handle dual interface for compatibility
        if isinstance(session_id_or_data, dict) and data is None:
            # EventHandler calls update_session(data) without session_id
            # This is a simplified interface for single-session contexts
            raise ValueError("Single-argument session update not implemented - need session_id")
        
        # Normal interface: update_session(session_id, data)
        session_id = session_id_or_data
        
        if session_id is None:
            raise TypeError("session_id cannot be None")
        
        if not session_id or not isinstance(session_id, str):
            return False
        
        if data is None:
            raise TypeError("Session data cannot be None")
        
        # Validate UUID format
        try:
            uuid.UUID(session_id)
        except (ValueError, TypeError):
            return False
        
        # Serialize new data
        try:
            json_data = json.dumps(data, default=str)
        except (TypeError, ValueError):
            raise ValueError(f"Cannot serialize session data")
        
        now = time.time()
        
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE sessions 
                SET data = ? 
                WHERE session_id = ? AND expires_at > ?
            ''', (json_data, session_id, now))
            
            conn.commit()
            rowcount = cursor.rowcount
            
            # Only close if it's not persistent connection
            if self._persistent_conn is None:
                conn.close()
            
            return rowcount > 0
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions from database.
        
        Performance Property: Efficient batch cleanup
        
        Returns:
            Number of sessions removed
        """
        now = time.time()
        
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM sessions WHERE expires_at <= ?', (now,))
            conn.commit()
            rowcount = cursor.rowcount
            
            # Only close if it's not persistent connection
            if self._persistent_conn is None:
                conn.close()
            
            return rowcount
    
    def extend_ttl(self, session_id: str, extension_seconds: int) -> bool:
        """
        Extend TTL for active session.
        
        Mathematical Property: extend_ttl: UUID × Seconds → Bool
        Time Invariant: new_expires_at > old_expires_at
        
        Args:
            session_id: Session UUID string
            extension_seconds: Additional seconds to add to TTL
            
        Returns:
            True if extended successfully, False if session not found
        """
        if not session_id or not isinstance(session_id, str):
            return False
        
        if extension_seconds <= 0:
            return False
        
        try:
            uuid.UUID(session_id)
        except (ValueError, TypeError):
            return False
        
        now = time.time()
        
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            # Get current expiry time for active session
            cursor.execute('''
                SELECT expires_at FROM sessions 
                WHERE session_id = ? AND expires_at > ?
            ''', (session_id, now))
            
            row = cursor.fetchone()
            if row is None:
                # Only close if it's not persistent connection
                if self._persistent_conn is None:
                    conn.close()
                return False
            
            # Calculate new expiry time
            new_expires_at = row['expires_at'] + extension_seconds
            
            # Update expiry time
            cursor.execute('''
                UPDATE sessions 
                SET expires_at = ? 
                WHERE session_id = ?
            ''', (new_expires_at, session_id))
            
            conn.commit()
            rowcount = cursor.rowcount
            
            # Only close if it's not persistent connection
            if self._persistent_conn is None:
                conn.close()
            
            return rowcount > 0
    
    def validate_session(self, session_id: str) -> bool:
        """
        Validate that session exists and is not expired.
        
        Args:
            session_id: Session UUID string
            
        Returns:
            True if session is valid, False otherwise
        """
        session = self.get_session(session_id)
        return session is not None