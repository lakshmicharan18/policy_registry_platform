from fastapi import FastAPI

from app.api.routers.datasets import router as datasets_router
from app.api.routers.warehouses import router as warehouses_router


app = FastAPI(
    title="Policy Registry Platform",
    version="0.1.0",
)

app.include_router(warehouses_router)
app.include_router(datasets_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return the service health status."""
    return {
        "status": "healthy",
        "service": "policy-registry-platform",
    }
