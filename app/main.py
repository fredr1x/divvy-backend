from fastapi import FastAPI

app = FastAPI(title="Divvy API")

@app.get("/health")
def health_check():
    return {"status": "ok"}
