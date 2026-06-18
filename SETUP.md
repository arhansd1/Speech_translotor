# Sarvam Voice Translator — Setup Guide (for Cursor)

This document is written to be pasted into Cursor as a build/setup reference. It assumes the full project zip (`sarvam-voice-translator.zip`) has already been extracted into your workspace. Follow every step in order — don't skip ahead.

---

## 0. Prerequisites — install these first

| Tool | Minimum version | Check with |
|---|---|---|
| Python | 3.11+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | any recent | `git --version` |

If any are missing, install them before continuing. On macOS, `brew install python node git` covers all three.

---

## 1. Open the project in Cursor

```bash
cd sarvam-voice-translator
cursor .
```

You should see two top-level folders: `backend/` (FastAPI + LangGraph) and `frontend/` (Next.js).

---

## 2. Get your Sarvam API key

1. Go to `https://dashboard.sarvam.ai`
2. Sign up — no credit card required
3. You receive ₹100 free credit (roughly 20+ full demo sessions at ₹3–5 each)
4. Copy the API key from the dashboard — you'll need it in Step 4

---

## 3. Backend — virtual environment and dependencies

In Cursor's integrated terminal:

```bash
cd backend
python3 -m venv venv
```

Activate it:
```bash
# macOS / Linux
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

Your terminal prompt should now show `(venv)` at the start. Install dependencies:

```bash
pip install -r requirements.txt
```

This installs FastAPI, LangGraph, LangSmith, httpx, sacrebleu, and everything else listed in `requirements.txt`. It should take 30–60 seconds with no errors.

---

## 4. Backend — environment variables

```bash
cp .env.example .env
```

Open the new `.env` file in Cursor and fill in:

```bash
SARVAM_API_KEY=paste_your_real_key_here
```

Leave `LANGCHAIN_API_KEY` blank for now — that's optional and covered in Step 8. Leave `FRONTEND_URL` and `PORT` as-is for local development.

**Important:** `.env` is already in `.gitignore` — it will never be committed. Never paste your real key into any file that isn't `.env`.

---

## 5. Frontend — dependencies

Open a **second terminal tab** in Cursor (keep the backend terminal as-is):

```bash
cd frontend
npm install
```

This installs Next.js 14.2.35 (a patched version — do not downgrade, earlier 14.x versions have a known RCE vulnerability), React, Tailwind, and TypeScript tooling. Takes 15–30 seconds.

---

## 6. Frontend — environment variables

```bash
cp .env.local.example .env.local
```

Open `.env.local` and confirm it says:

```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

This is correct for local development — leave it as-is. You'll only change this after deploying the backend (covered in Step 9).

---

## 7. Verify project structure

Your folder tree should now look like this:

```
sarvam-voice-translator/
├── backend/
│   ├── venv/                  ← created in Step 3 (gitignored)
│   ├── .env                   ← created in Step 4, has your real key (gitignored)
│   ├── .env.example
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   └── state.py
│   ├── evals/
│   │   ├── __init__.py
│   │   ├── bleu_scorer.py
│   │   ├── llm_judge.py
│   │   ├── run_evals.py
│   │   └── test_cases.json
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── glossary_lookup.py
│   │   └── server.py
│   ├── memory/
│   │   ├── __init__.py
│   │   └── working_memory.py
│   ├── sarvam/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── languages.py
│   ├── main.py
│   ├── Procfile
│   └── requirements.txt
└── frontend/
    ├── node_modules/           ← created in Step 5 (gitignored)
    ├── .env.local              ← created in Step 6 (gitignored)
    ├── .env.local.example
    ├── app/
    │   ├── globals.css
    │   ├── layout.tsx
    │   └── page.tsx
    ├── components/
    │   ├── BYOKSettings.tsx
    │   ├── LanguageSelector.tsx
    │   ├── PanelAudio.tsx
    │   ├── PanelDetected.tsx
    │   ├── PanelTranslation.tsx
    │   ├── PushToTalkButton.tsx
    │   ├── StatusBar.tsx
    │   └── TranslatorApp.tsx
    ├── hooks/
    │   └── useAudioRecorder.ts
    ├── lib/
    │   └── api.ts
    ├── next.config.js
    ├── package.json
    ├── postcss.config.js
    ├── tailwind.config.js
    └── tsconfig.json
```

If any file is missing, re-extract the zip — do not hand-create files, since exact content matters for imports to resolve correctly.

---

## 8. (Optional but recommended) LangSmith tracing

This is what gives you screenshots of agent traces for your GitHub README and shows the JD's "observability" requirement in action.

1. Go to `https://smith.langchain.com` and sign up free
2. Create a new project, name it `sarvam-voice-translator`
3. Copy your API key from Settings
4. Add these three lines to `backend/.env`:
   ```bash
   LANGCHAIN_API_KEY=your_langsmith_key_here
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_PROJECT=sarvam-voice-translator
   ```
5. Restart the backend (next document covers exactly how) — every LangGraph run now appears automatically in your LangSmith dashboard with per-node latency and token cost.

---

## 9. Deployment prep (do this only after local testing passes — see the second document)

**Backend → Render.com**
1. Push this repo to GitHub
2. On render.com: New → Web Service → connect your repo
3. Root directory: `backend`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables: `SARVAM_API_KEY`, and optionally the three LangSmith vars from Step 8
7. Deploy — copy the resulting `https://your-app.onrender.com` URL

**Frontend → Vercel**
1. On vercel.com: New Project → import the same GitHub repo
2. Root directory: `frontend`
3. Add environment variable: `NEXT_PUBLIC_BACKEND_URL` = your Render URL from above
4. Deploy — copy the resulting `https://your-app.vercel.app` URL

That Vercel URL is what goes in your cover email to Sarvam's HR.

---

## Common setup errors and fixes

**`pip install` fails with a compiler error** — you're likely on a very old Python. Upgrade to 3.11+.

**`npm install` warns about vulnerabilities** — run `npm audit` to see details. The remaining advisories after this setup are general Next.js advisories unrelated to features this app uses (Image Optimizer, Middleware, i18n routing) and are safe to leave for a portfolio project.

**`ModuleNotFoundError` when running the backend** — your venv isn't activated. Re-run the `source venv/bin/activate` command from Step 3; you should see `(venv)` in your prompt.

**Backend starts but `/translate` always fails** — your `SARVAM_API_KEY` in `.env` is missing, wrong, or has no credits left. Check the dashboard.

**Frontend shows blank page or console errors about `NEXT_PUBLIC_BACKEND_URL`** — confirm `.env.local` exists (not just `.env.local.example`) and that you restarted `npm run dev` after creating it. Next.js only reads env files at startup.

Once every step above is done, move to the second document: **`RUN_AND_TEST.md`** — it walks through starting both servers and verifying the full pipeline works end-to-end.
