import google.generativeai as genai
import json
import os
import sys
import time

from dotenv import load_dotenv
load_dotenv()

# Try Groq first (higher free quota), fall back to Gemini
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

def _call_llm(prompt: str) -> str:
    # Try Groq first
    if GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            chat = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.0,
                max_tokens=600
            )
            return chat.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                pass  # fall through to Gemini
            else:
                raise
    # Fall back to Gemini
    response = gemini_model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(temperature=0.0)
    )
    return response.text

SYSTEM_PROMPT = """You are Vera, magicpin's AI assistant for merchant growth. You compose WhatsApp messages for Indian merchants.

SCORING DIMENSIONS (each 0-10, total 50 — optimize ALL five):
1. Specificity: anchor on ONE verifiable fact (number, percentage, date, source citation, price)
2. Category fit: match tone and vocabulary to the merchant's business type exactly
3. Merchant fit: use owner's name, their real numbers, their actual offers, their language preference
4. Trigger relevance: clearly communicate WHY this message is sent RIGHT NOW
5. Engagement compulsion: one compelling reason to reply NOW using exactly ONE of these levers:
   - Specificity lever: "6,777 missed searches in Sector 14 this week"
   - Loss aversion: "you're losing X to competitors"
   - Social proof: "3 clinics in your area already did this"
   - Effort externalization: "I've already drafted it — just say go"
   - Curiosity: "want to see the full breakdown?"
   - Reciprocity: "noticed this in your data, thought you'd want to know"

CATEGORY VOICE RULES (follow strictly):
- dentists: peer/clinical tone. Use: "fluoride varnish", "caries", "JIDA", "recall", "CTR". NEVER: "guaranteed", "100% safe", "miracle", "best in city", "AMAZING". No emoji.
- salons: warm-practical. Use service names + prices. 1-2 emojis OK (💍🌟). Bridal: countdown days.
- restaurants: operator-to-operator. Use: "covers", "AOV", "delivery radius", "BOGO". Emoji ok for food 🍕.
- gyms: coach voice. Reframe dips as normal. Use: "member count", "retention", "conversion window". 
- pharmacies: compliance-first, trustworthy. Use molecule names. Namaste for seniors. Never alarming.

HARD RULES (violating any = low score):
- NEVER invent numbers, citations, competitor names, or offers not in the context
- ONE CTA only, placed at the END of the message
- Binary CTA (Reply YES / Reply STOP) for action triggers
- Open-ended CTA (question) for information triggers
- NO preamble: "Hope you're well", "I'm reaching out", "Dear Merchant" — start with the HOOK
- NO re-introducing yourself after the first message in a conversation
- Hindi-English code-mix REQUIRED when merchant languages includes "hi"
- If customer scope: send_as must be "merchant_on_behalf", use customer's name, customer's language preference

OUTPUT FORMAT: Return ONLY valid JSON, no markdown, no explanation:
{
  "body": "the complete WhatsApp message text",
  "cta": "binary_yes_stop" or "open_ended" or "none",
  "send_as": "vera" or "merchant_on_behalf",
  "suppression_key": "category:trigger_kind:merchant_id:week",
  "rationale": "2 sentences: which signal you picked and why, which compulsion lever and why"
}"""

