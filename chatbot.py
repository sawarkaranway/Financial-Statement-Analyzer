# chatbot.py
import google.generativeai as genai
from typing import List, Dict, Optional
import json

# ============================================================
# CONFIGURATION
# ============================================================
def configure_gemini(api_key: str):
    """
    Configure the Google Generative AI SDK with the provided API key.
    Call this once at app startup.
    """
    genai.configure(api_key=api_key)


# ============================================================
# PROMPT BUILDER
# ============================================================
def _build_prompt(
    user_query: str,
    context: Optional[Dict] = None,
    chat_history: Optional[List[Dict]] = None,
    max_history_turns: int = 6
) -> str:
    """
    Build a structured prompt for Gemini.
    Includes:
    - A system instruction
    - Company financial context (ratios/KPIs)
    - Last few chat history turns
    - Current user query
    """
    system_instr = (
        "You are a precise, professional financial analyst chatbot. "
        "Use the provided company financial data (KPIs, ratios, and metrics) "
        "to analyze and answer the user's question factually. "
        "When possible, cite which metrics you used. "
        "If data is missing, clearly state that you don’t have enough data."
    )

    # Format chat history
    convo_text = ""
    if chat_history:
        truncated = chat_history[-(max_history_turns * 2):]
        for msg in truncated:
            role = "User" if msg.get("role") == "user" else "Assistant"
            convo_text += f"{role}: {msg.get('content', '')}\n"

    # Ensure context is structured
    if context:
        if isinstance(context, dict):
            context_str = json.dumps(context, indent=2)
        else:
            context_str = str(context)
    else:
        context_str = "No financial context provided."

    # Build final prompt
    prompt = (
        f"{system_instr}\n\n"
        f"---\n"
        f"📊 Company Financial Data (KPIs & Ratios):\n{context_str}\n"
        f"---\n\n"
        f"Conversation so far:\n{convo_text}\n"
        f"User: {user_query}\n"
        f"Assistant:"
    )
    return prompt


# ============================================================
# ASK GEMINI FUNCTION
# ============================================================
def ask_gemini(
    user_query: str,
    context: Optional[Dict] = None,
    chat_history: Optional[List[Dict]] = None,
    model_name: str = "gemini-2.0-flash"
) -> str:
    """
    Send the constructed prompt to Gemini and return its response.
    - user_query: current user question
    - context: structured financial data (dict or string)
    - chat_history: conversation memory (list of {role, content})
    """
    try:
        # Build the prompt
        prompt = _build_prompt(
            user_query=user_query,
            context=context,
            chat_history=chat_history
        )

        # Initialize model
        model = genai.GenerativeModel(model_name)

        # Generate response
        response = model.generate_content(prompt)

        # Extract text
        if hasattr(response, "text") and response.text:
            answer = response.text.strip()
        else:
            answer = "⚠️ No response received from Gemini."

        return answer

    except Exception as e:
        return f"⚠️ Error while communicating with Gemini: {str(e)}"
