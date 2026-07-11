from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from app.routers import flags
from app.database import get_db
from app.redis_client import redis_client

logger = logging.getLogger("feature_flag_system")

app = FastAPI(title="Feature Flag Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flags.router)


# Global safety net: any exception we did NOT anticipate (DB connection drop,
# a bug, Redis being down mid-request, etc.) is caught here so the API always
# returns clean JSON instead of crashing the process or leaking a raw
# traceback to the client. Expected errors (404, 400, 422) are unaffected —
# those are still raised as HTTPException/validation errors in the routers
# and handled by FastAPI's normal flow before ever reaching this handler.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Something went wrong on our end. Please try again, and contact support if it keeps happening.",
            "error_type": type(exc).__name__,
        },
    )


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    health_status = {
        "status": "healthy",
        "postgres": "disconnected",
        "redis": "disconnected"
    }
    
    # 1. Test PostgreSQL Connection
    try:
        db.execute(text("SELECT 1"))
        health_status["postgres"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["postgres"] = f"error: {str(e)}"
        
    # 2. Test Redis Connection
    try:
        if redis_client.ping():
            health_status["redis"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["redis"] = f"error: {str(e)}"
        
    # If anything is broken, return a 500 error code
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=500, detail=health_status)
        
    return health_status    
@app.get("/")
def root():
    return {"message": "Feature Flag Management System API is running. Visit /docs for API documentation."}