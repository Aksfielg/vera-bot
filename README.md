# Vera-Bot: AI Assistant for Merchant Growth 🚀

Vera-Bot is an intelligent, context-aware AI assistant designed to help local merchants (salons, dentists, restaurants, gyms, and pharmacies) grow their businesses through automated, high-converting WhatsApp conversations. 

Built for the MagicPin AI Challenge, this system acts as a hyper-personalized growth manager, analyzing real-time performance metrics and suggesting actionable campaigns to merchants.

## 🌟 Key Features

1. **Dual-LLM Architecture (Groq + Gemini)**
   - **Primary Engine**: Powered by Groq (`llama-3.3-70b-versatile`) for lightning-fast inference and high rate limits.
   - **Smart Fallback**: Automatically falls back to Google's `gemini-2.0-flash` if Groq encounters errors or rate limits.
   - **Rule-Based Fallback**: An additional, fully offline rule-based generation layer guarantees the bot never fails to deliver a message, even if all API quotas are completely exhausted.

2. **Hyper-Personalized Generation**
   - Incorporates real-time merchant data: CTR vs. peer median, recent review milestones, active catalog offers, and customer aggregates.
   - Uses psychological levers like *Loss Aversion*, *Social Proof*, and *Effort Externalization* to maximize merchant conversion.
   - Adjusts voice and tone per category (e.g., clinical tone for dentists, operator-to-operator tone for restaurants).
   - Generates code-mixed Hindi-English messages for relevant merchants based on their preferences.

3. **Multi-Turn Conversation Engine**
   - Stateful context tracking via an in-memory `ContextStore`.
   - Automatically detects intents (accept, reject, hostile, question) and routes the conversation appropriately.
   - Capable of identifying auto-replies and gracefully exiting without annoying the merchant.

4. **FastAPI Backend Services**
   - **`/v1/context`**: Load and update merchant, customer, and trigger contexts.
   - **`/v1/tick`**: Process triggers and generate proactive outbound messages.
   - **`/v1/reply`**: Handle incoming merchant replies and manage the ongoing conversation.

## 📂 Project Structure

- `main.py`: The FastAPI application server and endpoint routing.
- `compose.py`: The core LLM prompt engineering, Groq/Gemini generation logic, and rule-based fallback system.
- `reply_handler.py`: LLM logic for handling and responding to merchant replies in an active conversation.
- `state.py`: In-memory datastore managing merchants, triggers, categories, and conversation history.
- `load_dataset.py`: Utility to parse and load the `dataset_bundle.json` into the context store.
- `generate_remaining.py` / `generate_submission.py`: Scripts used to evaluate the bot against the 30-pair test dataset and output to `submission.jsonl`.
- `verify_all.py` / `final_check.py`: Comprehensive test suites verifying APIs, endpoints, and the final submission output.

## 🛠️ Setup & Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key
   GEMINI_API_KEY=your_gemini_api_key
   PORT=8000
   ```

3. **Run the Server**:
   ```bash
   python main.py
   ```

## 📊 Evaluation & Testing

The bot has been rigorously evaluated against a 30-pair test dataset. You can verify the outputs and system health by running the final check script:

```bash
python final_check.py
```

This will:
- Verify both Groq and Gemini API connections.
- Test the dynamic generation pipeline across different trigger types.
- Validate the schema and quality of all 30 entries in `submission.jsonl`.
- Perform live endpoint tests against the running FastAPI server.

---
*Built for the MagicPin AI Challenge.*
