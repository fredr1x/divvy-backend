from fastapi import FastAPI

app = FastAPI(title="Divvy API")

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/fuck-up")
def fuck_up():
    return {
        "status": "fuck",
        "text": "Erba idi nahuy"
    }