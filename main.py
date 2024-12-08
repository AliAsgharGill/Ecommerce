from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise
from models import *



app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

# Registering the Tortoise ORM models with FastAPI
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)

