from src.report_agent.report_state import GraphBState
from src.report_agent.report_output_schema import (
    #GuardrailsOutputModel,
    SignalExtractModel,
    RiskScoreModel,
    ReportPlanModel,
    AssembleReportModel,
    ValidateSchemaModel
)
from src.config import settings
from src.report_agent.report_prompts import (
    #REPORT_GUARDRAILS_SYSTEM_PROMPT,
    SIGNAL_EXTRACT_SYSTEM_PROMPT,
    RISK_SCORE_SYSTEM_PROMPT,
    REPORT_PLAN_SYSTEM_PROMPT,
    ASSEMBLE_REPORT_SYSTEM_PROMPT
)
from src.agents.tools import retrieve_from_qdrant
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
import json

load_dotenv()

# Use LangChain's Gemini client for better compatibility
llm_base = ChatGoogleGenerativeAI(
    model=settings.GEMINI_MODEL,
    google_api_key=settings.GEMINI_API_KEY,
    temperature=0.3
)

llm_mini = ChatGoogleGenerativeAI(
    model=settings.GEMINI_MODEL_MINI,
    google_api_key=settings.GEMINI_API_KEY,
    temperature=0.3
)
def escape_braces(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}")

def report_init_node(state: GraphBState) -> GraphBState:
    """
    Loads transcript + session metadata; defines output schema target.
    Initializes trace and timestamp.
    """
    #print("[ReportInit] Initializing report generation...")
    
    # Ensure required fields are present
    if "trace" not in state:
        state["trace"] = {}
    
    if "checkpoint" not in state:
        state["checkpoint"] = {}

    if "reportContext" not in state:
        state["reportContext"] = {}

    
    # Initialize timestamp
    from datetime import datetime
    state["input"]["now"] = datetime.utcnow().isoformat() + "Z"
    
    #print(f"[ReportInit] Session: {state.get('sessionId')}, User: {state.get('userId')}")
    #print(f"[ReportInit] Transcript length: {len(state['input']['transcript'])} turns")
    
    return state


# def report_guardrails_node(state: GraphBState) -> GraphBState:
#     """
#     Pass-through node: Guardrails disabled.
#     """
#     # Use original transcript directly, skip scrubbing
#     state["guardrails"]["scrubbedTranscript"] = state["input"]["transcript"]
#     return state


def signal_extract_node(state: GraphBState) -> GraphBState:
    """
    Extracts structured signals from transcript: emotions, symptoms, stressors, 
    protective factors, duration cues.
    """
    #print("[SignalExtract] Extracting clinical signals...")
    
    # Use scrubbed transcript if available, otherwise original
    transcript = state["guardrails"].get("scrubbedTranscript", state["input"]["transcript"])
    
    transcript_text = "\n".join([
        f"{turn.get('role', 'unknown')}: {turn.get('content', '')}" 
        for turn in transcript
    ])
    
    try:
        parser = PydanticOutputParser(pydantic_object=SignalExtractModel)
        format_instructions = escape_braces(parser.get_format_instructions())
        system_prompt = SIGNAL_EXTRACT_SYSTEM_PROMPT + "\n\n" + format_instructions

        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Analyze this transcript:\n\n{transcript}")
        ])
        
        chain = prompt | llm_base | parser
        parsed = chain.invoke({"transcript": transcript_text})
        
        # Debug: Print raw LLM output
        # print(f"[SignalExtract] DEBUG - Raw extraction result:")
        # print(f"  Symptoms: {parsed.symptoms}")
        # print(f"  Stressors: {parsed.stressors}")
        # print(f"  Emotions: {parsed.emotions}")
        # print(f"  Protective Factors: {parsed.protectiveFactors}")
        # print(f"  Time Hints: {parsed.timeHints}")
        
    except Exception as e:
        # print(f"[SignalExtract] Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to empty structures
        parsed = SignalExtractModel(
            symptoms=[],
            stressors=[],
            emotions=[],
            protectiveFactors=[],
            timeHints=[]
        )
    
    state["extracted"]["symptoms"] = parsed.symptoms
    state["extracted"]["stressors"] = parsed.stressors
    state["extracted"]["emotions"] = parsed.emotions
    state["extracted"]["protectiveFactors"] = parsed.protectiveFactors
    state["extracted"]["timeHints"] = parsed.timeHints
    
    # print(f"[SignalExtract] ✓ Extracted:")
    # print(f"  - Symptoms: {len(parsed.symptoms)}")
    # print(f"  - Stressors: {len(parsed.stressors)}")
    # print(f"  - Emotions: {len(parsed.emotions)}")
    # print(f"  - Protective factors: {len(parsed.protectiveFactors)}")
    # print(f"  - Time hints: {len(parsed.timeHints)}")
    
    return state


