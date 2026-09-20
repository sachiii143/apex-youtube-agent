# APEX — Complete Setup Guide

Step-by-step guide to get APEX running and uploading to YouTube.  
Total time: **30-45 minutes** (mostly waiting for installs).

---

## Step 1 — Install Python (5 min)

1. Go to [python.org/downloads](https://python.org/downloads)
2. Download Python 3.11 or newer
3. Run installer — **tick "Add Python to PATH"** (critical)
4. Click Install Now

Verify: open PowerShell → type `python --version` → should show `Python 3.11.x`

---

## Step 2 — Clone the repo (2 min)

```powershell
git clone https://github.com/sachiii143/apex-youtube-agent.git
cd apex-youtube-agent
```

Or download the ZIP from GitHub and extract to `C:\Krish11\`

---

## Step 3 — Run the one-shot installer (10-15 min)

```powershell
PowerShell -ExecutionPolicy Bypass -File "run_nova.ps1"
```

This installs everything automatically:
- Python virtual environment
- Flask, MoviePy, Pillow, gTTS, requests, apscheduler
- pyautogui (desktop control)
- playwright + Chromium (browser control)
- ffmpeg (video rendering)
- Ollama (local AI fallback)

---

## Step 4 — Get your free API keys (10 min)

The installer asks for these. All free:

### DeepSeek (recommended brain)
1. Go to [platform.deepseek.com](https://platform.deepseek.com)
2. Sign up (free)
3. Go to API Keys → Create new key
4. Paste when the installer asks

### Gemini (best for voice)
1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Sign in with Google
3. Click "Get API Key" → Create API key in new project
4. Paste when the installer asks

---

## Step 5 — YouTube OAuth (20 min, one time only)

This allows APEX to upload videos to your channel.

### 5a — Enable YouTube Data API
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (any name)
3. Click "Enable APIs and Services"
4. Search "YouTube Data API v3" → Enable it

### 5b — Create OAuth credentials
1. Go to Credentials → Create Credentials → OAuth 2.0 Client ID
2. Application type: **Desktop app**
3. Name: APEX
4. Click Create → Download JSON

### 5c — Configure the project
1. Rename the downloaded file to `client_secrets.json`
2. Put it in your APEX project folder (`C:\Krish11\client_secrets.json`)
3. Run `run_nova.ps1` again
4. It detects `client_secrets.json` and opens your browser
5. Sign in with your YouTube channel Google account
6. Allow the permissions
7. Done — token saved for all future uploads

---

## Step 6 — First video (5 min)

1. Browser opens at `http://127.0.0.1:5000`
2. Nova greets you by voice
3. Click "Chat with Nova" in the sidebar
4. Type: `make a video about Trishul losing his homework`
5. Nova creates the full video (5-15 min depending on internet speed)
6. Go to Approvals tab → review the metadata
7. Click "Approve & Upload to YouTube"
8. Video goes live

---

## Unlock real cartoon animation (optional)

### Tier 2 — Manim (free)
```powershell
pip install manim
winget install MiKTeX.MiKTeX
```
Then restart APEX — Animation tab shows Manim as available.

### Tier 3 — Kling AI (paid, ₹1,500/month)
1. Sign up at [klingai.com](https://klingai.com) — 66 free clips on signup
2. Go to API → Create API key
3. In APEX dashboard → Settings → API Keys → paste Kling AI key
4. Save → APEX automatically uses Kling for all future videos

### Tier 3 — Pika Labs (paid, ₹1,200/month)
1. Sign up at [pika.art](https://pika.art)
2. API → get key → paste in APEX Settings → PIKA_API_KEY

---

## Every future run

Just run this one command:

```powershell
PowerShell -ExecutionPolicy Bypass -File "C:\Krish11\run_nova.ps1"
```

Or set up a Windows Task Scheduler to run it automatically on startup.

---

## Troubleshooting

### "Python not found"
Reinstall Python and tick "Add Python to PATH" during installation.

### "ffmpeg not found"
Run: `winget install ffmpeg`  
Or download from [ffmpeg.org](https://ffmpeg.org) and add to PATH.

### "Upload failed — OAuth error"
Delete `youtube_token.json` and run `run_nova.ps1` again — it re-does OAuth.

### "Video rendered but no sound"
gTTS requires internet. Check your connection. Alternatively install: `pip install pyttsx3`

### "Manim render failed"
Install MiKTeX: `winget install MiKTeX.MiKTeX`  
Restart PowerShell and try again.

### "Nova not responding"
No API key set. Add a free DeepSeek or Gemini key in Settings → API Keys.

---

## Getting help

Open an issue on GitHub with:
- Your OS and Python version
- The error message
- Which step failed
