from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.building_blocks.infrastructure.database import init_db
from src.building_blocks.infrastructure.config import envConfig

from src.modules.iam.presentation.routes import router as iam_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db() 
    yield

app = FastAPI(
    title="Food Delivery System",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(iam_router, prefix="/api/v1/auth", tags=["IAM"])

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Server is running smoothly!"}