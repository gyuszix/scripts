#!/usr/bin/env bash

# Paths – change only if you move things
LOCAL_PATH="/Users/gyuszix/Documents/ObsidianVault/Vault-Mk1"
REMOTE="vaultdrive:ObsidianVault"

echo "========== Obsidian Vault Sync =========="
echo "Choose an option:"
echo ""
echo "1) One-way restore (cloud → local)"
echo "     Use if your local folder was deleted or corrupted."
echo "     SAFE – will NOT delete anything on Google Drive."
echo ""
echo "2) Normal Bisync (two-way sync)"
echo "     Use for daily syncing – pushes changes both ways."
echo "     WARNING: deleted local files will be deleted on Drive."
echo ""
echo "3) First-time / Resync (forces full match)"
echo "     Use only on FIRST sync or after sync errors."
echo "     WARNING: can overwrite both sides."
echo ""
echo "4) Dry run – see what would happen (no changes)"
echo "     Useful for checking before real sync."
echo ""
read -p "Select an option (1-4): " choice

case "$choice" in
1)
  echo "Restoring files from Drive to Local..."
  rclone copy "$REMOTE" "$LOCAL_PATH" --verbose
  echo "DONE: Local folder has been restored."
  ;;
2)
  echo "Running normal bisync..."
  rclone bisync "$LOCAL_PATH" "$REMOTE" --verbose
  ;;
3)
  echo "Running bisync with --resync (dangerous!)..."
  rclone bisync "$LOCAL_PATH" "$REMOTE" --verbose --resync
  ;;
4)
  echo "Dry run (no changes will be made)..."
  rclone bisync "$LOCAL_PATH" "$REMOTE" --dry-run --verbose
  ;;
*)
  echo "Invalid option. Exiting."
  ;;
esac

echo "=========================================="
echo "Finished."
