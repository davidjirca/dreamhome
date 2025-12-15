from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    print("Starting up...")
    # Initialize database tables (for development only)
    # In production, use Alembic migrations
    if settings.ENVIRONMENT == "development":
        await init_db()
    print("Database initialized")

    yield

    # Shutdown
    print("Shutting down...")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    version="0.1.3",
    description="""
    # RealEstate Platform API

    A comprehensive real estate platform for the Romanian market.

    ## Features

    * **Authentication**: Register, login, refresh tokens
    * **User Management**: Profile management, role-based access
    * **Property Listings**: Create, search, and manage listings (coming soon)
    * **Map Search**: Interactive map-based property search (coming soon)
    * **Favorites & Alerts**: Save searches and get notifications (coming soon)

    ## User Roles

    * **Buyer**: Can search and save properties
    * **Owner**: Can list properties
    * **Agent**: Can manage multiple listings
    * **Admin**: Full platform access
    """
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to RealEstate Platform API",
        "version": "0.1.3",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }