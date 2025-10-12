import hashlib
import secrets
from datetime import datetime, timedelta
from database.database import Database

class Session:
    @staticmethod
    async def create(db: Database, user_id):
        token = secrets.token_hex(16)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.utcnow() + timedelta(days=7)
        sql = "INSERT INTO user_sessions (user_id, token_hash, expires_at) VALUES (?, ?, ?)"
        await db.execute_insert(sql, (user_id, token_hash, expires_at.isoformat()))
        return token

    @staticmethod
    async def find_by_token(db: Database, token):
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        sql = "SELECT * FROM user_sessions WHERE token_hash = ? AND is_active = 1 AND expires_at > ?"
        return await db.execute_one(sql, (token_hash, datetime.utcnow().isoformat()))

    @staticmethod
    async def cleanup_expired(db: Database):
        """Remove expired sessions and return count of cleaned sessions"""
        current_time = datetime.utcnow().isoformat()
        # Deactivate expired sessions
        cleanup_sql = "UPDATE user_sessions SET is_active = 0 WHERE expires_at < ? AND is_active = 1"
        expired_count = await db.execute_update(cleanup_sql, (current_time,))
        
        return expired_count