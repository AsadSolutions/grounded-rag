from benchmarks.generate import generate_synthetic_documents


def test_generates_requested_count():
    docs = generate_synthetic_documents(25, seed=1)
    assert len(docs) == 25


def test_word_counts_within_bounds():
    docs = generate_synthetic_documents(50, seed=2)
    for doc in docs:
        word_count = len(doc.content.decode("utf-8").split())
        assert 300 <= word_count <= 2000


def test_fact_ids_are_unique():
    docs = generate_synthetic_documents(200, seed=3)
    fact_ids = {doc.fact_id for doc in docs}
    assert len(fact_ids) == 200


def test_fact_id_appears_in_content():
    docs = generate_synthetic_documents(20, seed=4)
    for doc in docs:
        assert doc.fact_id in doc.content.decode("utf-8")


def test_deterministic_given_same_seed():
    first = generate_synthetic_documents(10, seed=99)
    second = generate_synthetic_documents(10, seed=99)
    assert [d.fact_id for d in first] == [d.fact_id for d in second]
    assert [d.content for d in first] == [d.content for d in second]


def test_different_seeds_produce_different_fact_ids():
    first = generate_synthetic_documents(10, seed=1)
    second = generate_synthetic_documents(10, seed=2)
    assert {d.fact_id for d in first} != {d.fact_id for d in second}


def test_doc_names_are_unique():
    docs = generate_synthetic_documents(100, seed=5)
    names = {doc.doc_name for doc in docs}
    assert len(names) == 100


def test_length_distribution_is_not_uniform():
    # A realistic distribution shouldn't be a flat line between the bounds —
    # there should be meaningfully more variance/skew than "every doc is the
    # same length" or "evenly spaced."
    docs = generate_synthetic_documents(300, seed=6)
    word_counts = sorted(len(d.content.decode("utf-8").split()) for d in docs)
    assert word_counts[0] < word_counts[len(word_counts) // 2] < word_counts[-1]
