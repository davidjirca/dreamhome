from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, properties, favorites, saved_searches, alerts

api_router = APIRouter()

# Include routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(properties.router, prefix="/properties", tags=["Properties"])
api_router.include_router(favorites.router, prefix="/favorites", tags=["Favorites"])
api_router.include_router(saved_searches.router, prefix="/saved-searches", tags=["Saved Searches"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts & Notifications"]) 