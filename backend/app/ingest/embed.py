from openai import OpenAI

from app.config import get_settings


def embed_texts(texts: list[str], client: OpenAI | None = None) -> list[list[float]]:
    if not texts:
        return []
    settings = get_settings()
    client = client or OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(model=settings.embedding_model, input=texts)
    return [item.embedding for item in response.data]
