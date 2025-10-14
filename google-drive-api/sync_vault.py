import os
import time
import hashlib
from googleapiclient.http import MediaFileUpload
from drive_auth import get_service

# === CONFIGURATION ===
LOCAL_PATH = "/Users/gyuszix/Documents/ObsidianVault"  # your local vault folder
DRIVE_FOLDER_NAME = "ObsidianVaultGoogleDrive"          # target Drive folder name

# Exclusions — filenames or extensions to skip
EXCLUDE_FILES = {
    ".DS_Store",
    "workspace.json",
    "appearance.json",
    "app.json",
}
EXCLUDE_EXTENSIONS = {".log"}  # example: skip .log files
# ======================


def should_skip(file_name):
    """Decide whether a file should be skipped."""
    if file_name in EXCLUDE_FILES:
        return True
    if any(file_name.endswith(ext) for ext in EXCLUDE_EXTENSIONS):
        return True
    if file_name.startswith("."):  # skip hidden files like .gitignore
        return True
    return False


def file_md5(path):
    """Compute MD5 hash of a local file."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_folder(service, name):
    """Find or create the folder on Google Drive."""
    resp = service.files().list(
        q=f"name='{name}' and mimeType='application/vnd.google-apps.folder'",
        fields="files(id, name)"
    ).execute()
    if resp["files"]:
        return resp["files"][0]["id"]

    folder_metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    created = service.files().create(body=folder_metadata, fields="id").execute()
    return created["id"]


def upload_or_update(service, parent_id, file_path):
    """Upload or update a single file using MD5 content check."""
    file_name = os.path.basename(file_path)

    # Skip unwanted files
    if should_skip(file_name):
        print(f"Skipped: {file_name}")
        return

    query = f"'{parent_id}' in parents and name='{file_name}'"
    results = service.files().list(
        q=query,
        fields="files(id, name, md5Checksum)"
    ).execute()
    files = results.get("files", [])
    media = MediaFileUpload(file_path, resumable=True)

    local_hash = file_md5(file_path)

    if not files:
        service.files().create(
            body={"name": file_name, "parents": [parent_id]},
            media_body=media,
            fields="id"
        ).execute()
        print(f"Uploaded: {file_name}")
    else:
        drive_file = files[0]
        drive_hash = drive_file.get("md5Checksum")
        if drive_hash != local_hash:
            service.files().update(fileId=drive_file["id"], media_body=media).execute()
            print(f"Updated: {file_name}")
        else:
            print(f"Unchanged: {file_name}")


def sync_vault():
    """Sync all files from your local folder to Drive."""
    service = get_service()
    folder_id = ensure_folder(service, DRIVE_FOLDER_NAME)

    print(f"Syncing '{LOCAL_PATH}' → Google Drive folder '{DRIVE_FOLDER_NAME}' ...\n")
    for root, dirs, files in os.walk(LOCAL_PATH):
        # Skip hidden folders
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for f in files:
            file_path = os.path.join(root, f)
            upload_or_update(service, folder_id, file_path)

    print("\n✅ Sync complete.")


if __name__ == "__main__":
    sync_vault()