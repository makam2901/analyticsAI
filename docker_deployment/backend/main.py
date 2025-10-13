from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uvicorn
import os
from dotenv import load_dotenv

from database.database import Database
from models.user import User
from models.session import Session
from routes import auth, data, code_generation

# Load environment variables
load_dotenv('.env.development' if os.getenv('NODE_ENV') != 'production' else '.env.production')

# Initialize database
db = Database()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.connect()
    await db.initialize()
    
    # Clean up expired sessions
    expired_sessions = await Session.cleanup_expired(db)
    if expired_sessions > 0:
        print(f"🧹 Cleaned up {expired_sessions} expired sessions")
    
    yield
    
    # Shutdown
    await db.close()

# Create FastAPI app
app = FastAPI(
    title="Analytics AI Platform",
    description="AI-powered analytics platform for data insights and visualization",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
origins = [
    "http://localhost:3000",
    "http://localhost:8080", 
    "http://localhost",
    "https://analytics-ai-frontend-i73iz6e3wq-uc.a.run.app",
    os.getenv('FRONTEND_URL', 'http://localhost:3000')
]
# Remove duplicates while preserving order
origins = list(dict.fromkeys(origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        session_data = await Session.find_by_token(db, token)
        
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return session_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(data.router, prefix="/api/data", tags=["Data Management"])
app.include_router(code_generation.router, prefix="/api/code", tags=["Code Generation"])

@app.get("/")
async def root():
    return {
        "message": "Analytics AI Platform API",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0",
        "database": "connected" if db.connection else "disconnected"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        reload=True if os.getenv("NODE_ENV") == "development" else False
    )