from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.core.cache import cache_service  # ADD THIS IMPORT
from app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    print("🚀 Starting up...")
    
    # Initialize database tables (for development only)
    # In production, use Alembic migrations
    if settings.ENVIRONMENT == "development":
        await init_db()
        print("✅ Database initialized")
    
    # Connect to Redis cache
    await cache_service.connect()
    print("✅ Cache service connected")
    
    print("✅ Application ready!")

    yield

    # Shutdown
    print("🛑 Shutting down...")
    
    # Disconnect from Redis
    await cache_service.disconnect()
    print("✅ Cache service disconnected")
    
    print("✅ Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    version="1.0.0",
    description="""
    # dreamhome Platform API

    A comprehensive real estate platform for the Romanian market.

    ## Features

    * **Authentication**: Register, login, refresh tokens
    * **User Management**: Profile management, role-based access
    * **Property Listings**: Create, search, and manage listings
    * **Advanced Search**: Full-text, geospatial, 30+ filters
    * **Map Search**: Interactive map-based property search
    * **Favorites & Alerts**: Save searches and get notifications
    * **Caching**: Redis-powered search performance

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
        "message": "Welcome to dreamhome Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "cache_enabled": settings.CACHE_ENABLED,
        "cache_available": cache_service.is_available()
    }