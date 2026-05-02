def detect_auto_reply(message: str, history: list) -> bool:
    msg_lower = message.lower()
    
    phrases = [
        "aapki jaankari ke liye bahut-bahut shukriya",
        "aapki madad ke liye shukriya",
        "main ek automated assistant hoon",
        "i am an automated assistant",
        "thank you for contacting",
        "your message has been received",
        "we will get back to you",
        "hi, thanks for reaching out. i'm currently unavailable",
        "shukria aapka contact karne ke liye",
        "aapki baat hamari team tak",
        "our customer care team will contact"
    ]
    if any(p in msg_lower for p in phrases):
        return True
        
    merchant_msgs = [m.get("message", "").strip() for m in history if m.get("role") != "vera" and m.get("role") != "bot"]
    if merchant_msgs and merchant_msgs[-1] == message.strip():
        return True
        
    if len(message) > 150 and ("automated" in msg_lower or "bot" in msg_lower):
        return True
        
    return False

def detect_intent_transition(message: str) -> str:
    msg_lower = message.lower().strip()
    
    join_phrases = [
        "mujhe magicpin judrna hai",
        "join karna hai",
        "i want to join magicpin",
        "magicpin mein register",
        "onboard karna hai",
        "sign up karna"
    ]
    if any(p in msg_lower for p in join_phrases):
        return "join_intent"
        
    accept_phrases = [
        "yes", "haan", "ha", "ok", "okay", "go ahead", "let's do it", "karo",
        "proceed", "done", "sure", "bilkul", "theek hai", "chalega", "agree",
        "please do", "yes please", "sounds good", "perfect", "confirm", "go",
        "bata do", "bhej do", "draft kar do"
    ]
    for p in accept_phrases:
        if msg_lower == p or msg_lower.startswith(p + " ") or msg_lower.startswith(p + ",") or msg_lower.startswith(p + "."):
            return "accept"
        if msg_lower.startswith(p):
            return "accept"
            
    reject_phrases = [
        "no", "nahi", "nope", "not interested", "stop", "mat karo", "band karo",
        "don't contact", "remove me", "unsubscribe", "baad mein", "not now"
    ]
    if any(p in msg_lower for p in reject_phrases):
        return "reject"
        
    hostile_phrases = [
        "spam", "bakwaas", "band kar", "chup", "harassment", "report"
    ]
    if any(p in msg_lower for p in hostile_phrases):
        return "hostile"
        
    if msg_lower.endswith("?"):
        return "question"
        
    question_starts = ["kya", "how", "what", "when", "why", "kaisa", "kab", "kaise"]
    if any(msg_lower.startswith(q) for q in question_starts):
        return "question"
        
    return "neutral"

if __name__ == "__main__":
    print(detect_auto_reply("Aapki jaankari ke liye bahut-bahut shukriya. Main aapki yeh sabhi baatein team tak pahuncha deti hoon.", []))
    print(detect_intent_transition("yes please go ahead"))
    print(detect_intent_transition("mujhe magicpin judrna hai"))