def risk_score_node(state: GraphBState) -> GraphBState:
    """
    Computes stable risk score (0–5) + flags crisis_recommendation.
    """
    #print("[RiskScore] Computing risk assessment...")
    
    # Prepare extracted signals as context
    extracted_summary = f"""
        Symptoms: {', '.join(state['extracted']['symptoms']) if state['extracted']['symptoms'] else 'None'}
        Stressors: {', '.join(state['extracted']['stressors']) if state['extracted']['stressors'] else 'None'}
        Emotions: {', '.join(state['extracted']['emotions']) if state['extracted']['emotions'] else 'None'}
        Protective Factors: {', '.join(state['extracted']['protectiveFactors']) if state['extracted']['protectiveFactors'] else 'None'}
        Time Hints: {', '.join(state['extracted']['timeHints']) if state['extracted']['timeHints'] else 'None'}
        """
    
    try:
        parser = PydanticOutputParser(pydantic_object=RiskScoreModel)
        format_instructions = escape_braces(parser.get_format_instructions())
        system_prompt = RISK_SCORE_SYSTEM_PROMPT + "\n\n" + format_instructions

        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Assess risk based on these signals:\n\n{signals}")
        ])
        
        chain = prompt | llm_base | parser
        parsed = chain.invoke({"signals": extracted_summary})
        
    except Exception as e:
        # print(f"[RiskScore] Error during assessment: {e}")
        parsed = RiskScoreModel(
            riskScore=0,
            crisisRecommendation=False,
            flags=[]
        )
    
    state["safety"]["riskScore"] = parsed.riskScore
    state["safety"]["crisisRecommendation"] = parsed.crisisRecommendation
    state["safety"]["flags"] = parsed.flags
    
    risk_emoji = "🔴" if parsed.riskScore >= 4 else "🟡" if parsed.riskScore >= 2 else "🟢"
    # print(f"[RiskScore] {risk_emoji} Risk Score: {parsed.riskScore}/5")
    # print(f"[RiskScore] Crisis Recommendation: {parsed.crisisRecommendation}")
    # print(f"[RiskScore] Flags: {', '.join(parsed.flags) if parsed.flags else 'None'}")
    
    return state


def report_plan_node(state: GraphBState) -> GraphBState:
    """
    Decides report sections + what to emphasize (immediate vs week vs long-term).
    Keeps it actionable.
    """
    #print("[ReportPlan] Planning report structure...")
    
    # Prepare context for planning
    planning_context = f"""
        Risk Score: {state['safety']['riskScore']}/5
        Crisis Recommendation: {state['safety']['crisisRecommendation']}
        Flags: {', '.join(state['safety']['flags']) if state['safety']['flags'] else 'None'}
        Symptoms: {', '.join(state['extracted']['symptoms']) if state['extracted']['symptoms'] else 'None'}
        Emotions: {', '.join(state['extracted']['emotions']) if state['extracted']['emotions'] else 'None'}
        """
    
    try:
        parser = PydanticOutputParser(pydantic_object=ReportPlanModel)
        format_instructions = escape_braces(parser.get_format_instructions())
        system_prompt = REPORT_PLAN_SYSTEM_PROMPT + "\n\n" + format_instructions

        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{context}")
        ])
        
        chain = prompt | llm_mini | parser
        parsed = chain.invoke({"context": planning_context})
        
    except Exception as e:
        #print(f"[ReportPlan] Error: {e}")
        parsed = ReportPlanModel(
            sections=["coping_strategies"],
            emphasis="long-term",
            retrievalNeeded=False,
            kgNeeded=False,
            memoryNeeded=False
        )
    
    # Store plan decisions in state (we'll use them to route to appropriate nodes)
    state["_plan"] = {
        "sections": parsed.sections,
        "emphasis": parsed.emphasis,
        "retrievalNeeded": parsed.retrievalNeeded,
        "kgNeeded": parsed.kgNeeded,
        "memoryNeeded": parsed.memoryNeeded
    }
    
    # print(f"[ReportPlan] ✓ Sections: {', '.join(parsed.sections)}")
    # print(f"[ReportPlan] ✓ Emphasis: {parsed.emphasis}")
    # print(f"[ReportPlan] ✓ Needs - RAG: {parsed.retrievalNeeded}, KG: {parsed.kgNeeded}, Memory: {parsed.memoryNeeded}")
    
    return state