TRIGGER_STYLES = {
    "research_digest": "Lead with journal name + specific finding. Include: trial size (n=X), percentage improvement, source citation (Journal Month Year page). Mention the specific merchant patient/customer cohort that benefits. Offer to pull abstract + draft content they can share. CTA: open_ended",
    "recall_due": "This is CUSTOMER-FACING (send_as: merchant_on_behalf). Include: months since last visit, specific recall reason (6-month cleaning, annual eye check). List 2 real available slots with day+date+time. Include real catalog price. Add a free-add if in catalog. Language: match customer's preference. 1-2 emojis. CTA: multi-choice slot selection (Reply 1 or 2)",
    "perf_spike": "Lead with the exact percentage improvement. Compare to peer benchmark. Identify what likely caused it (from context signals). Propose ONE action to capitalize on momentum. CTA: binary_yes_stop",
    "perf_dip": "Do NOT lead with negative framing. Reframe: 'your numbers dipped X% — here is one fix'. Compare to peer median. Give exact drop percentage. Reference the specific signal causing it (stale posts, low CTR). Propose one concrete action. CTA: binary_yes_stop",
    "festival_upcoming": "Name the festival. Count days remaining. Reference what merchants in this category do for this festival. Reference the merchant's existing active offer. Offer to create campaign. CTA: binary_yes_stop",
    "dormant_with_vera": "Do NOT mention 'dormant' or 'inactive'. Frame as catching-up. Reference something positive from their profile (their rating, recent reviews). Ask a curious question about their business. CTA: open_ended",
    "curious_ask_due": "Ask ONE specific question about their business this week. Offer to immediately turn their answer into a useful output (Google post, WhatsApp reply template, performance insight). Keep it under 3 sentences. CTA: open_ended question",
    "milestone_reached": "Celebrate the exact number. Compare to peer benchmark (above/below/at). Suggest the logical next milestone. Keep it warm and brief. CTA: binary_yes_stop",
    "review_theme_emerged": "Name the review theme (positive or negative). Count occurrences. If negative: offer one fix. If positive: offer to amplify it in Google posts. CTA: binary_yes_stop",
    "bridal_followup": "CUSTOMER-FACING. Count exact days to wedding date. Reference the trial they had. Reference the specific bridal program with price. Mention their preferred slot time. CTA: binary slot commit",
    "ipl_match_today": "Add INSIGHT beyond just 'IPL today'. Check if weekend vs weekday (Saturday IPL = -12% restaurant covers). Give counter-intuitive recommendation if needed. Reference existing offers. Offer to create assets (banner + story). CTA: binary_yes_stop",
    "active_planning_intent": "Merchant explicitly said yes to something. Draft the ARTIFACT they asked about (pricing, package, message template). Do NOT ask more qualifying questions. Show the draft, ask if they want it sent. CTA: binary_yes_stop",
    "customer_lapsed_hard": "CUSTOMER-FACING. No shame/guilt framing. Use 'no judgment' framing. Reference their past goal/service. Offer a specific new class/service that matches their goal. Offer free trial slot with specific date+time. CTA: binary_yes_stop",
    "supply_alert": "Urgent tone but bounded risk ('sub-potency, no safety risk'). Name exact batch numbers. Derive count of affected customers from merchant's customer aggregate. Offer complete workflow (patient note + replacement process). CTA: binary_yes_stop",
    "chronic_refill_due": "CUSTOMER-FACING. Name exact medications. State run-out date. Confirm same dose/brand. Calculate total with discount applied. Show savings amount. Mention delivery time. Two response options (reply OR call). CTA: Reply CONFIRM",
    "generic": "Pick the SINGLE most actionable signal from merchant signals list. Anchor on one specific number. Use curiosity or loss aversion as compulsion lever. CTA: open_ended"
}

