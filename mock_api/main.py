from fastapi import FastAPI
from mock_api.routers import vms, projects, metrics

app = FastAPI(
    title="Cloud Operations Mock API",
    description="Synthetic cloud infrastructure API for the AI agent project.",
    version="1.0.0",
)

app.include_router(vms.router)
app.include_router(projects.router)
app.include_router(metrics.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
