from __future__ import print_function
import os, io, hashlib, time
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from drive_auth import get_service

# === CONFIGURATION ===
LOCAL_PATH = "/Users/gyuszix/Documents/ObsidianVault/Vault-Mk1"
DRIVE_FOLDER_NAME = "ObsidianVaultGoogleDrive"
IGNORE_FILE = os.path.join(os.path.dirname(__file__), ".syncignore")
# ======================


def load_ignore_list(ignore_file=IGNORE_FILE):
    """Load ignore patterns from a .syncignore file (like .gitignore)."""
    patterns = set()
    if os.path.exists(ignore_file):
        with open(ignore_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                patterns.add(line)
    return patterns


IGNORE_PATTERNS = load_ignore_list()


def should_skip(name: str) -> bool:
    """Decide whether a file should be skipped."""
    # Match file name or extension from ignore list
    if any(
        name == p
        or name.endswith(p)
        or name.startswith(p.strip("/"))
        for p in IGNORE_PATTERNS
    ):
        return True
    # Always skip hidden and temp files
    return (
        name.startswith(".")
        or name.lower().startswith("untitled")
    )


def file_md5(path: str) -> str:
    """Compute MD5 hash of a local file."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_execute(req, retries=5):
    """Execute a Drive API request with retries on rate-limit errors."""
    for attempt in range(retries):
        try:
            return req.execute()
        except HttpError as e:
            if e.resp.status in [403, 500, 503]:
                time.sleep(2 ** attempt)
            else:
                raise


def ensure_folder(service, name):
    """Find or create the top-level Drive folder."""
    resp = safe_execute(
        service.files().list(
            q=f"name='{name}' and mimeType='application/vnd.google-apps.folder'",
            fields="files(id)"
        )
    )
    if resp["files"]:
        return resp["files"][0]["id"]

    body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    created = safe_execute(service.files().create(body=body, fields="id"))
    return created["id"]


def list_drive_files(service, folder_id):
    """List all files (flat) within a Drive folder."""
    files, token = {}, None
    while True:
        r = safe_execute(
            service.files().list(
                q=f"'{folder_id}' in parents and mimeType!='application/vnd.google-apps.folder'",
                fields="nextPageToken, files(id,name,md5Checksum,modifiedTime)",
                pageToken=token,
            )
        )
        for f in r.get("files", []):
            files[f["name"]] = f
        token = r.get("nextPageToken")
        if not token:
            break
    return files


def upload_or_update(service, folder_id, path, drive_file=None):
    """Upload or update a single file."""
    name = os.path.basename(path)
    if should_skip(name):
        return

    media = MediaFileUpload(path, resumable=True)
    local_hash = file_md5(path)

    if not drive_file:
        safe_execute(
            service.files().create(
                body={"name": name, "parents": [folder_id]},
                media_body=media,
                fields="id"
            )
        )
        print(f"☁️  Uploaded: {name}")
    elif drive_file.get("md5Checksum") != local_hash:
        safe_execute(
            service.files().update(fileId=drive_file["id"], media_body=media)
        )
        print(f"🔄 Updated on Drive: {name}")
    else:
        print(f"✅ Unchanged: {name}")


def download_file(service, drive_file, local_dir):
    """Download a single file from Drive."""
    name = drive_file["name"]
    os.makedirs(local_dir, exist_ok=True)
    req = service.files().get_media(fileId=drive_file["id"])
    with open(os.path.join(local_dir, name), "wb") as f:
        downloader = MediaIoBaseDownload(f, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    print(f"⬇️  Downloaded: {name}")


def sync_two_way():
    """Perform two-way sync between local vault and Drive folder."""
    service = get_service()
    folder_id = ensure_folder(service, DRIVE_FOLDER_NAME)
    print(f"\n🔄 Two-way sync between '{LOCAL_PATH}' and Drive '{DRIVE_FOLDER_NAME}'\n")

    drive_files = list_drive_files(service, folder_id)

    # Collect all local files recursively
    local_files = {}
    for root, dirs, files in os.walk(LOCAL_PATH):
        dirs[:] = [d for d in dirs if d not in IGNORE_PATTERNS]
        for f in files:
            if should_skip(f):
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, LOCAL_PATH)
            local_files[rel] = {"path": full, "hash": file_md5(full)}

    # Upload new / changed locals
    for name, info in local_files.items():
        upload_or_update(service, folder_id, info["path"], drive_files.get(name))

    # Download new / changed Drive files
    for name, dfile in drive_files.items():
        lpath = os.path.join(LOCAL_PATH, name)
        if name not in local_files or dfile.get("md5Checksum") != local_files[name]["hash"]:
            download_file(service, dfile, LOCAL_PATH)

    print("\n✅ Sync complete.")


if __name__ == "__main__":
    sync_two_way()