from fastapi import FastAPI

from app.routers import chat, documents, search

app = FastAPI()
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(chat.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
