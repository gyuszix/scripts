from __future__ import print_function
import os, io, hashlib
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from drive_auth import get_service

# === CONFIGURATION ===
LOCAL_PATH = "/Users/gyuszix/Documents/ObsidianVault/Vault-Mk1"
DRIVE_FOLDER_NAME = "ObsidianVaultGoogleDrive"
EXCLUDE_FILES = {".DS_Store", "workspace.json", "appearance.json", "app.json"}
EXCLUDE_EXTENSIONS = {".log"}
# ======================

def should_skip(name):
    return (
        name in EXCLUDE_FILES
        or any(name.endswith(ext) for ext in EXCLUDE_EXTENSIONS)
        or name.startswith(".")
    )

def file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def ensure_folder(service, name):
    resp = service.files().list(
        q=f"name='{name}' and mimeType='application/vnd.google-apps.folder'",
        fields="files(id)"
    ).execute()
    if resp["files"]:
        return resp["files"][0]["id"]
    body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    return service.files().create(body=body, fields="id").execute()["id"]

def list_drive_files(service, folder_id):
    files, token = {}, None
    while True:
        r = service.files().list(
            q=f"'{folder_id}' in parents and mimeType!='application/vnd.google-apps.folder'",
            fields="nextPageToken, files(id,name,md5Checksum,modifiedTime)",
            pageToken=token,
        ).execute()
        for f in r["files"]:
            files[f["name"]] = f
        token = r.get("nextPageToken")
        if not token:
            break
    return files

def upload_or_update(service, folder_id, path, drive_file=None):
    name = os.path.basename(path)
    if should_skip(name):
        return
    media = MediaFileUpload(path, resumable=True)
    local_hash = file_md5(path)
    if not drive_file:
        service.files().create(body={"name": name, "parents": [folder_id]}, media_body=media).execute()
        print(f"☁️  Uploaded: {name}")
    elif drive_file.get("md5Checksum") != local_hash:
        service.files().update(fileId=drive_file["id"], media_body=media).execute()
        print(f"🔄 Updated on Drive: {name}")
    else:
        print(f"✅ Unchanged: {name}")

def download_file(service, drive_file, local_dir):
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
    service = get_service()
    folder_id = ensure_folder(service, DRIVE_FOLDER_NAME)
    print(f"\n🔄 Two-way sync between '{LOCAL_PATH}' and Drive '{DRIVE_FOLDER_NAME}'\n")

    drive_files = list_drive_files(service, folder_id)
    local_files = {
        f: {"path": os.path.join(LOCAL_PATH, f), "hash": file_md5(os.path.join(LOCAL_PATH, f))}
        for f in os.listdir(LOCAL_PATH)
        if os.path.isfile(os.path.join(LOCAL_PATH, f)) and not should_skip(f)
    }

    # Upload new / changed locals
    for name, info in local_files.items():
        upload_or_update(service, folder_id, info["path"], drive_files.get(name))

    # Download new / changed drives
    for name, dfile in drive_files.items():
        lpath = os.path.join(LOCAL_PATH, name)
        if name not in local_files or dfile.get("md5Checksum") != local_files[name]["hash"]:
            download_file(service, dfile, LOCAL_PATH)

    print("\n✅ Sync complete.")

if __name__ == "__main__":
    sync_two_way()