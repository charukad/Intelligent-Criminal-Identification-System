from fastapi import APIRouter

from src.api.v1.endpoints import auth, users, criminals, recognition, stats, cases, stations, alerts

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(criminals.router, prefix="/criminals", tags=["criminals"])
api_router.include_router(recognition.router, prefix="/recognition", tags=["recognition"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(stations.router, prefix="/stations", tags=["stations"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
