# ⚡ APEX — AI YouTube Content Agent

<div align="center">

![APEX Banner](https://img.shields.io/badge/APEX-AI%20YouTube%20Agent-00d4ff?style=for-the-badge&logo=youtube&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Backend-black?style=for-the-badge&logo=flask&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Production%20Ready-00e676?style=for-the-badge)

**The world's first fully autonomous AI YouTube content pipeline.**  
*From topic → script → video → upload → analytics → improvement — fully automated.*

[🚀 Quick Start](#-quick-start) • [📖 Documentation](#-how-it-works) • [🎨 Animation Tiers](#-animation-tiers) • [🌐 Dashboard Preview](#-dashboard) • [🗺️ Roadmap](#-roadmap)

</div>

---

## 🧠 What is APEX?

APEX is an agentic AI system that runs a complete YouTube channel **without manual work**. You provide a topic — APEX handles everything else:

- ✍️ **Writes comedy scripts** using your original characters (Trishul, Sandy, Libhu)
- 🎨 **Generates cartoon images** via AI (free — Pollinations.ai)
- 🎙️ **Records voice narration** (gTTS free or Google WaveNet human-quality)
- 🎬 **Renders real .mp4 videos** with Ken Burns motion effects
- 🖼️ **Creates branded thumbnails** with bold text overlays
- ✅ **Requires your approval** before every upload — you stay in control
- 📤 **Uploads to YouTube** with full SEO metadata
- 📊 **Tracks analytics** and improves the next video automatically
- ⏰ **Runs daily on a schedule** — fully autonomous

> Nova is APEX's AI persona — she has memory, voice, hands, eyes, and legs.  
> She talks to you in real time, controls your browser, sees your screen, and executes tasks on your desktop.

---

## ✨ Key Features

### 🎭 Original IP — Sunridge Town
Three original characters you own 100%:
- **Trishul** — The overconfident one. Always has a plan. Plan always fails.
- **Sandy** — The logical one. Always right. Nobody listens.
- **Libhu** — The wildcard. Randomly genius or completely clueless.

No licensed characters. No copyright risk. 100% owned by you.

### 🎬 3-Tier Animation System

| Tier | Cost | Quality | How to activate |
|------|------|---------|-----------------|
| **Tier 1 — Narrated Slideshow** | Free forever | AI images + voice + Ken Burns | Works immediately, no setup |
| **Tier 2 — Manim 2D Animation** | Free forever | Smooth animated scenes (3Blue1Brown style) | `pip install manim` |
| **Tier 3 — Kling AI / Pika Labs** | ~₹1,500/month | Near cartoon-quality animation | Add API key in Settings |

APEX **auto-selects** the best available tier on every run. No manual switching needed.

### 🧠 Nova's Senses
| Sense | Capability |
|-------|-----------|
| **Soul** | SQLite memory — remembers every conversation from day one |
| **Brain** | DeepSeek (free) → Gemini → Groq → Ollama — auto-detect |
| **Voice** | Speaks every reply aloud via Web Speech TTS or Google WaveNet |
| **Ears** | Click 🎤 to speak, or say "Hey Nova" hands-free |
| **Eyes** | Full desktop screenshot via pyautogui + browser screenshot |
| **Hands** | Move mouse, click anywhere, drag, scroll, type on desktop |
| **Legs** | Open folders, files, apps, run commands, browse web |

### 🔒 Safety-First Architecture
- Every YouTube upload **blocked** until you explicitly approve
- Every Google Ads spend **blocked** until you explicitly approve
- Copyright scanner — blocks any reference to licensed cartoon characters
- Payload-locked approval cards — any metadata change invalidates the card
- Full audit log — every action recorded immutably
- Prompt injection defense — user input sanitised before reaching LLM

---

## 🚀 Quick Start

### Prerequisites
- Windows 10/11 (Mac/Linux supported with minor changes)
- Python 3.10 or newer ([download](https://python.org/downloads) — tick **Add to PATH**)
- Git ([download](https://git-scm.com))

### One-Command Install

```powershell
# 1. Clone the repo
git clone https://github.com/sachiii143/apex-youtube-agent.git
cd apex-youtube-agent

# 2. Run the one-shot setup (installs everything, asks for free API keys)
PowerShell -ExecutionPolicy Bypass -File "run_nova.ps1"
```

That's it. The script handles:
- ✅ Python virtual environment
- ✅ All Python packages
- ✅ ffmpeg (video rendering)
- ✅ Ollama (local AI fallback)
- ✅ Playwright + Chromium (browser control)
- ✅ Free API key setup (wizard asks on first run)
- ✅ YouTube OAuth (guided step by step)
- ✅ Opens browser at `http://127.0.0.1:5000`

### Every future run

```powershell
PowerShell -ExecutionPolicy Bypass -File "run_nova.ps1"
```

Keys are saved. Nova starts in under 10 seconds.

---

## 📖 How It Works

### The Complete Pipeline

```
You say: "Nova, make a video about Trishul losing his homework"
                        ↓
        📝  Script Engine  (LLM writes 6-7 scene comedy sketch)
                        ↓
        🎨  Image Engine   (Pollinations generates cartoon images)
                        ↓
        🎙️  Voice Engine   (gTTS records narration per scene)
                        ↓
        🎬  Video Builder  (MoviePy renders final .mp4)
                        ↓
        🖼️  Thumbnail Gen  (PIL creates branded 1280×720 thumbnail)
                        ↓
        ✅  Quality Check  (20 automated checks — blocks failures)
                        ↓
        ⚖️  Rights Gate    (copyright scanner — blocks violations)
                        ↓
        👁️  Preview Card   (you see exact metadata before upload)
                        ↓
        🔐  YOUR APPROVAL  (explicit click required — no auto-publish)
                        ↓
        📤  YouTube Upload (title, tags, description, thumbnail set)
                        ↓
        📊  Analytics Reg  (auto-registered for tracking)
                        ↓
        🔄  Enhancement    (next video improved using real data)
                        ↓
        ⏰  Scheduler      (queues next episode automatically)
```

---

## 🎨 Animation Tiers — Full Guide

### Tier 1: Narrated Slideshow (Free, works today)

No install needed. APEX generates:
- AI cartoon image per scene (Pollinations.ai — unlimited free)
- Voice narration over each image (gTTS — free)
- Ken Burns zoom effect (slow pan/zoom on each image)
- On-screen captions
- Full .mp4 file ready to upload

**This is a proven YouTube format.** Channels like Bedtime Stories (5M+ subs) and The Infographics Show (14M+ subs) built massive audiences with narrated slideshow content.

### Tier 2: Manim 2D Animation (Free, one-time install)

Install once, free forever:

```powershell
pip install manim
winget install MiKTeX.MiKTeX   # Windows (for text rendering)
winget install ffmpeg
```

APEX generates smooth animated scenes:
- Moving characters (Trishul, Sandy, Libhu appear as animated shapes)
- Speech bubbles with dialogue
- Animated captions and transitions
- Same animation engine as **3Blue1Brown** (4M+ subscribers)

### Tier 3: Kling AI / Pika Labs (Paid — Real Cartoon Animation)

Add one API key in Settings to unlock near-Cartoon-Network quality:

**Kling AI** (Recommended)
- Sign up: [klingai.com](https://klingai.com)
- **66 free clips on signup** (enough for ~11 episodes to test)
- Paid: ~₹1,500/month for ~500 clips
- Quality: Excellent — actual moving cartoon characters

**Pika Labs**
- Sign up: [pika.art](https://pika.art)
- Free trial available
- Paid: ~₹1,200/month
- Quality: Very good

**Runway ML**
- Sign up: [runwayml.com](https://runwayml.com)
- Paid: ~₹1,500/month
- Quality: Cinematic

Once you add a key, APEX **automatically uses it** on every video — no other changes needed.

---

## 🌐 Dashboard

17-tab web dashboard at `http://127.0.0.1:5000`:

| Tab | What it does |
|-----|-------------|
| 🏠 **Home** | Stats + quick actions + live activity + neural globe |
| 💬 **Chat** | Talk to Nova in real time — controls everything |
| 🧠 **Neural Core** | Live 3D globe showing all 8 agents |
| 🎬 **Pipeline** | Production jobs — pending, running, done |
| ✅ **Approvals** | Every upload waits here for your click |
| 📝 **Scripts** | All written scripts with scene breakdown |
| 📹 **Published** | Published videos with YouTube links |
| 🎨 **Animation** | Switch between 3 animation tiers |
| 🔬 **Research** | PULSE engine — trend and competitor research |
| 📋 **Content Plans** | Multi-episode content planning |
| 🧪 **Experiments** | A/B test thumbnails, titles, formats |
| 📊 **Analytics** | Real YouTube analytics — views, CTR, retention |
| ⏰ **Scheduler** | Daily auto-queue with topic pool |
| 📢 **Google Ads** | Read-only campaigns, draft with approval |
| 🔍 **Audit Log** | Every action recorded immutably |
| 💚 **Health** | System checks + backup management |
| ⚙️ **Settings** | API keys, provider selection, characters |

---

## 🔧 Configuration

### Free API Keys (all optional but recommended)

| Key | Where to get | What it unlocks |
|-----|-------------|-----------------|
| **DeepSeek** | [platform.deepseek.com](https://platform.deepseek.com) | Best LLM brain (free 500k tokens/month) |
| **Gemini** | [aistudio.google.com](https://aistudio.google.com) | Google LLM + best voice quality |
| **Groq** | [console.groq.com](https://console.groq.com) | Fastest free cloud LLM |
| **YouTube Data API** | [console.cloud.google.com](https://console.cloud.google.com) | YouTube upload + analytics |

### Paid API Keys (for real cartoon animation)

| Key | Where to get | Cost | Quality |
|-----|-------------|------|---------|
| **KLING_API_KEY** | [klingai.com](https://klingai.com) | ~₹1,500/mo | ⭐⭐⭐⭐⭐ |
| **PIKA_API_KEY** | [pika.art](https://pika.art) | ~₹1,200/mo | ⭐⭐⭐⭐ |
| **RUNWAY_API_KEY** | [runwayml.com](https://runwayml.com) | ~₹1,500/mo | ⭐⭐⭐⭐⭐ |

All keys saved locally to `.apex_config` — never sent to any third party.

### YouTube OAuth Setup (one time, ~20 minutes)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create project → Enable **YouTube Data API v3**
3. Credentials → Create → **OAuth 2.0 Client ID** → Desktop app
4. Download JSON → rename to `client_secrets.json`
5. Put `client_secrets.json` in the project folder
6. Run `run_nova.ps1` again — browser opens for sign-in → done forever

---

## 📁 Project Structure

```
apex-youtube-agent/
├── dashboard.py           # Flask backend — 79 API routes
├── apex_agent.py          # Comedy script writer (Trishul/Sandy/Libhu)
├── video_builder.py       # .mp4 renderer with approval gate
├── image_engine.py        # Pollinations + Ideogram + Leonardo
├── thumbnail_gen.py       # Branded YouTube thumbnail generator
├── manim_engine.py        # Tier 2 — free 2D animation
├── kling_engine.py        # Tier 3 — Kling/Pika/Runway animation
├── publisher.py           # YouTube upload with approval gate
├── analytics.py           # YouTube Analytics API integration
├── enhancement_engine.py  # Self-improvement loop
├── pipeline.py            # Full orchestrator
├── scheduler.py           # Daily auto-scheduler
├── research_engine.py     # PULSE — trend + competitor research
├── content_plan.py        # Multi-episode content planning
├── experiment_registry.py # A/B testing framework
├── quality_check.py       # 20-point automated quality gate
├── rights_ledger.py       # Asset rights tracking + copyright scan
├── approval.py            # Approval card system
├── memory.py              # Persistent SQLite memory (Nova's soul)
├── llm_provider.py        # Multi-provider LLM gateway
├── desktop_agent.py       # Eyes + hands + legs (pyautogui)
├── browser_agent.py       # Browser control (Playwright)
├── hardening.py           # Security + backup + health checks
├── audit_log.py           # Immutable event log
├── job_queue.py           # Idempotent job queue with retry
├── character_bible.py     # Trishul/Sandy/Libhu original IP
├── google_ads.py          # Google Ads read-only + draft campaigns
├── upload_to_youtube.py   # YouTube OAuth uploader
├── static/
│   ├── index.html         # 17-page dashboard frontend
│   ├── app.js             # Complete frontend logic
│   └── style.css          # Design system
├── tests/
│   └── test_e2e.py        # 20 end-to-end integration tests
├── run_nova.ps1            # One-shot setup + launcher
└── requirements.txt        # All dependencies
```

---

## 🧪 Test Suite

```powershell
# Run all 20 end-to-end tests
python tests/test_e2e.py
```

```
test_01_audit_log .................... PASS
test_02_job_queue .................... PASS
test_03_approval_issue_approve_check . PASS
test_04_approval_payload_lock ........ PASS
test_05_character_bible_intact ....... PASS
test_06_memory_persist_recall ........ PASS
test_07_hardening_injection_blocked .. PASS
test_08_rights_ledger ................ PASS
test_09_quality_check_passes ......... PASS
test_10_quality_check_copyright ...... PASS
test_11_image_engine ................. PASS
test_12_llm_provider_fallback ........ PASS
test_13_pipeline_status .............. PASS
test_14_scheduler .................... PASS
test_15_publisher_list ............... PASS
test_16_analytics_summary ............ PASS
test_17_enhancement_no_data .......... PASS
test_18_google_ads_summary ........... PASS
test_19_experiment_create ............ PASS
test_20_full_flow_simulation ......... PASS

PASSED: 20 / FAILED: 0 — ALL TESTS PASSED
```

---

## 🗺️ Roadmap

### ✅ Completed (v1.0)
- [x] Full YouTube pipeline — script → video → upload
- [x] 17-tab interactive dashboard
- [x] 3-tier animation system (free + paid)
- [x] Nova AI persona with memory, voice, hands, eyes, legs
- [x] Approval gate on every upload and spend
- [x] Quality check + rights ledger + copyright scanner
- [x] Daily scheduler with enhancement feedback loop
- [x] Google Ads integration (read-only + draft)
- [x] 20 end-to-end integration tests
- [x] One-shot PowerShell installer

### 🔜 Coming (v1.1)
- [ ] **NEXUS** — AI Affiliate Marketing Agent (ClickBank, CJ, Digi24)
- [ ] Multi-client channel management
- [ ] Instagram Reels auto-posting
- [ ] YouTube Shorts auto-generation from long videos
- [ ] Monetization tracker (AdSense revenue display)
- [ ] Client PDF reporting export
- [ ] Email newsletter builder

### 🔮 Future (v2.0)
- [ ] Full lip-synced character animation
- [ ] Voice cloning for consistent character voices
- [ ] Automatic trend detection + topic injection
- [ ] Multi-language support (Tamil, Hindi, English)
- [ ] SaaS packaging — manage client channels

---

## 💡 Realistic Expectations

| Metric | Timeline | Notes |
|--------|----------|-------|
| First video live | Day 1 | After OAuth setup |
| 100 subscribers | 1-3 months | Depends on niche + consistency |
| 1,000 subscribers | 3-9 months | Required for monetization |
| YouTube Partner | 6-12 months | 1K subs + 4K watch hours |
| ₹10,000/month | 12-18 months | With monetization + ads enabled |

> **APEX handles the consistency.** Daily uploads are the single most proven growth driver on YouTube. APEX makes this possible without manual work.

No tool guarantees views. Growth depends on content quality, niche competition, and YouTube's algorithm. APEX gives you the best possible setup — execution is automatic.

---

## 🤝 Contributing

Contributions welcome! Please read the guidelines:

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Run the test suite: `python tests/test_e2e.py`
4. Commit: `git commit -m 'feat: your feature'`
5. Push: `git push origin feature/your-feature`
6. Open a Pull Request

---

## 📄 License

MIT License — free to use, modify, and distribute.  
Original characters (Trishul, Sandy, Libhu, Sunridge Town) are the intellectual property of the channel creator and are **not** covered by the MIT license.

---

## 👤 Author

Built with ❤️ as a fully autonomous AI YouTube agent.  
If this project helped you, please ⭐ star the repository.

---

<div align="center">

**APEX v1.0** · 29 Python files · 79 API routes · 17 UI pages · 20/20 tests passing

*The AI that runs your YouTube channel so you don't have to.*

</div>
