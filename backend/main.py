from fastapi import FastAPI

app = FastAPI(title="Aegis")


@app.get("/api/health", operation_id="get_health")
def get_health() -> dict[str, str]:
    """Report that the backend is up."""
    return {"status": "ok"}
