#from fastapi import FastAPI
from sqlalchemy import text  # <- Add this import
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.routers import flags
from app.database import get_db
from app.redis_client import redis_client

app = FastAPI(title="Feature Flag Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flags.router)


@app.get("/health")
#def health_check():
    #return {"status": "ok"}
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