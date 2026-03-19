# 🚀 NGROK SETUP FOR ELEVENLABS

Your ngrok authtoken is configured ✅

## Quick Start

### Terminal 2: Start ngrok tunnel
```bash
cd techmellon-fde
.venv\Scripts\activate
python start_ngrok.py
```

When ngrok starts, you'll see:
```
✅ ngrok tunnel is live!
📍 Public URL: https://xxxxx-xx-xxx.ngrok.io
⚙️  Update your ElevenLabs agent webhook to:
   https://xxxxx-xx-xxx.ngrok.io/webhook/elevenlabs
```

---

## Setup Checklist

### ✅ You have:
- Authtoken: configured in `start_ngrok.py`
- ngrok Python library: installed (`pyngrok`)
- API running: `uvicorn backend.main:app --reload --port 8000` (Terminal 1)

### ⏳ Next steps:
1. **Run ngrok**: `python start_ngrok.py` in Terminal 2
2. **Copy the public URL** (https://xxxxx-xx-xxx.ngrok.io)
3. **Update ElevenLabs** with webhook: `https://xxxxx-xx-xxx.ngrok.io/webhook/elevenlabs`
4. **Open the UI**: `http://localhost:8000` (Terminal 3)
5. **Click "START LOOP"** in the observer UI

---

## Terminal Layout

```
Terminal 1 (API Server):
$ uvicorn backend.main:app --reload --port 8000
INFO:     Uvicorn running on http://127.0.0.1:8000

Terminal 2 (ngrok tunnel):
$ python start_ngrok.py
✅ ngrok tunnel is live!
📍 Public URL: https://xxxxx-xx-xxx.ngrok.io

Terminal 3 (Browser):
http://localhost:8000
```

---

## Troubleshooting

### ngrok tunnel fails to start
- Check internet connection
- Your firewall might block ngrok — try temporarily disabling it
- Authtoken might have expired — regenerate at https://dashboard.ngrok.com

### API doesn't receive webhook calls
- Make sure ngrok URL is updated in ElevenLabs agent
- Check ElevenLabs webhook settings → must be `https://xxxxx-xx-xxx.ngrok.io/webhook/elevenlabs`

### ElevenLabs agent not working
- Verify agent is created in ElevenLabs → Conversational AI
- Tools must be added to the agent (check system prompt for tool definitions)
- Webhook URL must match exactly

---

**Ready?** Run `python start_ngrok.py` in Terminal 2! 🎉
