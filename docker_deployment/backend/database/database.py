import aiosqlite
import os

class Database:
    def __init__(self):
        self.db_path = os.getenv("DATABASE_PATH", "data/analytics_ai.db")
        self.connection = None

    async def connect(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.connection = await aiosqlite.connect(self.db_path)

    async def close(self):
        await self.connection.close()

    async def initialize(self):
        await self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                token_hash TEXT,
                expires_at TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        """)
        await self.connection.commit()

    async def execute_one(self, sql, params=()):
        async with self.connection.execute(sql, params) as cursor:
            return await cursor.fetchone()

    async def execute_all(self, sql, params=()):
        async with self.connection.execute(sql, params) as cursor:
            return await cursor.fetchall()

    async def execute_insert(self, sql, params):
        cursor = await self.connection.execute(sql, params)
        await self.connection.commit()
        return cursor.lastrowid

    async def execute_update(self, sql, params):
        """Execute UPDATE/DELETE queries and return affected rows count"""
        cursor = await self.connection.execute(sql, params)
        await self.connection.commit()
        return cursor.rowcount