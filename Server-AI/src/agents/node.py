from src.agents.state import GraphAState
from typing import List
from src.agents.output_schema import (
    SafetyModel, 
    FastAcknowledgeModel,
    route_decider_node_Model,
    query_fanout_translate_node_Model,
    WHETHER_USER_SHARED_CONCERN_Model,
    whether_GOAL_ACHEIVED_Model,
    WHETHER_USER_CONFIRMED_END_Model,
    counselling_composer_node_Model,
    
)
from src.config import settings
from src.agents.prompts import (
    risk_triage_node_SYSTEM_PROMPT, 
    fast_acknowledge_node_SYSTEM_PROMPT,
    route_decider_node_SYSTEM_PROMPT,
    query_fanout_translate_node_SYSTEM_PROMPT,
    counseling_composer_node_SYSTEM_PROMPT,
    WHETHER_USER_SHARED_CONCERN_SYSTEM_PROMPT,
    whether_goal_achieved_system_prompt,
    WHETHER_USER_CONFIRMED_END_SYSTEM_PROMPT,
    crisis_override_node_System_Prompt
)
from dotenv import load_dotenv
# from src.tools import recall_user_memory
from openai import OpenAI
# from src.agents.tools import retrieve_from_qdrant
from src.agents.tools import add_user_memory,recall_user_memory,retrieve_from_qdrant
from datetime import datetime, timedelta, UTC

load_dotenv()

llm = OpenAI(
    api_key=settings.GEMINI_API_KEY,
    base_url=settings.GEMINI_BASE_URL,
)

# def guardrails_gate_node(state: GraphAState) -> GraphAState:
#     """
#     Input sanitation + injection resistance + "allowed behavior" constraints;
#     ensures we don't follow malicious instructions.
#     """
#     # TODO: Implement logic
#     return {}


def risk_triage_node(state: GraphAState) -> GraphAState:
    """
    Detects urgency and self-harm/violence indicators;
    outputs risk_level + needs_crisis boolean + a "priority mode" (panic vs vent vs info).
    """

    user_input = state['input']['userText']

    result = llm.beta.chat.completions.parse(
        response_format=SafetyModel,
        model=settings.GEMINI_MODEL_MINI,
        messages=[
            { "role": "system", "content": risk_triage_node_SYSTEM_PROMPT },
            { "role": "user", "content": user_input }
        ]
    )

    state["safety"]["flags"] = result.choices[0].message.parsed.flags
    state['safety']['needsCrisis'] = result.choices[0].message.parsed.needsCrisis
    state['safety']["riskLevel"] = result.choices[0].message.parsed.riskLevel

    print(state['safety'])
    return state


