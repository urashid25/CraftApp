#!/usr/bin/env python3
import json
import os
import re
import shutil
import urllib.request
import glob
from datetime import datetime

# --- CONFIGURATION ---
# List all the repositories you want to monitor nightly
REPOS_TO_CHECK = [
    "gohugoio/hugo",
    "facebook/react",
    "python/cpython"
]

LOCAL_VERSION_FILE = os.path.expanduser("~/.local_repo_versions.txt")
DOWNLOAD_DIR = os.path.expanduser("~/Downloads")
# ---------------------

def parse_version(version_str):
    """Cleans and extracts semver numbers for accurate comparison."""
    match = re.search(r"(\d+\.\d+\.\d+)", version_str)
    if match:
        return tuple(map(int, match.group(1).split(".")))
    return (0, 0, 0)

def get_latest_github_release(repo):
    """Fetches the latest release data from the public GitHub API."""
    url = f"https://github.com{repo}/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "macOS-Update-Script"})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return data.get("tag_name"), data.get("tarball_url")
    except Exception as e:
        print(f"  ❌ Error fetching {repo} from GitHub: {e}")
        return None, None

def load_local_versions():
    """Reads the key-value version file into a Python dictionary."""
    versions = {}
    if os.path.exists(LOCAL_VERSION_FILE):
        with open(LOCAL_VERSION_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line and ":" in line:
                    repo, ver = line.split(":", 1)
                    versions[repo.strip()] = ver.strip()
    return versions

def save_local_versions(versions):
    """Saves the dictionary back to the flat text file."""
    with open(LOCAL_VERSION_FILE, "w") as f:
        for repo, ver in sorted(versions.items()):
            f.write(f"{repo}: {ver}\n")

def prune_old_backups():
    """Finds all local backup files and retains only the single most recent one."""
    # Matches patterns like: ~/.local_repo_versions.txt.*.bak
    backup_pattern = f"{LOCAL_VERSION_FILE}.*.bak"
    all_backups = glob.glob(backup_pattern)
    
    if len(all_backups) <= 1:
        return  # Nothing to clean up
        
    # Sort backups by creation/modification time (oldest first)
    all_backups.sort(key=os.path.getmtime)
    
    # Slice the list to target everything except the absolute newest backup
    backups_to_remove = all_backups[:-1]
    
    print(f"\n🧹 Cleaning up {len(backups_to_remove)} older backup files...")
    for old_bak in backups_to_remove:
        try:
            os.remove(old_bak)
            print(f"  Removed old backup: {os.path.basename(old_bak)}")
        except Exception as e:
            print(f"  ⚠️ Could not remove {old_bak}: {e}")

def main():
    # 1. Load existing tracking records
    local_versions = load_local_versions()
    updated_versions = local_versions.copy()
    changes_made = False

    print(f"Starting nightly check for {len(REPOS_TO_CHECK)} repositories...")

    # 2. Loop through and check all listed repositories
    for repo in REPOS_TO_CHECK:
        print(f"\nChecking: {repo}")
        local_ver = local_versions.get(repo, "0.0.0")
        print(f"  Local version: {local_ver}")

        remote_ver, download_url = get_latest_github_release(repo)
        if not remote_ver or not download_url:
            print("  Skipping due to API error.")
            continue
        print(f"  Latest remote: {remote_ver}")

        # Compare versions
        if parse_version(remote_ver) > parse_version(local_ver):
            print(f"  🚀 New version detected! Downloading...")
            
            # Prep download destination
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            repo_short_name = repo.split('/')[-1]
            filename = f"{repo_short_name}-{remote_ver}.tar.gz"
            dest_path = os.path.join(DOWNLOAD_DIR, filename)

            try:
                urllib.request.urlretrieve(download_url, dest_path)
                print(f"  ✅ Downloaded to: {dest_path}")
                
                # Queue the version update in memory
                updated_versions[repo] = remote_ver
                changes_made = True
            except Exception as e:
                print(f"  ❌ Failed to download package: {e}")
        else:
            print("  ✅ Up to date.")

    # 3. Handle file backup and updates after all checks complete
    if changes_made:
        print("\n💾 Changes detected. Finalizing files...")
        
        if os.path.exists(LOCAL_VERSION_FILE):
            # Generate unique timestamp suffix
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            backup_file = f"{LOCAL_VERSION_FILE}.{timestamp}.bak"
            
            try:
                shutil.copy2(LOCAL_VERSION_FILE, backup_file)
                print(f"  Created new backup file at: {backup_file}")
            except Exception as e:
                print(f"  ⚠️ Warning: Could not create backup file: {e}")
        
        # Save the new version values
        save_local_versions(updated_versions)
        print("  Local tracking file updated successfully.")
        
        # Run cleanup rules
        prune_old_backups()
    else:
        print("\n🔒 No updates needed. Tracking file unchanged.")

if __name__ == "__main__":
    main()
