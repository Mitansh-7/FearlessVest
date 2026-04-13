"""
Fearlessvest - Backend API Server
Proxies both Groq (VERA chatbot) and Finnhub (live market data) requests.
API keys live ONLY in backend/.env — never in the frontend code.
"""

import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from dotenv import load_dotenv

# Load .env — both GROQ_API_KEY and FINNHUB_API_KEY live here
load_dotenv()

app = Flask(__name__)

# Allow requests from any local origin (file://, localhost)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ── Constants ────────────────────────────────────────────────────
GROQ_API_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL     = "llama-3.1-8b-instant"
FINNHUB_URL    = "https://finnhub.io/api/v1"

SYSTEM_PROMPT = """You are VERA, a highly advanced Quantitative Technical Market Analyst for the platform Fearlessvest.

Your Objective:
- Provide technical analysis, hypothetical trade setups, and trend predictions based on standard market indicators.
- When asked for a trade prediction, clearly output a hypothetical scenario including:
  1. Entry Zone
  2. Take Profit (TP) Targets
  3. Stop Loss (SL)
  4. Reasoning (RSI, MACD, Volume, Support/Resistance).
- Adopt a professional, analytical, and sharp trader persona.
- Format numbers cleanly. Use bolding (**text**) for key price levels and targets.
- ALWAYS include a brief, one-sentence disclaimer at the very end stating that this is an AI simulation and not actual financial advice.
- Keep your responses under 200 words. Be concise and actionable."""


# ════════════════════════════════════════════════════════════════
# CHAT ENDPOINT  (used by chatbot.html)
# ════════════════════════════════════════════════════════════════
@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Accepts: { "messages": [ {"role": "user", "content": "..."}, ... ] }
    Returns: { "reply": "...", "model": "..." }
    """
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return jsonify({"error": "GROQ_API_KEY not set in .env"}), 500

    body = request.get_json(silent=True)
    if not body or "messages" not in body:
        return jsonify({"error": "Request body must contain a 'messages' array"}), 400

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            *body["messages"],
        ],
        "temperature": 0.7,
        "max_tokens": 300,
    }

    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        reply = resp.json()["choices"][0]["message"]["content"]
        return jsonify({"reply": reply, "model": GROQ_MODEL})

    except requests.exceptions.HTTPError as e:
        return jsonify({"error": f"Groq error {e.response.status_code}: {e.response.text}"}), e.response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Network error: {str(e)}"}), 503


# ════════════════════════════════════════════════════════════════
# MARKET DATA ENDPOINTS  (used by market-today.html)
# ════════════════════════════════════════════════════════════════

def finnhub_get(path, params=None):
    """Internal helper — calls Finnhub with the server-side key."""
    key = os.getenv("FINNHUB_API_KEY", "")
    if not key:
        raise ValueError("FINNHUB_API_KEY not set in .env")
    p = params or {}
    p["token"] = key
    resp = requests.get(f"{FINNHUB_URL}{path}", params=p, timeout=10)
    resp.raise_for_status()
    return resp.json()


@app.route("/api/market/quote", methods=["GET"])
def market_quote():
    """
    Proxy a single Finnhub stock quote.
    Query param: symbol (e.g. RELIANCE.NS, ^NSEI)
    Returns Finnhub quote object: { c, d, dp, h, l, o, pc, t }
    """
    symbol = request.args.get("symbol", "").strip()
    if not symbol:
        return jsonify({"error": "symbol query param required"}), 400
    try:
        data = finnhub_get("/quote", {"symbol": symbol})
        return jsonify(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 500
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": f"Finnhub error {e.response.status_code}"}), e.response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Network error: {str(e)}"}), 503


@app.route("/api/market/batch", methods=["POST"])
def market_batch():
    """
    Fetch multiple quotes in one backend call to reduce frontend requests.
    Accepts: { "symbols": ["RELIANCE.NS", "TCS.NS", ...] }
    Returns: { "RELIANCE.NS": { c, d, dp, ... }, "TCS.NS": {...}, ... }
    """
    body = request.get_json(silent=True)
    if not body or "symbols" not in body:
        return jsonify({"error": "Body must contain 'symbols' array"}), 400

    symbols = body["symbols"][:20]  # cap at 20 to be safe
    results = {}

    for sym in symbols:
        try:
            results[sym] = finnhub_get("/quote", {"symbol": sym})
        except Exception as e:
            results[sym] = {"error": str(e), "c": 0, "d": 0, "dp": 0}

    return jsonify(results)


# ════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ════════════════════════════════════════════════════════════════
@app.route("/api/health", methods=["GET"])
def health():
    """Ping endpoint — frontend checks this to show backend status badge."""
    return jsonify({
        "status": "ok",
        "groq_configured":    bool(os.getenv("GROQ_API_KEY")),
        "finnhub_configured": bool(os.getenv("FINNHUB_API_KEY")),
    })


# ════════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    groq_ok    = bool(os.getenv("GROQ_API_KEY"))
    finnhub_ok = bool(os.getenv("FINNHUB_API_KEY"))
    print(f"\n  ✅  Fearlessvest backend running → http://localhost:{port}")
    print(f"  🤖  GROQ_API_KEY    : {'✓ configured' if groq_ok    else '✗ MISSING — set in .env'}")
    print(f"  📈  FINNHUB_API_KEY : {'✓ configured' if finnhub_ok else '✗ MISSING — set in .env'}\n")
    app.run(host="0.0.0.0", port=port, debug=False)