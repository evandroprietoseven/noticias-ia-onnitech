from fastapi import FastAPI
from app.api import routes

app = FastAPI(title="Notícias Diárias Onnitech", version="0.1.0")
app.include_router(routes.router)