def build_user_prompt(category, merchant, trigger, customer, style_instruction) -> str:
    parts = []
    
    parts.append("--- MERCHANT ---")
    identity = merchant.get("identity", {})
    parts.append(f"Identity: Name={identity.get('name')}, Owner={identity.get('owner_first_name')}, City={identity.get('city')}, Locality={identity.get('locality')}, Languages={identity.get('languages')}, Verified={identity.get('verified')}")
    
    subscription = merchant.get("subscription", {})
    parts.append(f"Subscription: Status={subscription.get('status')}, DaysRemaining={subscription.get('days_remaining')}, Plan={subscription.get('plan')}")
    
    perf = merchant.get("performance", {})
    parts.append(f"Performance: Views={perf.get('views')}, Calls={perf.get('calls')}, Directions={perf.get('directions')}, CTR={perf.get('ctr')}, Leads_30d={perf.get('leads')}, Delta_7d={perf.get('delta_7d')}")
    
    offers = merchant.get("offers", [])[:4]
    parts.append(f"Offers: {json.dumps(offers, ensure_ascii=False)}")
    
    cust_agg = merchant.get("customer_aggregate", {})
    parts.append(f"Customer Aggregate: {json.dumps(cust_agg, ensure_ascii=False)}")
    
    signals = merchant.get("signals", [])
    parts.append(f"Signals: {json.dumps(signals, ensure_ascii=False)}")
    
    history = merchant.get("conversation_history", [])[:3]
    parts.append(f"Conversation History: {json.dumps(history, ensure_ascii=False)}")
    
    review_themes = merchant.get("review_themes", [])[:2]
    parts.append(f"Review Themes: {json.dumps(review_themes, ensure_ascii=False)}")
    
    parts.append("\n--- CATEGORY ---")
    parts.append(f"Slug: {category.get('slug')}")
    voice = category.get("voice", {})
    parts.append(f"Voice: Tone={voice.get('tone')}, CodeMix={voice.get('code_mix')}, Taboo={voice.get('vocab_taboo')}")
    peer_stats = category.get("peer_stats", {})
    parts.append(f"Peer Stats: {json.dumps(peer_stats, ensure_ascii=False)}")
    digest = category.get("digest", [])[:2]
    parts.append(f"Digest: {json.dumps(digest, ensure_ascii=False)}")
    beats = category.get("seasonal_beats", [])[:2]
    parts.append(f"Seasonal Beats: {json.dumps(beats, ensure_ascii=False)}")
    
    parts.append("\n--- TRIGGER ---")
    parts.append(f"Kind: {trigger.get('kind')}, Urgency={trigger.get('urgency')}, SuppressionKey={trigger.get('suppression_key')}, ExpiresAt={trigger.get('expires_at')}")
    payload = trigger.get("payload", {})
    parts.append(f"Payload: {json.dumps(payload, ensure_ascii=False)}")
    
    if customer:
        parts.append("\n--- CUSTOMER ---")
        c_ident = customer.get("identity", {})
        parts.append(f"Identity: Name={c_ident.get('name')}, LanguagePref={c_ident.get('language_pref')}")
        rel = customer.get("relationship", {})
        parts.append(f"Relationship: LastVisit={rel.get('last_visit')}, VisitsTotal={rel.get('visits_total')}, Services={rel.get('services_received')}")
        parts.append(f"State: {customer.get('state')}")
        prefs = customer.get("preferences", {})
        parts.append(f"Preferences: {json.dumps(prefs, ensure_ascii=False)}")
        consent = customer.get("consent", {})
        parts.append(f"Consent Scope: {consent.get('scope')}")
        
    parts.append("\n--- COMPOSITION STYLE FOR THIS TRIGGER: ---")
    parts.append(style_instruction)
    
    parts.append("\nReturn ONLY valid JSON. No markdown.")
    
    return "\n".join(parts)

