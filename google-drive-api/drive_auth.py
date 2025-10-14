from __future__ import print_function
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_service():
    creds = None

    # Get the directory of this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    client_secret_path = os.path.join(base_dir, "client_secret_1059329444691-s5dm39707hik1s07i8e9avsdj4r34scu.apps.googleusercontent.com.json")
    token_path = os.path.join(base_dir, "token.json")

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    return build("drive", "v3", credentials=creds)