"""
upload_to_youtube.py — APEX
YouTube Data API v3 uploader with OAuth2.
Run with --setup flag to do the one-time OAuth flow.
"""

import os, sys, json
from pathlib import Path

BASE_DIR      = Path(__file__).parent
TOKEN_FILE    = BASE_DIR / "youtube_token.json"
SECRETS_FILE  = BASE_DIR / "client_secrets.json"
SCOPES        = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtubepartner",
]

def _get_credentials():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not SECRETS_FILE.exists():
                raise FileNotFoundError(
                    f"client_secrets.json not found in {BASE_DIR}. "
                    "Download from Google Cloud Console > Credentials > OAuth 2.0 Client IDs"
                )
            flow  = InstalledAppFlow.from_client_secrets_file(str(SECRETS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
    return creds

def upload(video_path: str, title: str, description: str,
           tags: list = None, privacy: str = "public",
           made_for_kids: bool = True) -> dict:
    """Upload a video to YouTube. Returns {"id": youtube_video_id}"""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds   = _get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title":       title[:100],
            "description": description[:5000],
            "tags":        (tags or [])[:15],
            "categoryId":  "22",
        },
        "status": {
            "privacyStatus":      privacy,
            "madeForKids":        made_for_kids,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True, chunksize=1024*1024*5)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Upload progress: {int(status.progress() * 100)}%")

    video_id = response.get("id","")
    print(f"  Uploaded: https://youtube.com/watch?v={video_id}")
    return {"id": video_id, "url": f"https://youtube.com/watch?v={video_id}"}

def set_thumbnail(video_id: str, thumbnail_path: str):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds   = _get_credentials()
    youtube = build("youtube", "v3", credentials=creds)
    youtube.thumbnails().set(
        videoId    = video_id,
        media_body = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
    ).execute()

def is_configured() -> bool:
    return TOKEN_FILE.exists()

if __name__ == "__main__":
    if "--setup" in sys.argv:
        print("Starting YouTube OAuth setup...")
        print("Your browser will open — sign in with your YouTube channel account.")
        try:
            creds = _get_credentials()
            print("OAuth complete! Token saved. Nova can now upload to YouTube.")
        except Exception as e:
            print(f"OAuth failed: {e}")
            print("Make sure client_secrets.json is in the project folder.")
    else:
        print("Usage: python upload_to_youtube.py --setup")
        print("       (to configure YouTube OAuth for uploads)")
