from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient
from src.agents.state import GraphAState
from src.agents.node import (
    risk_triage_node,
    fast_acknowledge_node,
    route_decider_node,
    query_fanout_translate_node,
    retrieve_context_node,
    context_pack_builder_node,
    counseling_composer_node,
    crisis_override_node,
    stream_out_node,
    checkpoint_and_trace_node,
    session_phase_manager_node
)
from src.config import settings

client = MongoClient(settings.MONGO_URI)
checkpointer = MongoDBSaver(client=client, db_name=settings.CHECKPOINT_DB_NAME)


def build_graph():
    """
    Builds Graph A with the following structure:
    
    Note: State is pre-initialized in FastAPI endpoint before graph invocation.
    
    Main flow: GuardrailsGate → RiskTriage
    
    Safety fork: RiskTriage → (if needs_crisis) CrisisOverride → StreamOut → CheckpointAndTrace → END
    
    Normal smooth path: RiskTriage → FastAcknowledge → RouteDecider
    
    Retrieval decision:
      - (if retrieval_needed = false) → CounselingComposer → StreamOut → CheckpointAndTrace → END
      - (if retrieval_needed = true) → QueryFanoutTranslate
    
    Retrieval flow (tools integrated into retrieve_context):
      - QueryFanoutTranslate → RetrieveContext (uses tools for Qdrant, mem0, Neo4j) → ContextPackBuilder
    
    Assemble + compose: ContextPackBuilder → CounselingComposer
    
    Mid-turn escalation: CounselingComposer → (if new high-risk signal) CrisisOverride else StreamOut
    
    Finalize: StreamOut → CheckpointAndTrace → END
    """
    workflow = StateGraph(GraphAState)

    # Add all nodes (turn_init removed - state initialized in FastAPI)
    # workflow.add_node("guardrails_gate", guardrails_gate_node)
    workflow.add_node("risk_triage", risk_triage_node)
    workflow.add_node("fast_acknowledge", fast_acknowledge_node)
    workflow.add_node("route_decider", route_decider_node)
    workflow.add_node("query_fanout_translate", query_fanout_translate_node)
    workflow.add_node("retrieve_context", retrieve_context_node)
    workflow.add_node("context_pack_builder", context_pack_builder_node)
    workflow.add_node("counseling_composer", counseling_composer_node)
    workflow.add_node("crisis_override", crisis_override_node)
    workflow.add_node("stream_out", stream_out_node)
    workflow.add_node("checkpoint_and_trace", checkpoint_and_trace_node)
    workflow.add_node("session_phase_manager", session_phase_manager_node)

    # Conditional edge functions
    def check_needs_crisis_after_triage(state: GraphAState) -> str:
        """Safety fork: check if immediate crisis intervention needed"""
        needs_crisis = state.get("safety", {}).get("needsCrisis", False)
        if needs_crisis:
            print("[ConditionalEdge] Routing to crisis_override")
            return "crisis_override"
        print("[ConditionalEdge] Routing to fast_acknowledge")
        return "fast_acknowledge"

    def check_retrieval_needed(state: GraphAState) -> str:
        """Retrieval decision: check if context retrieval is needed"""
        retrieval_needed = state.get("routing", {}).get("retrievalNeeded", False)
        if retrieval_needed:
            print("[ConditionalEdge] Routing to query_fanout_translate_node")
            return "query_fanout_translate"
        print("[ConditionalEdge] Routing to counseling_composer")
        return "counseling_composer"

    def check_mid_turn_escalation(state: GraphAState) -> str:
        """Mid-turn escalation: check if crisis signal appeared during composition"""
        # TODO: Implement logic

        needs_crisis = state.get("safety", {}).get("needsCrisis", False)
        if needs_crisis:
            return "crisis_override"
        return "stream_out"

    # Set entry point (start from guardrails_gate since state is pre-initialized)
    # workflow.set_entry_point("guardrails_gate")

    # Main flow: GuardrailsGate → RiskTriage
    workflow.add_edge(START, "risk_triage")

    # Safety fork from RiskTriage
    workflow.add_conditional_edges(
        "risk_triage",
        check_needs_crisis_after_triage,
        {
            "crisis_override": "crisis_override",
            "fast_acknowledge": "fast_acknowledge",
        }
    )

    # Normal smooth path: FastAcknowledge → RouteDecider
    workflow.add_edge("fast_acknowledge", "route_decider")

    # Retrieval decision from RouteDecider
    workflow.add_conditional_edges(
        "route_decider",
        check_retrieval_needed,
        {
            "query_fanout_translate": "query_fanout_translate",
            "counseling_composer": "counseling_composer",
        }
    )

    # Retrieval flow (tools integrated into retrieve_context node)
    workflow.add_edge("query_fanout_translate", "retrieve_context")
    workflow.add_edge("retrieve_context", "context_pack_builder")

    # Context assembled → Compose counseling response
    workflow.add_edge("context_pack_builder", "session_phase_manager")
    workflow.add_edge("session_phase_manager", "counseling_composer")

    # After counseling_composer, check if session ended
    def check_session_ended(state: GraphAState) -> str:
        """Check if session is complete (ready for reporting)"""
        phase = state.get("sessionPhase", {}).get("current", "opening")
        
        if phase == "ended":
            return "generate_report"  # Transition to reporting agent
        
        # Check for mid-turn crisis escalation
        needs_crisis = state.get("safety", {}).get("needsCrisis", False)
        if needs_crisis:
            return "crisis_override"
        
        return "stream_out"
    
    workflow.add_conditional_edges(
        "counseling_composer",
        check_session_ended,
        {
            # "generate_report": "generate_report_node",  # NEW: Reporting phase
            "crisis_override": "crisis_override",
            "stream_out": "stream_out"
        }
    )

    # Mid-turn escalation check
    workflow.add_conditional_edges(
        "counseling_composer",
        check_mid_turn_escalation,
        {
            "crisis_override": "crisis_override",
            "stream_out": "stream_out",
        }
    )

    # Crisis override goes to stream out
    workflow.add_edge("crisis_override", "stream_out")

    # Finalize: StreamOut → CheckpointAndTrace → END
    workflow.add_edge("stream_out", "checkpoint_and_trace")
    workflow.add_edge("checkpoint_and_trace", END)

    return workflow.compile(checkpointer=checkpointer)


app_graph = build_graph()