def compose_fallback(category: dict, merchant: dict, trigger: dict, customer: dict | None) -> dict:
    """Rule-based composer — fires when Gemini quota is exhausted."""
    import random
    
    identity = merchant.get("identity", {})
    perf = merchant.get("performance", {})
    offers = merchant.get("offers", [])
    signals = merchant.get("signals", [])
    cat_slug = merchant.get("category_slug", "")
    trigger_kind = trigger.get("kind", "generic")
    owner = identity.get("owner_first_name", "")
    languages = identity.get("languages", ["en"])
    use_hindi = "hi" in languages
    
    # Pick best offer
    active_offer = next((o["title"] for o in offers if o.get("status") == "active"), None)
    if not active_offer and offers:
        active_offer = offers[0].get("title", "")
    
    # Real numbers from context
    ctr = perf.get("ctr", 0)
    views = perf.get("views", 0)
    calls = perf.get("calls", 0)
    peer_ctr = category.get("peer_stats", {}).get("avg_ctr", 0.03)
    delta_calls = perf.get("delta_7d", {}).get("calls_pct", 0)
    
    # Customer context
    cust_name = customer.get("identity", {}).get("name", "") if customer else ""
    cust_lang = customer.get("identity", {}).get("language_pref", "en") if customer else "en"
    
    # Trigger payload
    payload = trigger.get("payload", {})
    
    # Build message by trigger kind
    if trigger_kind == "recall_due" and customer:
        slots = payload.get("available_slots", [])
        slot_str = slots[0].get("label", "this week") if slots else "this week"
        service = payload.get("service_due", "checkup").replace("_", " ")
        price_offer = active_offer or "special price"
        body = f"Hi {cust_name}! {identity.get('name','your clinic')} se — aapka {service} due hai. Slot available: {slot_str}. {price_offer}. Reply 1 to confirm?"
        return {"body": body, "cta": "open_ended", "send_as": "merchant_on_behalf",
                "suppression_key": f"recall:{cat_slug}:{merchant.get('merchant_id','')}:{cust_name}",
                "rationale": f"Fallback recall: {cust_name} due for {service}, slot {slot_str}"}
    
    elif trigger_kind in ("perf_dip", "perf_spike"):
        direction = "upar" if delta_calls >= 0 else "neeche"
        pct = abs(round(delta_calls * 100))
        vs_peer = "above" if ctr > peer_ctr else "below"
        fix = f"ek offer add karo" if not active_offer else f"{active_offer} ko boost karo"
        if use_hindi:
            body = f"{owner}, calls this week {pct}% {direction} aayi. CTR {ctr:.1%} hai — peer median {peer_ctr:.1%} se {vs_peer}. {fix} toh views convert honge. Kya main draft karoon?"
        else:
            body = f"{owner}, calls moved {pct}% this week. CTR {ctr:.1%} vs peer {peer_ctr:.1%}. Let me draft a quick fix — shall I?"
        return {"body": body, "cta": "binary_yes_stop", "send_as": "vera",
                "suppression_key": f"{trigger_kind}:{cat_slug}:{merchant.get('merchant_id','')}",
                "rationale": f"Fallback perf message using real CTR {ctr:.1%} vs peer {peer_ctr:.1%}"}
    
    elif trigger_kind == "research_digest":
        digest = category.get("digest", [{}])[0]
        title = digest.get("title", "new research")
        source = digest.get("source", "industry journal")
        n = digest.get("trial_n", "")
        n_str = f" (n={n})" if n else ""
        body = f"{owner}, {source} mein {title}{n_str} — aapke patients ke liye relevant hai. Kya main patient-friendly summary draft karoon?"
        return {"body": body, "cta": "open_ended", "send_as": "vera",
                "suppression_key": f"research:{cat_slug}:{merchant.get('merchant_id','')}",
                "rationale": f"Fallback research digest using {source} finding"}
    
    elif trigger_kind == "milestone_reached":
        metric = payload.get("metric", "milestone")
        value = payload.get("value_now", views)
        target = payload.get("milestone_value", "")
        target_str = f"/{target}" if target else ""
        body = f"{owner}, {metric} {value}{target_str} tak pahunch gaya — great milestone! CTR {ctr:.1%} hai. Isko ek Google post se celebrate karte hain? Main draft karta hoon abhi."
        return {"body": body, "cta": "binary_yes_stop", "send_as": "vera",
                "suppression_key": f"milestone:{cat_slug}:{merchant.get('merchant_id','')}:{metric}",
                "rationale": f"Fallback milestone using real metric {metric}={value}"}
    
    elif trigger_kind == "festival_upcoming":
        festival = payload.get("festival_name", "upcoming festival")
        days = payload.get("days_until", "")
        days_str = f" — {days} days left" if days else ""
        offer_str = f"with {active_offer}" if active_offer else "with a special offer"
        body = f"{owner}, {festival}{days_str}! {cat_slug.title()} peers already running campaigns {offer_str}. Kya main aapka campaign draft karoon? Reply YES."
        return {"body": body, "cta": "binary_yes_stop", "send_as": "vera",
                "suppression_key": f"festival:{cat_slug}:{merchant.get('merchant_id','')}:{festival}",
                "rationale": f"Fallback festival trigger for {festival}"}
    
    else:
        # Generic fallback — always has a number
        top_signal = signals[0] if signals else "engagement_opportunity"
        offer_str = f" {active_offer} available." if active_offer else ""
        body = f"{owner}, {views} views this month with CTR {ctr:.1%} vs peer {peer_ctr:.1%}.{offer_str} Ek quick action se yeh convert ho sakta hai — kya main draft karoon?"
        return {"body": body, "cta": "binary_yes_stop", "send_as": "vera",
                "suppression_key": f"generic:{cat_slug}:{merchant.get('merchant_id','')}",
                "rationale": f"Fallback generic using real views={views}, CTR={ctr:.1%}"}

