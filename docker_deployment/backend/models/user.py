import bcrypt
from database.database import Database

class User:
    @staticmethod
    async def create(db: Database, name, username, password):
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        sql = "INSERT INTO users (name, username, password) VALUES (?, ?, ?)"
        user_id = await db.execute_insert(sql, (name, username, hashed_password))
        return user_id

    @staticmethod
    async def find_by_username(db: Database, username):
        sql = "SELECT * FROM users WHERE username = ?"
        return await db.execute_one(sql, (username,))

    @staticmethod
    async def find_by_id(db: Database, user_id):
        sql = "SELECT * FROM users WHERE id = ?"
        return await db.execute_one(sql, (user_id,))