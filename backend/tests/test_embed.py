"""embed_texts is a thin wrapper around the OpenAI SDK. We can't call the real
API in tests (no network, no key, no bill), so these tests inject a fake
client that honors the same `.embeddings.create(model=, input=)` contract —
this is an external paid API boundary, exactly where a test double is
unavoidable rather than testing our own code via a mock.
"""

from app.ingest.embed import embed_texts


class _FakeEmbeddingItem:
    def __init__(self, embedding):
        self.embedding = embedding


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeEmbeddingsResource:
    def __init__(self):
        self.calls = []

    def create(self, model, input):
        self.calls.append({"model": model, "input": input})
        return _FakeResponse([_FakeEmbeddingItem([0.1, 0.2, 0.3]) for _ in input])


class _FakeOpenAIClient:
    def __init__(self):
        self.embeddings = _FakeEmbeddingsResource()


def test_embed_texts_returns_a_vector_per_input_text():
    client = _FakeOpenAIClient()

    vectors = embed_texts(["hello", "world"], client=client)

    assert vectors == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]


def test_embed_texts_sends_all_texts_in_one_call():
    client = _FakeOpenAIClient()

    embed_texts(["a", "b", "c"], client=client)

    assert client.embeddings.calls == [{"model": client.embeddings.calls[0]["model"], "input": ["a", "b", "c"]}]


def test_embed_texts_empty_input_returns_empty_without_calling_the_api():
    client = _FakeOpenAIClient()

    assert embed_texts([], client=client) == []
    assert client.embeddings.calls == []
