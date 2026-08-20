"""YouTube Shorts upload via the YouTube Data API v3.

Authentication flow:
1. Place client_secret.json from Google Cloud Console in workspace/social/
2. First run opens a browser for OAuth consent and saves credentials
3. Subsequent runs reuse the saved credentials
"""
import datetime
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from . import config

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _get_credentials():
    creds = None
    if os.path.exists(config.CREDENTIALS_FILE):
        creds = Credentials.from_authorized_user_file(config.CREDENTIALS_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(config.CLIENT_SECRETS_FILE):
                raise FileNotFoundError(
                    f"YouTube client secret not found at {config.CLIENT_SECRETS_FILE}. "
                    "Download it from Google Cloud Console > APIs & Services > Credentials."
                )
            flow = InstalledAppFlow.from_client_secrets_file(config.CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(config.CREDENTIALS_FILE), exist_ok=True)
        with open(config.CREDENTIALS_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())
    return creds


def upload_short(video_path: str, title: str, description: str, tags: list[str], publish_at: datetime.datetime | None = None) -> dict:
    """Upload a video as a YouTube Short."""
    creds = _get_credentials()
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": config.YOUTUBE_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": "private" if publish_at else config.YOUTUBE_PRIVACY,
            "selfDeclaredMadeForKids": False,
        },
    }
    if publish_at:
        body["status"]["publishAt"] = publish_at.isoformat()

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
    return response