def compose_message(category: dict, merchant: dict, trigger: dict, customer: dict | None = None) -> dict | None:
    trigger_kind = trigger.get("kind", "generic")
    style = TRIGGER_STYLES.get(trigger_kind, TRIGGER_STYLES["generic"])
    user_prompt = build_user_prompt(category, merchant, trigger, customer, style)
    full_prompt = SYSTEM_PROMPT + "\n\n" + user_prompt

    for attempt in range(3):  # retry up to 3 times
        try:
            raw = _call_llm(full_prompt).strip()
            # Strip markdown if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()
            result = json.loads(raw)
            
            # Sanitize CTA — Gemini sometimes returns a sentence instead of the enum value
            valid_ctas = {"binary_yes_stop", "open_ended", "none"}
            cta = result.get("cta", "open_ended")
            if cta not in valid_ctas:
                # Auto-detect: if it contains "yes" or "stop" → binary, else → open_ended
                cta_lower = cta.lower()
                if "yes" in cta_lower or "stop" in cta_lower or "binary" in cta_lower:
                    result["cta"] = "binary_yes_stop"
                else:
                    result["cta"] = "open_ended"
            
            return result

        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower() or "rate limit" in err.lower():
                # Extract retry delay from error message if present
                wait = 25  # default wait
                import re
                match = re.search(r'retry in (\d+)', err)
                if match:
                    wait = int(match.group(1)) + 3  # add 3s buffer
                print(f"\n  [Rate limit] Waiting {wait}s before retry (attempt {attempt+1}/3)...", flush=True)
                time.sleep(wait)
                continue  # retry
            else:
                print(f"Error in compose_message: {e}", file=sys.stderr)
                return None

    print("compose_message: Gemini quota exhausted — using rule-based fallback", file=__import__('sys').stderr)
    return compose_fallback(category, merchant, trigger, customer)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    test_category = {"slug": "dentists", "voice": {"tone": "peer_clinical", "code_mix": "hindi_english_natural", "vocab_taboo": ["guaranteed"]}, "peer_stats": {"avg_ctr": 0.030}, "digest": [{"title": "3-month fluoride recall cuts caries 38%", "source": "JIDA Oct 2026 p.14", "trial_n": 2100}]}
    test_merchant = {"merchant_id": "m_001", "category_slug": "dentists", "identity": {"name": "Dr. Meera Dental", "owner_first_name": "Meera", "city": "Delhi", "languages": ["en", "hi"]}, "performance": {"ctr": 0.021, "views": 2410}, "offers": [{"title": "Dental Cleaning @ ₹299", "status": "active"}], "signals": ["ctr_below_peer_median"], "customer_aggregate": {"high_risk_adult_count": 124}}
    test_trigger = {"kind": "research_digest", "urgency": 2, "suppression_key": "research:dentists:2026-W17", "payload": {"merchant_id": "m_001", "top_item": {"title": "3-month fluoride recall", "source": "JIDA Oct 2026 p.14", "trial_n": 2100}}}
    
    result = compose_message(test_category, test_merchant, test_trigger)
    print(json.dumps(result, indent=2, ensure_ascii=False))
