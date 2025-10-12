from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import bcrypt
import hashlib
from database.database import Database
from models.user import User
from models.session import Session

router = APIRouter()
security = HTTPBearer()

# Get database instance from main.py
async def get_db():
    from main import db
    if not db.connection:
        await db.connect()
    return db

class UserCreate(BaseModel):
    name: str
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

@router.post("/register")
async def register(user: UserCreate, db: Database = Depends(get_db)):
    existing_user = await User.find_by_username(db, user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    user_id = await User.create(db, user.name, user.username, user.password)
    token = await Session.create(db, user_id)
    return {"token": token}

@router.post("/login")
async def login(user: UserLogin, db: Database = Depends(get_db)):
    db_user = await User.find_by_username(db, user.username)
    if not db_user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    # Check password - db_user[2] is the password field
    stored_password = db_user[2]
    if not bcrypt.checkpw(user.password.encode('utf-8'), stored_password.encode('utf-8')):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    token = await Session.create(db, db_user[0])
    return {"token": token}

@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security), db: Database = Depends(get_db)):
    try:
        token = credentials.credentials
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Deactivate the session
        sql = "UPDATE user_sessions SET is_active = 0 WHERE token_hash = ?"
        await db.execute_update(sql, (token_hash,))
        
        return {"message": "Successfully logged out"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not logout"
        )

@router.get("/verify")
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security), db: Database = Depends(get_db)):
    """Verify if the provided token is valid"""
    try:
        token = credentials.credentials
        session_data = await Session.find_by_token(db, token)
        
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Get user info
        user_data = await User.find_by_id(db, session_data[1])  # session_data[1] is user_id
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return {
            "valid": True,
            "user_id": session_data[1],
            "username": user_data[1],
            "name": user_data[3]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not verify token"
        )