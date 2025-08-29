from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import engine
from app.models import models
from app.api.routes import auth, places, weather
from app.services.admin.__init__ import init_admin  # <-- ensure this import path matches your tree

@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine, checkfirst=True)
    yield

app = FastAPI(title="FoodMap API", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(places.router)
app.include_router(weather.router)
init_admin(app)

@app.get("/")
def root():
    return {"ok": True}