def report_context_fetch_node(state: GraphBState) -> GraphBState:
    """
    Pulls evidence/guideline snippets from Qdrant to ground "next steps".
    """
    # print("[ReportContextFetch] Fetching evidence from Qdrant...")
    
    # TODO: Qdrant integration - temporarily disabled
    # Build retrieval query based on symptoms and risk level
    symptoms = state['extracted']['symptoms']
    risk_score = state['safety']['riskScore']
    
    query = f"Mental health interventions for: {', '.join(symptoms)}. Risk level: {risk_score}/5. Evidence-based recommendations and next steps."
    
    try:
        docs = retrieve_from_qdrant.invoke({"query": query, "top_k": 5})
        state["reportContext"]["ragDocs"] = docs
        #print(f"[ReportContextFetch] ✓ Retrieved {len(docs)} documents")
    except Exception as e:
        #print(f"[ReportContextFetch] Error: {e}")
        state["reportContext"]["ragDocs"] = []
    
    # # Placeholder until Qdrant is set up
    # state["reportContext"]["ragDocs"] = []
    # print(f"[ReportContextFetch] ⚠️  Qdrant disabled - using empty context")
    
    return state


def kg_enrich_node(state: GraphBState) -> GraphBState:
    """
    Adds structured mapping: risk→recommended actions, symptom clusters→common techniques.
    (Neo4j integration - placeholder for now)
    """
    #print("[KGEnrich] Enriching with knowledge graph...")
    
    # TODO: Implement Neo4j integration
    # For now, use rule-based mappings
    
    risk_score = state['safety']['riskScore']
    symptoms = state['extracted']['symptoms']
    
    facts = []
    
    # Risk-based recommendations
    if risk_score >= 4:
        facts.append("Immediate professional intervention recommended for high-risk cases")
        facts.append("Crisis hotline: AASRA 91-22-27546669, iCall 9152987821")
    elif risk_score >= 2:
        facts.append("Regular therapy sessions recommended for moderate distress")
        facts.append("Consider CBT or DBT-based interventions")
    
    # Symptom-based techniques
    if any(s in str(symptoms).lower() for s in ["anxiety", "panic", "worry"]):
        facts.append("Grounding techniques and breathing exercises effective for anxiety")
    
    if any(s in str(symptoms).lower() for s in ["depression", "low mood", "hopeless"]):
        facts.append("Behavioral activation and CBT reframing helpful for depression")
    
    state["reportContext"]["kgFacts"] = facts
    #print(f"[KGEnrich] ✓ Added {len(facts)} knowledge facts")
    
    return state


def memory_add_node(state: GraphBState) -> GraphBState:
    """
    Adds longitudinal "what helped before / repeated patterns" into next steps.
    (mem0 integration - placeholder for now)
    """
    #print("[MemoryAdd] Recalling user history...")
    
    # TODO: Implement mem0 integration
    # For now, placeholder
    
    state["reportContext"]["memoryItems"] = []
    #print(f"[MemoryAdd] ✓ Memory integration (placeholder)")
    
    return state


def assemble_report_json_node(state: GraphBState) -> GraphBState:
    """
    Produces JSON object: riskScore, symptoms[], summary, nextSteps[] 
    (and optional resources list).
    """
    #print("[AssembleReport] Assembling final report...")
    
    # Prepare comprehensive context
    context = f"""
        ## Extracted Signals
        Symptoms: {', '.join(state['extracted']['symptoms']) if state['extracted']['symptoms'] else 'None'}
        Stressors: {', '.join(state['extracted']['stressors']) if state['extracted']['stressors'] else 'None'}
        Emotions: {', '.join(state['extracted']['emotions']) if state['extracted']['emotions'] else 'None'}
        Protective Factors: {', '.join(state['extracted']['protectiveFactors']) if state['extracted']['protectiveFactors'] else 'None'}
        Time Context: {', '.join(state['extracted']['timeHints']) if state['extracted']['timeHints'] else 'None'}

        ## Risk Assessment
        Risk Score: {state['safety']['riskScore']}/5
        Crisis Recommendation: {state['safety']['crisisRecommendation']}
        Flags: {', '.join(state['safety']['flags']) if state['safety']['flags'] else 'None'}

        ## Evidence-Based Guidance
        {chr(10).join([f"- {doc['content'][:200]}..." for doc in state['reportContext'].get('ragDocs', [])[:3]])}

        ## Knowledge Graph Facts
        {chr(10).join([f"- {fact}" for fact in state['reportContext'].get('kgFacts', [])])}

        ## Plan Emphasis
        {state.get('_plan', {}).get('emphasis', 'balanced')} timeframe focus
        """
    
    try:
        parser = PydanticOutputParser(pydantic_object=AssembleReportModel)
        format_instructions = escape_braces(parser.get_format_instructions())
        system_prompt = ASSEMBLE_REPORT_SYSTEM_PROMPT + "\n\n" + format_instructions

        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{context}")
        ])
        
        chain = prompt | llm_base | parser
        parsed = chain.invoke({"context": context})
        
    except Exception as e:
        print(f"[AssembleReport] Error during assembly: {e}")
        parsed = AssembleReportModel(
            riskScore=state['safety']['riskScore'],
            symptoms=["Session completed"],
            summary="Unable to fully assemble report.",
            nextSteps=["Consult with healthcare provider"]
        )
    
    state["report"]["riskScore"] = parsed.riskScore
    state["report"]["symptoms"] = parsed.symptoms
    state["report"]["summary"] = parsed.summary
    state["report"]["nextSteps"] = parsed.nextSteps
    
    # print(f"[AssembleReport] ✓ Report assembled")
    # print(f"  - Risk: {parsed.riskScore}/5")
    # print(f"  - Symptoms: {len(parsed.symptoms)}")
    # print(f"  - Next steps: {len(parsed.nextSteps)}")
    
    return state


