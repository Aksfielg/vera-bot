# Vera-Bot 🤖 — AI Growth Manager for Local Merchants

> **MagicPin AI Challenge Submission** · Team: Risha Gupta · Model: Groq `llama-3.3-70b-versatile` + Gemini `2.0-flash` fallback

Vera-Bot is an intelligent, context-aware WhatsApp assistant that helps local merchants (salons, dentists, restaurants, gyms, and pharmacies) grow their businesses through automated, high-converting conversations. It acts as a hyper-personalized growth manager — analyzing real-time performance data and proactively reaching out to merchants with actionable insights.

---

## 🏆 Evaluation Results (Judge Simulator)

Scored across all **30 test pairs** using `llama-3.3-70b-versatile` as the LLM judge:

| Dimension | Avg Score |
|---|---|
| Specificity | 7 / 10 |
| Category Fit | 8 / 10 |
| Merchant Fit | 7 / 10 |
| Decision Quality | 6 / 10 |
| Engagement | 6 / 10 |
| **Overall Average** | **34 / 50 (68%) — GOOD** |

Top entries (T01, T02) scored **41/50 (82%) — EXCELLENT**.

---

## 🌟 Key Features

### 1. Triple-Layer LLM Architecture
| Layer | Provider | When Used |
|---|---|---|
| **Primary** | Groq `llama-3.3-70b-versatile` | All requests (high quota, fast) |
| **Fallback** | Gemini `gemini-2.0-flash` | When Groq hits rate limits (429) |
| **Emergency** | Rule-based composer | When both APIs are exhausted |

### 2. Hyper-Personalized Message Generation
- Pulls real-time merchant data: CTR vs peer median, review milestones, active catalog offers
- Uses psychological levers: *Loss Aversion*, *Social Proof*, *Effort Externalization*
- Adjusts tone per category — clinical for dentists, operator-to-operator for restaurants, coaching for gyms
- Generates Hindi-English code-mixed messages based on merchant language preferences

### 3. Multi-Turn Conversation Engine
- Stateful context tracking via in-memory `ContextStore`
- Intent detection: accept → action mode, reject → graceful exit, hostile → immediate end
- Auto-reply detection — identifies OOO/bot replies and exits without annoying the merchant
- Supports customer-facing messages (`send_as: merchant_on_behalf`)

### 4. Complete FastAPI Backend
| Endpoint | Method | Purpose |
|---|---|---|
| `/v1/context` | POST | Load merchant / category / trigger / customer context |
| `/v1/tick` | POST | Process triggers, generate proactive outbound messages |
| `/v1/reply` | POST | Handle incoming merchant replies, drive conversation |
| `/v1/healthz` | GET | Health check + loaded context counts |
| `/v1/metadata` | GET | Bot identity, model, capabilities |
| `/v1/teardown` | POST | Clear all state between judge test runs |

---

## 📂 Project Structure

```
vera-bot/
├── main.py                  # FastAPI server + all endpoint routing
├── compose.py               # LLM prompt engine + Groq/Gemini/rule-based generation
├── reply_handler.py         # Multi-turn conversation + intent routing
├── state.py                 # In-memory ContextStore (merchants, triggers, conversations)
├── utils.py                 # Auto-reply detection, intent transition utilities
├── load_dataset.py          # Loads dataset_bundle.json into the live server
├── dataset_bundle.json      # Full dataset: 5 categories, 50 merchants, 200 customers, 100 triggers
├── embedded_testpairs.json  # 30 test pairs with full embedded context
├── submission.jsonl         # Final 30/30 generated messages (challenge submission)
├── judge_simulator.py       # LLM-powered local evaluation harness (7 providers)
├── final_check.py           # Comprehensive system health + submission QA script
├── verify_all.py            # API connectivity + endpoint test suite
├── generate_submission.py   # Bulk generation script for all 30 test pairs
├── keepalive.py             # Render.com keepalive pinger
├── Procfile                 # Render/Railway deployment config
└── render.yaml              # Render.com infrastructure config
```

---

## 🛠️ Setup & Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
PORT=8000
```

### 3. Start the Server
```bash
python main.py
```

### 4. Load the Dataset
```bash
python load_dataset.py
```
This loads 355 contexts (5 categories + 50 merchants + 200 customers + 100 triggers) into the live server.

---

## 🧪 Testing & Evaluation

### Full System Health Check
```bash
python final_check.py
```
Verifies: API keys, Groq connectivity, compose() pipeline, 30 submission entries, all live endpoints.

### LLM Judge Simulator
```bash
python judge_simulator.py
```
Scores all 30 submission entries with the Groq LLM judge and prints dimension-by-dimension score bars.

**Supported scenarios** (set `TEST_SCENARIO` in the config section):
| Scenario | What it tests |
|---|---|
| `score_submission` | Scores all 30 `submission.jsonl` entries with LLM (default) |
| `all` | Runs warmup + auto_reply + intent + hostile scenarios |
| `phase2_short` | Pushes all contexts, calls tick, scores live actions |
| `full_evaluation` | Scores all trigger batches via tick |
| `warmup` | healthz + metadata + context push only |
| `auto_reply_hell` | Multi-turn auto-reply detection |
| `intent_transition` | YES→action routing test |
| `hostile` | Hostile message handling |

---

## 🚀 Deployment (Render.com)

1. Push to GitHub
2. Create new Web Service on [render.com](https://render.com)
3. Set environment variables: `GROQ_API_KEY`, `GEMINI_API_KEY`
4. Build command: `pip install -r requirements.txt`
5. Start command: `python main.py`

The `render.yaml` and `Procfile` are pre-configured for one-click deployment.

---

## 🧠 How It Works

```
Judge/Tick → POST /v1/tick
                │
                ▼
         ContextStore.get(trigger)
         ContextStore.get(merchant)
         ContextStore.get(category)
                │
                ▼
         compose_message()
          ├─ Try Groq (llama-3.3-70b-versatile)
          ├─ Fallback → Gemini (gemini-2.0-flash)
          └─ Emergency → compose_fallback() [rule-based]
                │
                ▼
         Structured JSON response
         { body, cta, send_as, template_params, rationale }
                │
                ▼
         POST /v1/reply (merchant responds)
                │
                ▼
         detect_auto_reply() → end if OOO detected
         detect_intent_transition() → route by intent
         handle_reply() → Groq/Gemini generates next turn
```

---

*Built for the MagicPin AI Challenge · May 2026*