def fast_acknowledge_node(state: GraphAState) -> GraphAState:
    """
    Generates an immediate 1 or 2 sentence supportive acknowledgement (or immediate grounding start).
    No retrieval needed. This is what you stream first to keep voice UX smooth.
    """
    user_input = state['input']['userText']

    result = llm.beta.chat.completions.parse(
        response_format=FastAcknowledgeModel,
        model=settings.GEMINI_MODEL_MINI,
        messages=[
            {"role" : "system", "content": fast_acknowledge_node_SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ]
    )

    # state['output']['fastAckText'] = result.choices[0].message.parsed.fastAckText
    fast_ack = result.choices[0].message.parsed.fastAckText
    state['output']['fastAckText'] = fast_ack
    # enqueue whole fast-ack message (no token streaming)
    state['output']['events'] = [{"type": "fast_ack", "text": fast_ack, "delay_ms": 0}]
    print("fastAckText 🤖: ", state["output"]['fastAckText'])
    return state


def route_decider_node(state: GraphAState) -> GraphAState:
    """
    Chooses the main counseling path for this turn (Grounding / CBT / Coping / Resource / Info)
    and whether retrieval is needed.
    """
    user_input = state['input']['userText']

    result = llm.beta.chat.completions.parse(
        model=settings.GEMINI_MODEL_MINI,
        response_format=route_decider_node_Model,
        messages=[
            {"role" : "system", "content": route_decider_node_SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ]
    )

    state["routing"]["route"] = result.choices[0].message.parsed.route
    state["routing"]["retrievalNeeded"] = result.choices[0].message.parsed.retrievalNeeded
    print("Route and Is retrival needed 💻 ", state["routing"])

    return state


def query_fanout_translate_node(state: GraphAState) -> GraphAState:
    """
    Produces 2–4 targeted retrieval queries (symptom keywords, situation summary, technique query) to improve recall.
    """
    if not state.get("routing", {}).get("retrievalNeeded"):
        state["routing"]["fanoutQueries"] = []
        return state
    
    user_input = state['input']['userText']
    safety_flags = state['safety']['flags']
    query_route = state['routing']["route"]

    combined_input = f"""
        User Input: {user_input}
        Safety Flags: {', '.join(safety_flags) if safety_flags else 'None'}
        Counseling Route: {', '.join(query_route) if isinstance(query_route, list) else query_route}
        """

    result = llm.chat.completions.parse(
        model=settings.GEMINI_MODEL,
        response_format=query_fanout_translate_node_Model,
        messages=[
            {"role" : "system", "content": query_fanout_translate_node_SYSTEM_PROMPT},
            {"role": "user", "content": combined_input},
        ]
    )

    # state["routing"]["fanoutQueries"] = result.choices[0].message.parsed.fanoutQueries
    state["routing"]["fanoutQueries"] = (result.choices[0].message.parsed.fanoutQueries or [])[:2]
    # print("Fanout queries 🤖: ", state["routing"]["fanoutQueries"])

    return state


def retrieve_context_node(state: GraphAState) -> GraphAState:
    """
    Similarity search from Qdrant (topK=4 default); returns chunks + source metadata.
    Uses integrated tools for Qdrant, mem0, and Neo4j retrieval.
    """
    fanout_queries = state.get("routing", {}).get("fanoutQueries", []) or []
    top_k = state.get("input", {}).get("topK", 4)
    user_id = state.get("userId")

    # Short-circuit if nothing to retrieve
    if not fanout_queries:
        state["rag"]["docs"] = []
        state["memory"]["items"] = []
        return state

    all_docs: List[dict] = []
    all_memories: List[str] = []

    # Execute retrieval once per fanout query (Qdrant + mem0)
    for query in fanout_queries:
        try:
            docs = retrieve_from_qdrant.invoke({"query": query, "top_k": top_k})
            all_docs.extend(docs)
        except Exception as e:
            print(f"[RetrieveContext] Error retrieving for query '{query}': {e}")

        if user_id:
            try:
                memories = recall_user_memory.invoke(
                    {"user_id": user_id, "query": query, "limit": 3}
                )
                all_memories.extend(memories)
            except Exception as e:
                print(f"[RetrieveContext] Error retrieving memories: {e}")

    # Deduplicate docs by content, keep highest score
    unique_docs = []
    seen_content = set()
    for doc in all_docs:
        if doc["content"] not in seen_content:
            seen_content.add(doc["content"])
            unique_docs.append(doc)

    unique_docs.sort(key=lambda x: x.get("score", 0) or 0, reverse=True)
    unique_docs = unique_docs[:top_k]

    state["rag"]["docs"] = [
        {
            "content": doc["content"],
            "score": doc.get("score"),
            "source": doc.get("source"),
            "metadata": doc.get("metadata", {}),
        }
        for doc in unique_docs
    ]
    state["memory"]["items"] = list(dict.fromkeys(all_memories))  # dedupe, preserve order

    print(f"\n{'='*80}")
    print(f"[RetrieveContext] Retrieved {len(state['rag']['docs'])} unique documents")
    return state

def context_pack_builder_node(state: GraphAState) -> GraphAState:
    """
    Compresses retrieval + memory into a "context pack":
    facts, suggestions, do/don't, and citations meta.
    """
    rag_docs = state.get("rag", {}).get("docs", [])
    memories = state.get("memory", {}).get("items", [])
    route = state.get("routing", {}).get("route", [])
    
    # Build route-specific guidance
    route_guidance = f"**Counseling Focus:** {', '.join(route)}\n" if route else ""
    
    # Build memory context section (only if memories exist)
    memory_context = ""
    if memories:
        memory_context = "\n**User's Past Preferences & Patterns:**\n"
        for i, memory in enumerate(memories[:5], 1):  # Top 5 memories
            memory_context += f"- {memory}\n"
    
    # Build RAG context section (only if docs exist)
    rag_context = ""
    if rag_docs:
        rag_context = "\n**Relevant Mental Health Knowledge:**\n"
        for i, doc in enumerate(rag_docs[:10], 1):  # Top 10 docs
            rag_context += f"\n{i}. [Source: {doc.get('source', 'Unknown')}]\n{doc['content']}\n"
    
    # Combine into merged context (handle empty sections gracefully)
    merged_context = f"{route_guidance}{memory_context}{rag_context}".strip()
    
    # Fallback if no context available at all
    if not merged_context:
        merged_context = "**No prior context available. Respond based on current user input.**"
    
    # Extract source metadata for citations
    sources_meta = [
        {
            "source": doc.get("source", "unknown"),
            "score": doc.get("score", 0.0),
            "metadata": doc.get("metadata", {})
        }
        for doc in rag_docs[:5]
    ]
    
    # Store in state
    state["contextPack"]["mergedContext"] = merged_context
    state["contextPack"]["sourcesMeta"] = sources_meta
    
    print(f"\n{'='*80}")
    print(f"[ContextPackBuilder] Built context pack:")
    print(f"  - RAG docs: {len(rag_docs)}")
    print(f"  - Memories: {len(memories)}")
    print(f"  - Total context length: {len(merged_context)} chars")
    print(f"  - Is first-time user: {len(memories) == 0}")
    print(f"{'='*80}\n")
    
    return state

def session_phase_manager_node(state: GraphAState) -> GraphAState:
    """
    Manages clinical session structure:
    - Opening (5 min / 2-4 turns): Build rapport, assess state
    - Working (15 min / 6-10 turns): Active intervention (CBT/grounding)
    - Closing (10 min / 2-3 turns): Summarize, plan next steps
    
    Determines current phase and sets objectives for counseling_composer.
    """
    
    user_input = state['input']['userText']
    route = state.get("routing", {}).get("route", [])
    recent_conversation_history = state.get("transcript", {}).get("recentTurns", [])

    combined_input= f"""
    Current user input: {user_input}
    Detected route: {', '.join(route) if route else 'None'}
    Recent conversation history:
    {chr(10).join([f"{turn['role'].upper()}: {turn['content']}" for turn in recent_conversation_history]) if recent_conversation_history else 'No prior conversation'}
    """

    # Initialize session phase on first turn
    if "sessionPhase" not in state or not state.get("sessionPhase"):
        now = datetime.now(UTC)
        state["sessionPhase"] = {
            "current": "opening",
            "startTime": now.isoformat(),  # Use CURRENT time, not input time
            "phaseStartTime": now.isoformat(),
            "openingTurns": 0,
            "workingTurns": 0,
            "closingTurns": 0,
            "totalDuration": 0.0,
            "interventionType": "",
            "rapportEstablished": False,
            "goalAchieved": False
        }
        print(f"[SessionPhase] Initialized: OPENING phase at {now.isoformat()}")
        return state
    
    # Get current phase data
    phase = state["sessionPhase"]
    current_phase = phase["current"]
    session_start = datetime.fromisoformat(phase["startTime"])
    phase_start = datetime.fromisoformat(phase["phaseStartTime"])
    now = datetime.now(UTC)
    
    # Calculate durations
    total_duration = (now - session_start).total_seconds() / 60  # minutes
    phase_duration = (now - phase_start).total_seconds() / 60
    
    phase["totalDuration"] = total_duration
    
    # Get turn counts
    opening_turns = phase["openingTurns"]
    working_turns = phase["workingTurns"]
    closing_turns = phase["closingTurns"]
    
    # --- PHASE TRANSITION LOGIC ---
    
    # 1. OPENING → WORKING transition
    if current_phase == "opening":
        # Conditions to move to WORKING:
        # - User shared main concern (detected via route_decider)
        # - OR 2-4 turns completed
        # - OR 5 minutes elapsed
        

        result = llm.beta.chat.completions.parse(
            model=settings.GEMINI_MODEL_MINI,
            response_format=WHETHER_USER_SHARED_CONCERN_Model,
            messages=[
                {"role" : "system", "content" : WHETHER_USER_SHARED_CONCERN_SYSTEM_PROMPT},
                {"role" : "user", "content" : combined_input}
            ]
        )

        user_shared_concern = result.choices[0].message.parsed.user_shared_concern
        
        print(f"🤖[SessionPhase] User shared concern: {user_shared_concern}")

        should_transition = (
            (opening_turns >= 2 and user_shared_concern) or  # Natural transition
            opening_turns >= 4 or  # Max turns
            phase_duration >= 5  # Max time
        )
        
        if should_transition:
            print(f"[SessionPhase] Transitioning: OPENING → WORKING")
            print(f"  Reason: turns={opening_turns}, concern_shared={user_shared_concern}, duration={phase_duration:.1f}min")
            
            phase["current"] = "working"
            phase["phaseStartTime"] = now.isoformat() + "Z"
            phase["rapportEstablished"] = True
            phase["interventionType"] = route[0] if route else "general_support"
        else:
            # Stay in opening
            phase["openingTurns"] += 1
    
    # 2. WORKING → CLOSING transition
    elif current_phase == "working":
        # Conditions to move to CLOSING:
        # - User reports relief/progress (goal achieved)
        # - OR 6-10 turns completed
        # - OR 15 minutes elapsed in working phase
        # - OR total session duration >= 20 minutes
        
        # Detect goal achievement (simplified - enhance with sentiment analysis)
        
        response = llm.beta.chat.completions.parse(
            model=settings.GEMINI_MODEL_MINI,
            response_format=whether_GOAL_ACHEIVED_Model,
            messages=[
                {"role" : "system", "content" : whether_goal_achieved_system_prompt},
                {"role" : "user", "content" : combined_input}
            ]
        )

        goal_achieved = response.choices[0].message.parsed.goal_achieved
        print(f"🤖Goal achievement detected: {goal_achieved}")
        
        should_transition = (
            (working_turns >= 6 and goal_achieved) or  # Natural completion
            working_turns >= 10 or  # Max turns
            phase_duration >= 15 or  # Max working phase time
            total_duration >= 20  # Total session approaching 30min
        )
        
        if should_transition:
            print(f"[SessionPhase] Transitioning: WORKING → CLOSING")
            print(f"  Reason: turns={working_turns}, goal_achieved={goal_achieved}, duration={phase_duration:.1f}min")
            
            phase["current"] = "closing"
            phase["phaseStartTime"] = now.isoformat() + "Z"
            phase["goalAchieved"] = goal_achieved
        else:
            # Stay in working
            phase["workingTurns"] += 1
    
    # 3. CLOSING → ENDED transition
    elif current_phase == "closing":
        # Conditions to end session:
        # - User confirms closure ("thanks", "goodbye", etc.)
        # - OR 2-3 turns completed in closing
        # - OR total session >= 30 minutes
        
        ending_input = f"""
        Current user input: {user_input}
        Recent conversation history:
        {chr(10).join([f"{turn['role'].upper()}: {turn['content']}" for turn in recent_conversation_history]) if recent_conversation_history else 'No prior conversation'}
        """
        
        res = llm.beta.chat.completions.parse(
            model=settings.GEMINI_MODEL_MINI,
            response_format=WHETHER_USER_CONFIRMED_END_Model,
            messages=[
                {"role" : "system", "content" : WHETHER_USER_CONFIRMED_END_SYSTEM_PROMPT},
                {"role" : "user", "content" : ending_input}
            ]
        )

        user_confirmed_end = res.choices[0].message.parsed.user_confirmed_end
        
        should_end = (
            user_confirmed_end or
            closing_turns >= 3 or
            total_duration >= 30
        )
        
        if should_end:
            print(f"[SessionPhase] Transitioning: CLOSING → ENDED")
            print(f"  Reason: confirmed={user_confirmed_end}, turns={closing_turns}, duration={total_duration:.1f}min")
            
            phase["current"] = "ended"
        else:
            # Stay in closing
            phase["closingTurns"] += 1
    
    # 4. ENDED state (session complete)
    elif current_phase == "ended":
        # Session is over - ready for reporting
        pass
    
    # --- LOG CURRENT STATE ---
    print(f"\n{'='*80}")
    print(f"[SessionPhase] Current State:")
    print(f"  Phase: {phase['current'].upper()}")
    print(f"  Total Duration: {total_duration:.1f} min")
    print(f"  Phase Duration: {phase_duration:.1f} min")
    print(f"  Turns: Opening={opening_turns}, Working={working_turns}, Closing={closing_turns}")
    print(f"  Rapport: {phase['rapportEstablished']}, Goal Achieved: {phase['goalAchieved']}")
    print(f"{'='*80}\n")
    
    return state

def counseling_composer_node(state: GraphAState) -> GraphAState:
    """
    Phase-aware counseling content generation:
    - OPENING: Build rapport, explore feelings, avoid advice
    - WORKING: Active intervention (CBT/grounding/coping)
    - CLOSING: Summarize progress, affirm strengths, plan next steps
    """
    from src.agents.prompts import (
        counseling_composer_OPENING_PHASE_PROMPT,
        counseling_composer_WORKING_PHASE_PROMPT,
        counseling_composer_CLOSING_PHASE_PROMPT
    )
    
    user_input = state['input']['userText']
    merged_context = state.get('contextPack', {}).get('mergedContext', '')
    phase_info = state.get('sessionPhase', {})
    
    current_phase = phase_info.get('current', 'opening')
    intervention_type = phase_info.get('interventionType', 'general_support')
    rapport_established = phase_info.get('rapportEstablished', False)
    goal_achieved = phase_info.get('goalAchieved', False)
    
    # Select phase-specific system prompt
    phase_system_prompts = {
        "opening": counseling_composer_OPENING_PHASE_PROMPT,
        "working": counseling_composer_WORKING_PHASE_PROMPT.format(
            intervention_type=intervention_type,
            rapport_established=rapport_established,
            merged_context=merged_context
        ),
        "closing": counseling_composer_CLOSING_PHASE_PROMPT.format(
            rapport_established=rapport_established,
            intervention_type=intervention_type,
            goal_achieved=goal_achieved
        )
    }
    
    system_prompt = phase_system_prompts.get(current_phase, counseling_composer_OPENING_PHASE_PROMPT)
    
    # Build user message
    user_message = f"User said: {user_input}\n\nGenerate your {current_phase} phase response."
    
    # Call LLM with phase-specific prompt
    result = llm.beta.chat.completions.parse(
        model=settings.GEMINI_MODEL,
        response_format=counselling_composer_node_Model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    )
    
    response = result.choices[0].message.parsed.finalText
    
    state["output"]["finalText"] = response
    
    print(f"\n{'='*80}")
    print(f"[CounselingComposer] Generated response for phase: {current_phase.upper()}")
    print(f"  Intervention: {intervention_type}")
    print(f"  Response length: {len(response)} chars")
    print(f"  Response: {state['output']['finalText']}")
    print(f"{'='*80}\n")
    
    return state


def crisis_override_node(state: GraphAState) -> GraphAState:
    """
    If needs_crisis=true (from RiskTriage or mid-turn signal),
    replaces normal content with a strict crisis/safety message and immediate actions.
    """

    user_input = state['input']['userText']

    result = llm.beta.chat.completions.parse(
        model=settings.GEMINI_MODEL,
        response_format=counselling_composer_node_Model,
        messages=[
            {"role" : "system", "content" : crisis_override_node_System_Prompt},
            {"role": "user", "content": user_input}
        ]
    )

    state["output"]["finalText"] = result.choices[0].message.parsed.finalText
    print("🤖 Crisis : ", state["output"]["finalText"])
    return state


def stream_out_node(state: GraphAState) -> GraphAState:
    """
    Emits streamable events:
      - fast_ack (immediate), then
      - final (after a 2s delay on the client side)
    fastAckText is cleared after enqueue to avoid re-sending.
    """
    events = state.get("output", {}).get("events", []) or []
    final_text = state.get("output", {}).get("finalText") or ""
    if final_text:
        events.append({"type": "final", "text": final_text, "delay_ms": 0})
    state["output"]["events"] = events
    return state


def checkpoint_and_trace_node(state: GraphAState) -> GraphAState:
    """
    1. Update recent turns in state (for phase detection)
    2. Save to mem0 (which auto-summarizes for long-term memory)
    3. Save checkpoint to MongoDB (only metadata, not full conversation)
    """
    
    user_id = state.get("userId")
    user_input = state.get("input", {}).get("userText", "")
    assistant_response = state.get("output", {}).get("finalText", "")
    
    # 1. Update recent turns (IN-MEMORY ONLY - not saved to DB)
    recent_turns = state.get("transcript", {}).get("recentTurns", [])
    
    recent_turns.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now(UTC).isoformat()
    })
    
    recent_turns.append({
        "role": "assistant",
        "content": assistant_response,
        "timestamp": datetime.now(UTC).isoformat()
    })
    
    # Keep only last 6 turns (ephemeral - lives in LangGraph state only)
    state["transcript"]["recentTurns"] = recent_turns[-6:]
    
    # 2. Save to mem0 - it handles summarization automatically
    if user_id and user_input and assistant_response:
        messages = [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": assistant_response}
        ]
        add_user_memory.invoke({"user_id": user_id, "messages": messages})
        print(f"[Checkpoint] Saved to mem0 (auto-summarized)")
    
    # 3. MongoDB checkpoint - ONLY METADATA (no full conversation)
    # state["checkpoint"]["route"] = state.get("routing", {}).get("route", [])
    # state["checkpoint"]["riskLevel"] = state.get("safety", {}).get("riskLevel", "low")
    # state["checkpoint"]["endedAt"] = datetime.utcnow().isoformat() + "Z"
    
    return state