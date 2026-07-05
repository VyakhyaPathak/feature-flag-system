from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import flags

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
def health_check():
    return {"status": "ok"}
@app.get("/")
def root():
    return {"message": "Feature Flag Management System API is running. Visit /docs for API documentation."}