from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient
from src.report_agent.report_state import GraphBState
from src.report_agent.report_node import (
    report_init_node,
    signal_extract_node,
    risk_score_node,
    report_plan_node,
    report_context_fetch_node,
    kg_enrich_node,
    memory_add_node,
    assemble_report_json_node,
    validate_schema_node,
    repair_once_node,
    return_and_trace_node,
)
from src.config import settings

client = MongoClient(settings.MONGO_URI)
checkpointer = MongoDBSaver(client=client, db_name=settings.CHECKPOINT_DB_NAME)


def build_report_graph():
    """
    Builds Graph B (Post-session Report Graph) with the following structure:
    
    Main flow:
    START → ReportInit → ReportGuardrails → SignalExtract → RiskScore → ReportPlan
    
    Parallel context fetching (based on ReportPlan decisions):
    ReportPlan → ReportContextFetch (if retrievalNeeded)
    ReportPlan → KGEnrich (if kgNeeded)
    ReportPlan → MemoryAdd (if memoryNeeded)
    
    Assembly flow:
    All context nodes → AssembleReportJSON → ValidateSchema
    
    Validation flow:
    ValidateSchema → (if valid) ReturnAndTrace → END
    ValidateSchema → (if invalid) RepairOnce → ValidateSchema (single retry) → ReturnAndTrace → END
    """
    workflow = StateGraph(GraphBState)
    
    # Add all nodes
    workflow.add_node("report_init", report_init_node)
    workflow.add_node("signal_extract", signal_extract_node)
    workflow.add_node("risk_score", risk_score_node)
    workflow.add_node("report_plan", report_plan_node)
    workflow.add_node("report_context_fetch", report_context_fetch_node)
    workflow.add_node("kg_enrich", kg_enrich_node)
    workflow.add_node("memory_add", memory_add_node)
    workflow.add_node("assemble_report_json", assemble_report_json_node)
    workflow.add_node("validate_schema", validate_schema_node)
    workflow.add_node("repair_once", repair_once_node)
    workflow.add_node("return_and_trace", return_and_trace_node)
    
    # Conditional edge functions
    def route_after_plan(state: GraphBState) -> list[str]:
        """
        Routes to appropriate context fetching nodes based on plan.
        For simplicity, we'll route to all three and let them handle empty results.
        In production, you could optimize this to skip unnecessary nodes.
        """
        # For now, always go through all context nodes
        # They will only process if needed
        return ["report_context_fetch"]
    
    def route_after_validation(state: GraphBState) -> str:
        """
        Routes based on validation result.
        If valid -> return_and_trace
        If invalid and not repaired -> repair_once
        If invalid and already repaired -> return_and_trace (give up gracefully)
        """
        valid = state.get("validation", {}).get("valid", False)
        repaired = state.get("validation", {}).get("repaired", False)
        
        if valid:
            #print("[ConditionalEdge] Report valid, routing to return_and_trace")
            return "return_and_trace"
        elif repaired:
            # Already tried repair once, give up and return
            #print("[ConditionalEdge] Report still invalid after repair, giving up and routing to return_and_trace")
            return "return_and_trace"
        else:
            #print("[ConditionalEdge] Report invalid, routing to repair_once")
            return "repair_once"
    
    # Set entry point
    workflow.add_edge(START, "report_init")
    
    # Main sequential flow
    workflow.add_edge("report_init", "signal_extract")
    workflow.add_edge("signal_extract", "risk_score")
    workflow.add_edge("risk_score", "report_plan")
    
    # Context fetching (simplified - all in sequence for now)
    # In a more advanced version, these could be parallelized
    workflow.add_edge("report_plan", "report_context_fetch")
    workflow.add_edge("report_context_fetch", "kg_enrich")
    workflow.add_edge("kg_enrich", "memory_add")
    
    # Assembly
    workflow.add_edge("memory_add", "assemble_report_json")
    workflow.add_edge("assemble_report_json", "validate_schema")
    
    # Validation routing
    workflow.add_conditional_edges(
        "validate_schema",
        route_after_validation,
        {
            "repair_once": "repair_once",
            "return_and_trace": "return_and_trace",
        }
    )
    
    # Repair loop (single retry)
    workflow.add_edge("repair_once", "validate_schema")
    
    # Finalize
    workflow.add_edge("return_and_trace", END)
    
    return workflow.compile(checkpointer=checkpointer)


report_graph = build_report_graph()
