"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import get_settings
from database import init_mongodb_indexes, engine, Base

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB tables (works for both PostgreSQL and SQLite) and MongoDB indexes."""
    Base.metadata.create_all(bind=engine)
    print("Database schema ready")
    await init_mongodb_indexes()
    print("MongoDB indexes initialized")
    yield
    print("Application shutting down")


app = FastAPI(
    title=settings.app_name,
    description="Chess Pattern Analyzer - See your chess blind spots clearly",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from api import auth, games, patterns, jobs, analysis, openings

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(games.router, prefix="/api/games", tags=["Games"])
app.include_router(patterns.router, prefix="/api/patterns", tags=["Patterns"])
app.include_router(openings.router, prefix="/api/openings", tags=["Openings"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])


@app.get("/")
async def root():
    return {"message": "Welcome to ChessMirror API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
