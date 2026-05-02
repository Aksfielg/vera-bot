import google.generativeai as genai
import json
import os
import sys

from dotenv import load_dotenv
load_dotenv()

from groq import Groq as GroqClient

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

genai.configure(api_key=GEMINI_API_KEY)
gemini_reply_model = genai.GenerativeModel("gemini-2.0-flash")

def _call_reply_llm(prompt: str) -> str:
    if GROQ_API_KEY:
        try:
            client = GroqClient(api_key=GROQ_API_KEY)
            chat = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.0,
                max_tokens=400
            )
            return chat.choices[0].message.content
        except Exception as e:
            if "429" not in str(e) and "rate" not in str(e).lower():
                raise
    response = gemini_reply_model.generate_content(prompt)
    return response.text

REPLY_SYSTEM_PROMPT = """You are Vera, responding to a merchant's WhatsApp reply.
Be concise. Hindi-English mix if merchant used Hindi.

INTENT ROUTING RULES (follow strictly):
- intent=accept or intent=join_intent → IMMEDIATELY start the action. Do NOT ask more qualifying questions. Draft/do the thing they agreed to.
- intent=reject → ONLY return action="end"
- intent=hostile → Stay polite, acknowledge, offer to follow up later, then end
- intent=question → Answer the specific question from context, then re-offer the CTA
- intent=neutral → Continue conversation naturally, re-anchor on the trigger

CONVERSATION RULES:
- turn_count >= 5 → return action="end" with warm closing
- If merchant hasn't replied in 3 turns → do NOT re-engage
- Never repeat the same message you already sent
- Never say "I hope this finds you well" or re-introduce yourself

OUTPUT: Return ONLY valid JSON:
{"action": "send", "body": "message", "cta": "binary_yes_stop or open_ended", "rationale": "why"}
OR: {"action": "wait", "wait_seconds": 1800, "rationale": "why"}  
OR: {"action": "end", "rationale": "why"}"""

def handle_reply(conv: dict, merchant: dict, trigger: dict, message: str, intent: str, store) -> dict:
    if intent == "reject":
        return {"action": "end", "rationale": "Merchant declined — preserving relationship by exiting gracefully"}
    if intent == "hostile":
        return {"action": "end", "rationale": "Hostile response detected — exiting to preserve merchant relationship"}
    if intent == "join_intent":
        return {
            "action": "send", 
            "body": f"Perfect! Abhi register karti hoon. {merchant.get('identity',{}).get('owner_first_name','Aapka')} ji, business ka naam aur address confirm kar sakte hain? 2 min mein sab ho jayega.", 
            "cta": "open_ended", 
            "rationale": "Join intent detected — routing immediately to onboarding action without further qualification"
        }
        
    turn = conv.get("turn_count", 1)
    if turn >= 5:
        return {"action": "end", "rationale": "Natural conversation conclusion after 5 turns"}
        
    history = conv.get("message_history", [])
    last_4 = history[-4:] if len(history) >= 4 else history
    history_str = "\n".join([f"{msg.get('role', 'unknown')}: {msg.get('message', '')}" for msg in last_4])
    
    merchant_name = merchant.get("identity", {}).get("owner_first_name", "")
    trigger_kind = trigger.get("kind", "")
    
    user_prompt = f"""Conversation history (last 4 turns):
{history_str}

Merchant just replied: "{message}"
Merchant first name: {merchant_name}
Detected intent: {intent}
Turn number: {turn}
Original trigger type: {trigger_kind}

Continue the conversation. If intent=accept: immediately draft/send the artifact they agreed to. Do not ask another qualifying question."""

    try:
        full_prompt = REPLY_SYSTEM_PROMPT + "\n\n" + user_prompt
        raw = _call_reply_llm(full_prompt).strip().strip("```json").strip("```").strip()
        
        if raw.startswith("```"):
            lines = raw.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw = "\n".join(lines).strip()
            
        return json.loads(raw)
    except Exception as e:
        print(f"Error in handle_reply: {e}", file=sys.stderr)
        return {"action": "send", "body": "Zaroor! Thoda aur detail share karein toh turant help kar sakti hoon. Chalega?", "cta": "open_ended", "rationale": "Fallback response to keep conversation flowing"}
