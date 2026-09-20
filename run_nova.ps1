# ================================================================
#  APEX v1 — Complete One-Shot Setup & Launch
#  Save all project files to C:\Krish11\
#  Run: PowerShell -ExecutionPolicy Bypass -File "C:\Krish11\run_nova.ps1"
# ================================================================

$ErrorActionPreference = "Continue"
$ProjectDir = "C:\Krish11"
$VenvDir    = "$ProjectDir\venv"
$PythonExe  = "$VenvDir\Scripts\python.exe"
$ConfigFile = "$ProjectDir\.apex_config"

Set-Location $ProjectDir

function Write-Step($n, $msg) { Write-Host ""; Write-Host "  [$n] $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "      OK: $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "      !! $msg" -ForegroundColor Yellow }
function Write-Info($msg) { Write-Host "      $msg" -ForegroundColor DarkGray }

Clear-Host
Write-Host ""
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host "   APEX v1 - AI YouTube Agent" -ForegroundColor Cyan
Write-Host "   Trishul / Sandy / Libhu - Sunridge Town" -ForegroundColor Cyan
Write-Host "   Complete One-Shot Setup" -ForegroundColor Cyan
Write-Host "  ================================================" -ForegroundColor Cyan

# Fix flat folder structure
$StaticDir = "$ProjectDir\static"
if (-not (Test-Path $StaticDir)) { New-Item -ItemType Directory -Path $StaticDir | Out-Null }
foreach ($file in @("index.html","app.js","style.css")) {
    $src = "$ProjectDir\$file"; $dst = "$StaticDir\$file"
    if ((Test-Path $src) -and (-not (Test-Path $dst))) { Move-Item $src $dst; Write-Info "Moved $file to static\" }
}

# Step 1: Python
Write-Step "1/8" "Checking Python..."
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "  ERROR: Python not found." -ForegroundColor Red
    Write-Host "  Install from https://python.org - tick Add to PATH during install" -ForegroundColor White
    Read-Host "  Press Enter to exit"; exit 1
}
Write-OK (python --version 2>&1)

# Step 2: Virtual environment
Write-Step "2/8" "Setting up virtual environment..."
if (-not (Test-Path $PythonExe)) { python -m venv $VenvDir 2>&1 | Out-Null }
Write-OK "Virtual environment ready"

# Step 3: Core packages
Write-Step "3/8" "Installing packages (3-5 min first time)..."
& $PythonExe -m pip install --upgrade pip -q 2>&1 | Out-Null
& $PythonExe -m pip install flask flask-sock openai gTTS pillow requests apscheduler tweepy praw pypdf cryptography google-api-python-client google-auth-oauthlib google-auth-httplib2 -q 2>&1 | Out-Null
Write-OK "Core packages done"
& $PythonExe -m pip install "moviepy==1.0.3" -q 2>&1 | Out-Null
Write-OK "Video rendering ready"
& $PythonExe -m pip install pyautogui -q 2>&1 | Out-Null
Write-OK "Desktop control ready (eyes + hands + legs)"
& $PythonExe -m pip install playwright -q 2>&1 | Out-Null
& $PythonExe -m playwright install chromium 2>&1 | Out-Null
Write-OK "Browser control ready"
& $PythonExe -m pip install SpeechRecognition google-cloud-texttospeech -q 2>&1 | Out-Null
Write-OK "Voice packages ready"

# Step 4: ffmpeg
Write-Step "4/8" "Checking ffmpeg..."
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    try {
        winget install ffmpeg --silent --accept-package-agreements --accept-source-agreements 2>$null
        $env:PATH += ";C:\ProgramData\chocolatey\bin;C:\ffmpeg\bin"
        Write-OK "ffmpeg installed"
    } catch { Write-Warn "ffmpeg install failed - download from https://ffmpeg.org and add to PATH" }
} else { Write-OK "ffmpeg already installed" }

# Step 5: Ollama (local AI fallback)
Write-Step "5/8" "Setting up Ollama (free local AI - works without internet)..."
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    try {
        winget install Ollama.Ollama --silent --accept-package-agreements --accept-source-agreements 2>$null
        Write-OK "Ollama installed"
        Start-Sleep 5
        try { ollama pull qwen2.5-coder:1.5b 2>&1 | Out-Null; Write-OK "AI model downloaded" }
        catch { Write-Warn "Model download will retry on first Nova run" }
    } catch { Write-Warn "Ollama install failed - Nova will use cloud AI (add a key below)" }
} else { Write-OK "Ollama already installed" }

