# Fearlessvest 📈

A modern Indian stock market analysis platform with an AI chatbot (VERA), live market data, sandbox trading, and portfolio dashboard.

---

## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/FearlessVest.git
cd FearlessVest
```

### 2. Set up the backend (AI Chatbot)
```bash
cd backend
cp .env.example .env
```

Open `backend/.env` and add your free Groq API key:
```
GROQ_API_KEY=your_key_here
```
> Get a free key at: https://console.groq.com/keys

### 3. Start the backend (Windows)
Double-click **`start_backend.bat`** — it will:
- Create a Python virtual environment
- Install all dependencies
- Start the Flask server at `http://localhost:5000`

Or manually:
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### 4. Open the app
Open any `.html` file directly in your browser — no build step needed.
- `index.html` — Home
- `chatbot.html` — AI Analyst (requires backend running)
- `market-today.html` — Live Market Data
- `dashboard.html` — Portfolio Dashboard
- `sandbox.html` — Paper Trading
- `analysis.html` — Technical Analysis

---

## 🏗️ Architecture

```
FearlessVest/
├── index.html              # Landing page
├── chatbot.html            # AI Chatbot (calls backend)
├── market-today.html       # Live market data (Finnhub + TradingView)
├── dashboard.html          # Portfolio dashboard
├── sandbox.html            # Paper trading
├── analysis.html           # Technical analysis
├── start_backend.bat       # One-click Windows launcher
├── .gitignore
│
└── backend/
    ├── app.py              # Flask API server
    ├── requirements.txt    # Python dependencies
    ├── .env.example        # Template — copy to .env
    └── .env                # ⚠️ YOUR SECRETS — never committed
```

## 🔐 Security

| What | Where | In Git? |
|---|---|---|
| Groq API Key | `backend/.env` | ❌ **No** (gitignored) |
| Frontend code | `*.html` | ✅ Yes — no secrets here |
| Finnhub key | User's browser `localStorage` | ❌ No |

The API key is **never** in the frontend code or git history.

---

## 🛠️ Backend API

| Endpoint | Method | Description |
|---|---|---|
| `/api/chat` | POST | Send messages to VERA AI |
| `/api/health` | GET | Check if backend is running |

**Chat request:**
```json
POST /api/chat
{ "messages": [{"role": "user", "content": "Analyze RELIANCE"}] }
```
**Chat response:**
```json
{ "reply": "VERA's analysis...", "model": "llama-3.1-8b-instant" }
```

---

## 📦 Dependencies

**Backend (Python):**
- Flask, Flask-CORS, requests, python-dotenv

**Frontend:**
- TailwindCSS CDN, Font Awesome, Google Fonts
- TradingView Widgets (market data)
- Finnhub API (stock quotes — user provides key)

---

## ⚠️ Disclaimer
This platform is for **educational purposes only**. All AI-generated trade setups are simulated and do **not** constitute financial advice.