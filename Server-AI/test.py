from src.agents.graph import app_graph
from src.agents.state import GraphAState
from datetime import datetime
import uuid
import asyncio

async def interactive_test():
    """
    Interactive terminal testing - keeps same session, just change user input
    """
    session_id = f"interactive_session_{uuid.uuid4()}"
    session_start_time = datetime.now()
    
    print("🧠 MindGuard Graph Testing")
    print("Type 'quit' to exit\n")
    
    while True:
        user_text = input("User: ")
        
        if user_text.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not user_text.strip():
            continue
        
        initial_state: GraphAState = {
            "userId": "interactive_user",
            "sessionId": session_id,
            "input": {
                "userText": user_text,
                "locale": "en-US",
                "channel": "web",
                "topK": 8,
                
                "now": datetime.now().isoformat() + "Z"
            },
            "transcript": {"recentTurns": []},
            "trace": {
                "traceId": str(uuid.uuid4()),
                "sessionSpanId": str(uuid.uuid4())
            },
            "safety": {
                "riskLevel": "low", 
                "needsCrisis": False, 
                "flags": []
            },
            "routing": {
                "route": [], 
                "retrievalNeeded": False,
                "fanoutQueries": [],
                # NEW: Closure detection fields
                "suggestClosure": False,
                "closureReasons": [],
                "closureSignalStrength": 0,
                "awaitingClosureConfirmation": False
            },
            "rag": {"docs": []},
            "kg": {"facts": []},
            "memory": {"items": []},
            "contextPack": {
                "mergedContext": "", 
                "sourcesMeta": []
            },
            # NEW: Session phase tracking
            
            "output": {
                "fastAckText": "",
                "finalText": "",
                "safetyOverride": False,
                "events": [],
                # NEW: Closure and reporting
                "closureText": "",
                "sessionReport": "",
                "reportSources": []
            },
            "streaming": {
                "started": False, 
                "tokensSent": 0
            },
            "checkpoint": {
                "route": [],
                "riskLevel": "low",
                "usedRag": False,
                "usedMem": False,
                "endedAt": ""
            }
        }
        
        config = {"configurable": {"thread_id": session_id}}
        
        try:
            result = await app_graph.ainvoke(initial_state, config)
            
            # Extract response
            final_text = result.get('output', {}).get('finalText', '')
            fast_ack = result.get('output', {}).get('fastAckText', '')
            closure_text = result.get('output', {}).get('closureText', '')
            session_report = result.get('output', {}).get('sessionReport', '')
            
            # Display response (prioritize closure/report if session ended)
            if session_report:
                print(f"\n📄 SESSION REPORT:\n{session_report}\n")
            elif closure_text:
                print(f"\n🤖 Assistant: {closure_text}")
            elif final_text:
                print(f"\n🤖 Assistant: {final_text}")
            elif fast_ack:
                print(f"\n🤖 Assistant (Fast): {fast_ack}")
            
            # Display session metadata
            phase = result.get('sessionPhase', {})
            print(f"\n📊 Session Phase: {phase.get('current', 'unknown').upper()}")
            print(f"⏱️  Duration: {phase.get('totalDuration', 0):.1f} min")
            print(f"🔄 Turns: Opening={phase.get('openingTurns', 0)}, Working={phase.get('workingTurns', 0)}, Closing={phase.get('closingTurns', 0)}")
            print(f"🎯 Risk: {result.get('safety', {}).get('riskLevel')} | Route: {result.get('routing', {}).get('route')}")
            
            # Display flags if any
            if result.get('safety', {}).get('flags'):
                print(f"⚠️  Flags: {', '.join(result.get('safety', {}).get('flags'))}")
            
            # Display closure signals if detected
            if result.get('routing', {}).get('suggestClosure'):
                print(f"🚪 Closure Suggested: {', '.join(result.get('routing', {}).get('closureReasons', []))}")
            
            # Display memory/RAG usage
            rag_count = len(result.get('rag', {}).get('docs', []))
            mem_count = len(result.get('memory', {}).get('items', []))
            print(f"🧠 Context: {rag_count} docs, {mem_count} memories")
            
            print()
            
        except Exception as e:
            print(f"❌ Error: {e}\n")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(interactive_test())