# Step 6: API keys
Write-Step "6/8" "API Key Setup..."
if (-not (Test-Path $ConfigFile)) {
    Write-Host ""
    Write-Host "  ================================================" -ForegroundColor Cyan
    Write-Host "   NOVA KEY SETUP - All free, press Enter to skip" -ForegroundColor Cyan
    Write-Host "  ================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  BRAIN - add at least one of these free keys:" -ForegroundColor White
    Write-Host "  DeepSeek -> platform.deepseek.com (free 500k tokens)" -ForegroundColor DarkGray
    Write-Host "  Gemini   -> aistudio.google.com   (free, best for voice)" -ForegroundColor DarkGray
    Write-Host "  Groq     -> console.groq.com      (free, fastest)" -ForegroundColor DarkGray
    Write-Host ""
    $dk = Read-Host "  DeepSeek key [RECOMMENDED]"
    $gk = Read-Host "  Gemini key   [BEST FOR VOICE]"
    $grk= Read-Host "  Groq key     [OPTIONAL]"
    $oai= Read-Host "  OpenAI key   [OPTIONAL]"
    Write-Host ""
    Write-Host "  YOUTUBE (needed to upload videos):" -ForegroundColor White
    Write-Host "  console.cloud.google.com -> Enable YouTube Data API v3 -> Create API key" -ForegroundColor DarkGray
    Write-Host ""
    $ytk= Read-Host "  YouTube Data API key"
    Write-Host ""
    Write-Host "  SOCIAL & TRACKING (optional):" -ForegroundColor White
    $tgt= Read-Host "  Telegram Bot token (@BotFather on Telegram)"
    $tgc= Read-Host "  Telegram Chat ID"
    $bit= Read-Host "  Bitly token (bitly.com - free link tracking)"

    @{ DEEPSEEK_API_KEY=$dk; GEMINI_API_KEY=$gk; GROQ_API_KEY=$grk; OPENAI_API_KEY=$oai;
       YOUTUBE_DATA_API_KEY=$ytk; TELEGRAM_BOT_TOKEN=$tgt; TELEGRAM_CHAT_ID=$tgc;
       BITLY_ACCESS_TOKEN=$bit } | ConvertTo-Json | Set-Content $ConfigFile -Encoding UTF8
    Write-OK "Keys saved to .apex_config"
}

$cfg = Get-Content $ConfigFile -Raw | ConvertFrom-Json
foreach ($k in @("DEEPSEEK_API_KEY","GEMINI_API_KEY","GROQ_API_KEY","OPENAI_API_KEY",
                  "YOUTUBE_DATA_API_KEY","TELEGRAM_BOT_TOKEN","TELEGRAM_CHAT_ID","BITLY_ACCESS_TOKEN")) {
    $v = $cfg.$k; if ($v) { [System.Environment]::SetEnvironmentVariable($k,$v,"Process") }
}
if     ($env:DEEPSEEK_API_KEY)   { $env:LLM_PROVIDER="deepseek" }
elseif ($env:GEMINI_API_KEY)     { $env:LLM_PROVIDER="gemini"   }
elseif ($env:GROQ_API_KEY)       { $env:LLM_PROVIDER="groq"     }
else                             { $env:LLM_PROVIDER="ollama"   }
Write-OK "Brain: $($env:LLM_PROVIDER)"

# Step 7: YouTube OAuth
Write-Step "7/8" "YouTube OAuth (needed to upload videos)..."
$TokenFile   = "$ProjectDir\youtube_token.json"
$SecretsFile = "$ProjectDir\client_secrets.json"

if (Test-Path $TokenFile) {
    Write-OK "YouTube OAuth already done - uploads ready"
} elseif (Test-Path $SecretsFile) {
    Write-Info "client_secrets.json found - opening browser for sign in..."
    Write-Info "Sign in with your YouTube channel Google account when browser opens"
    Start-Sleep 2
    & $PythonExe "$ProjectDir\upload_to_youtube.py" --setup 2>&1
    if (Test-Path $TokenFile) { Write-OK "YouTube OAuth done - uploads ready" }
    else { Write-Warn "OAuth not completed - run script again after signing in" }
} else {
    Write-Host ""
    Write-Host "  YouTube OAuth needs client_secrets.json (one time setup):" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  STEP A: Go to https://console.cloud.google.com" -ForegroundColor White
    Write-Host "  STEP B: Create project -> Enable YouTube Data API v3" -ForegroundColor White
    Write-Host "  STEP C: Credentials -> Create -> OAuth 2.0 Client ID -> Desktop app" -ForegroundColor White
    Write-Host "  STEP D: Download JSON -> rename to client_secrets.json" -ForegroundColor White
    Write-Host "  STEP E: Put client_secrets.json in C:\Krish11\" -ForegroundColor Yellow
    Write-Host "  STEP F: Run this script again - OAuth completes automatically" -ForegroundColor White
    Write-Host ""
    Write-Host "  Nova will work for EVERYTHING ELSE right now." -ForegroundColor Green
    Write-Host "  (Script writing, image generation, video rendering, chat, voice)" -ForegroundColor DarkGray
    Write-Host ""
    $ans = Read-Host "  Continue without YouTube upload for now? (Y/N)"
    if ($ans.ToUpper() -eq "N") { Write-Host "  Add client_secrets.json then run again." -ForegroundColor Yellow; exit 0 }
    Write-Warn "YouTube upload skipped - add client_secrets.json and run again to enable"
}

# Step 8: Launch
Write-Step "8/8" "Launching Nova..."
Write-Host ""
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host "   Nova starting at http://127.0.0.1:5000" -ForegroundColor Cyan
Write-Host "   Browser opens in 3 seconds" -ForegroundColor Cyan
Write-Host "   Press Ctrl+C to stop Nova" -ForegroundColor DarkGray
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  QUICK START:" -ForegroundColor White
Write-Host "  - Nova greets you by voice on opening" -ForegroundColor DarkGray
Write-Host "  - Click MIC button or type to talk" -ForegroundColor DarkGray
Write-Host "  - Say: 'Nova make a video about Trishul'" -ForegroundColor DarkGray
Write-Host "  - Nova creates video -> you approve -> uploads to YouTube" -ForegroundColor DarkGray
Write-Host "  - Say 'Hey Nova' hands-free anytime" -ForegroundColor DarkGray
Write-Host ""

Start-Job -ScriptBlock { Start-Sleep 3; Start-Process "http://127.0.0.1:5000" } | Out-Null
& $PythonExe "$ProjectDir\dashboard.py"
