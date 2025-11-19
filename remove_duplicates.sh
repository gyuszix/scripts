#!/usr/bin/env bash

# Directory to scan (Downloads)
TARGET_DIR="$HOME/Downloads"

echo "Scanning $TARGET_DIR for duplicates..."

# Generate hashes and find duplicate files
declare -A filehash

while IFS= read -r -d '' file; do
  hash=$(sha256sum "$file" | awk '{print $1}')
  if [[ -n "${filehash[$hash]}" ]]; then
    echo "Duplicate found:"
    echo "  Original: ${filehash[$hash]}"
    echo "  Removing: $file"
    rm "$file"
  else
    filehash[$hash]="$file"
  fi
done < <(find "$TARGET_DIR" -type f -print0)

echo "Done. All duplicates removed."
