import os
import uuid
import json
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from state import ContextStore
from compose import compose_message

import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    if os.path.exists("expanded"):
        print("Auto-loading dataset from expanded/ folder...")
        async def delayed_load():
            await asyncio.sleep(2)
            try:
                from load_dataset import load_all
                await asyncio.to_thread(load_all)
                print("Dataset loaded successfully")
            except Exception as e:
                print(f"Dataset load warning: {e}")
        asyncio.create_task(delayed_load())
    yield

app = FastAPI(lifespan=lifespan)
store = ContextStore()

@app.post("/v1/context")
async def handle_context(request: Request):
    try:
        body = await request.json()
    except:
        body = {}
    
    scope = body.get("scope")
    context_id = body.get("context_id")
    version = body.get("version", 1)
    payload = body.get("payload", {})
    
    if not scope or not context_id:
        return JSONResponse(status_code=400, content={"accepted": False, "reason": "invalid_scope"})
        
    current = store.get_version(context_id)
    if current is not None and current > version:
        return JSONResponse(status_code=409, content={"accepted": False, "reason": "stale_version", "current_version": current})
        
    store.upsert(scope, context_id, version, payload)
    
    return JSONResponse(content={
        "accepted": True, 
        "ack_id": f"ack_{uuid.uuid4().hex[:8]}", 
        "stored_at": datetime.now(timezone.utc).isoformat()
    })

@app.post("/v1/tick")
async def handle_tick(request: Request):
    try:
        body = await request.json()
    except:
        body = {}
        
    available_triggers = body.get("available_triggers", [])
    used_keys = store.get_used_suppression_keys()
    actions = []
    
    for trigger_id in available_triggers[:20]:
        try:
            trigger = store.get("trigger", trigger_id)
            if not trigger:
                continue
                
            merchant_id = trigger.get("merchant_id") or trigger.get("payload", {}).get("merchant_id")
            if not merchant_id:
                continue
                
            merchant = store.get("merchant", merchant_id)
            if not merchant:
                continue
                
            category_slug = merchant.get("category_slug", "")
            category = store.get("category", category_slug) or {}
            
            suppression_key = trigger.get("suppression_key", trigger_id)
            if suppression_key in used_keys:
                continue
                
            customer_id = trigger.get("customer_id") or trigger.get("payload", {}).get("customer_id")
            customer = store.get("customer", customer_id) if customer_id else None
            
            result = compose_message(category, merchant, trigger, customer)
            if result is None:
                continue
                
            conv_id = f"conv_{uuid.uuid4().hex[:8]}"
            store.mark_suppression_key(suppression_key)
            store.add_conversation(conv_id, merchant_id, customer_id, trigger_id)
            
            action = {
                "conversation_id": conv_id,
                "merchant_id": merchant_id,
                "customer_id": customer_id,
                "send_as": result.get("send_as"),
                "trigger_id": trigger_id,
                "template_name": result.get("template_name", ""),
                "template_params": result.get("template_params", {}),
                "body": result.get("body"),
                "cta": result.get("cta"),
                "suppression_key": suppression_key,
                "rationale": result.get("rationale")
            }
            actions.append(action)
            
            if len(actions) >= 20:
                break
        except Exception as e:
            print(f"Error processing trigger {trigger_id}: {e}")
            continue
            
    return JSONResponse(content={"actions": actions})

@app.post("/v1/reply")
async def handle_reply_endpoint(request: Request):
    try:
        body = await request.json()
    except:
        body = {}
        
    conversation_id = body.get("conversation_id")
    merchant_id = body.get("merchant_id")
    customer_id = body.get("customer_id")
    from_role = body.get("from_role")
    message = body.get("message", "")
    received_at = body.get("received_at")
    turn_number = body.get("turn_number", 0)
    
    conv = store.get_conversation(conversation_id)
    if not conv:
        return JSONResponse(content={"action": "end", "rationale": "Unknown conversation ID"})
        
    from utils import detect_auto_reply, detect_intent_transition
    
    history = conv.get("message_history", [])
    if detect_auto_reply(message, history):
        store.add_to_conversation(conversation_id, from_role, message)
        if turn_number >= 2:
            return JSONResponse(content={"action": "end", "rationale": "Auto-reply detected after 2 turns — exiting to preserve merchant relationship"})
        else:
            return JSONResponse(content={"action": "send", "body": "Samajh gayi. Kya aap directly ek minute de sakte hain? 2 min mein ho jayega.", "cta": "binary_yes_stop", "rationale": "Single probe after first auto-reply detection"})
            
    intent = detect_intent_transition(message)
    store.add_to_conversation(conversation_id, from_role, message)
    
    from reply_handler import handle_reply
    merchant = store.get("merchant", merchant_id) or {}
    trigger = store.get("trigger", conv.get("trigger_id")) or {}
    
    reply_result = handle_reply(conv, merchant, trigger, message, intent, store)
    return JSONResponse(content=reply_result)

@app.get("/v1/healthz")
async def handle_healthz():
    return JSONResponse(content={
        "status": "ok", 
        "contexts_loaded": store.count_all(), 
        "uptime_seconds": store.get_uptime(), 
        "version": "1.0.0", 
        "model": "gemini-2.0-flash"
    })

@app.get("/v1/metadata")
async def handle_metadata():
    return JSONResponse(content={
        "bot_name": "VeRA-Pro", 
        "version": "1.0.0", 
        "author": "Participant", 
        "model": "gemini-2.0-flash", 
        "capabilities": ["compose", "multi_turn", "auto_reply_detection", "intent_transition", "hindi_english_mix", "customer_facing"], 
        "supported_categories": ["dentists", "salons", "restaurants", "gyms", "pharmacies"], 
        "max_actions_per_tick": 20, 
        "timeout_ms": 25000
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