def validate_schema_node(state: GraphBState) -> GraphBState:
    """
    Validates JSON strictly; ensures DB-ready.
    """
    #print("[ValidateSchema] Validating report structure...")
    
    errors = []
    
    # Check required fields
    report = state.get("report", {})
    
    if "riskScore" not in report:
        errors.append("Missing riskScore")
    elif not (0 <= report["riskScore"] <= 5):
        errors.append("riskScore must be between 0 and 5")
    
    if "symptoms" not in report:
        errors.append("Missing symptoms list")
    
    if "summary" not in report or not report["summary"].strip():
        errors.append("Missing or empty summary")
    
    if "nextSteps" not in report or not report["nextSteps"]:
        errors.append("Missing or empty nextSteps list")
    
    # Set validation state
    state["validation"]["valid"] = len(errors) == 0
    state["validation"]["errors"] = errors
    state["validation"]["repaired"] = False
    
    # if state["validation"]["valid"]:
    #     print("[ValidateSchema] ✅ Report is valid")
    # else:
    #     print(f"[ValidateSchema] ❌ Validation errors: {', '.join(errors)}")
    
    return state


def repair_once_node(state: GraphBState) -> GraphBState:
    """
    One retry loop to fix schema formatting only (no content changes unless 
    required for schema).
    """
    #print("[RepairOnce] Attempting to repair report...")
    
    errors = state["validation"].get("errors", [])
    current_report = state.get("report", {})
    
    # Simple repairs
    if "Missing riskScore" in errors:
        if "safety" in state and state["safety"].get("riskScore") is not None:
            state["report"]["riskScore"] = state["safety"]["riskScore"]
        else:
            state["report"]["riskScore"] = 0
    
    if "Missing symptoms list" in errors:
        extracted_symptoms = state.get("extracted", {}).get("symptoms", [])
        state["report"]["symptoms"] = extracted_symptoms
    
    if "Missing or empty summary" in errors:
        state["report"]["summary"] = "Session completed. Clinical assessment in progress."
    
    if "Missing or empty nextSteps list" in errors:
        risk_score = state.get("report", {}).get("riskScore", 0) or state.get("safety", {}).get("riskScore", 0)
        if risk_score >= 4:
            state["report"]["nextSteps"] = ["Contact crisis helpline immediately", "Ensure safety plan is in place"]
        else:
            state["report"]["nextSteps"] = ["Continue self-care practices", "Schedule follow-up session"]
    
    # Mark as repaired so we don't loop infinitely
    state["validation"]["repaired"] = True
    #print("[RepairOnce] ✓ Repair attempt completed")
    
    return state


def return_and_trace_node(state: GraphBState) -> GraphBState:
    """
    Returns report JSON to Core, logs trace + checkpoint metadata.
    """
    #print("[ReturnAndTrace] Finalizing report...")
    
    from datetime import datetime
    
    # Set checkpoint data
    state["checkpoint"]["riskScore"] = state["report"].get("riskScore", 0)
    state["checkpoint"]["endedAt"] = datetime.now().isoformat() + "Z"
    
    # print("[ReturnAndTrace] ✅ Report generation complete")
    # print(f"  - Risk Score: {state['report'].get('riskScore', 0)}/5")
    # print(f"  - Summary length: {len(state['report'].get('summary', ''))} chars")
    # print(f"  - Next steps: {len(state['report'].get('nextSteps', []))} actions")
    
    return state
