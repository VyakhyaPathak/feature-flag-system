from fastapi import FastAPI
app = FastApi(title="Feature Flag Management System")
@app.get("heath/")
def heath_check():
    return {"status" : "ok"}
    
