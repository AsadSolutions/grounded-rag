"""Graph wiring only — no retrieval or LLM logic lives here (CLAUDE.md rule 6)."""

from langgraph.graph import END, StateGraph

from app.graph.nodes import (
    check_groundedness_llm,
    generate,
    generate_answer_llm,
    grade,
    grade_chunks_llm,
    groundedness_check,
    retrieve,
    rewrite,
    rewrite_query_llm,
    route_after_check,
    route_after_grade,
)
from app.models import GraphState
from app.retrieval.hybrid import hybrid_search


def build_graph(
    *,
    search_fn=hybrid_search,
    grade_fn=grade_chunks_llm,
    rewrite_fn=rewrite_query_llm,
    generate_fn=generate_answer_llm,
    check_fn=check_groundedness_llm,
):
    graph = StateGraph(GraphState)
    graph.add_node("retrieve", lambda state: retrieve(state, search_fn=search_fn))
    graph.add_node("grade", lambda state: grade(state, grade_fn=grade_fn))
    graph.add_node("rewrite", lambda state: rewrite(state, rewrite_fn=rewrite_fn))
    graph.add_node("generate", lambda state: generate(state, generate_fn=generate_fn))
    graph.add_node("groundedness_check", lambda state: groundedness_check(state, check_fn=check_fn))

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "grade")
    graph.add_conditional_edges("grade", route_after_grade, {"rewrite": "rewrite", "generate": "generate"})
    graph.add_edge("rewrite", "retrieve")
    graph.add_edge("generate", "groundedness_check")
    graph.add_conditional_edges(
        "groundedness_check",
        route_after_check,
        {"finish": END, "regenerate": "generate", "finish_low_confidence": END},
    )

    return graph.compile()


def run_graph(state: GraphState, graph=None, **fns) -> GraphState:
    compiled = graph or build_graph(**fns)
    return GraphState(**compiled.invoke(state))
