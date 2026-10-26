#!/usr/bin/env python3
import json
import os
import re
import shutil
import urllib.request
import glob
from datetime import datetime

# --- CONFIGURATION ---
REPOS_TO_CHECK = [
    "storytold/cadcraft",
    "storytold/deckcraft",
    "storytold/designcraft"
    "storytold/effectcraft",
    "storytold/figcraft",
    "storytold/filmcraft"
    "storytold/gridcraft",
    "storytold/lightcraft",
    "storytold/pdfcraft"
    "storytold/photocraft",
    "storytold/soundcraft",
    "storytold/vectorcraft"
    "storytold/wordcraft"
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
    """Fetches the latest release data and looks for a specific zipped web asset."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    
    req = urllib.request.Request(
        url, 
        headers={
            "User-Agent": "macOS-Update-Script",
            "Accept": "application/vnd.github+json"
        }
    )
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
            tag_name = data.get("tag_name")
            if not tag_name:
                print(f"  ❌ No tag_name found for {repo}.")
                return None, None
                
            # Strip potential leading 'v' to match your asset name format (0.12.1)
            version_clean = tag_name.lstrip('v')
            repo_short_name = repo.split('/')[-1]
            
            # Expected asset pattern, e.g., "gridcraft-web-0.12.1.zip"
            target_asset_name = f"{repo_short_name}-web-{version_clean}.zip"
            
            # Look through the release assets array
            assets = data.get("assets", [])
            for asset in assets:
                if asset.get("name") == target_asset_name:
                    download_url = asset.get("browser_download_url")
                    return tag_name, download_url
                    
            print(f"  ❌ Release {tag_name} found, but missing required asset: {target_asset_name}")
            return None, None

    except Exception as e:
        print(f"  ❌ Error fetching {repo} from GitHub API: {e}")
        return None, None

def load_local_versions():
    """Reads the key-value version file into a dictionary."""
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
    """Retains only the single most recent backup file."""
    backup_pattern = f"{LOCAL_VERSION_FILE}.*.bak"
    all_backups = glob.glob(backup_pattern)
    
    if len(all_backups) <= 1:
        return
        
    all_backups.sort(key=os.path.getmtime)
    backups_to_remove = all_backups[:-1]
    
    print(f"\n🧹 Cleaning up {len(backups_to_remove)} older backup files...")
    for old_bak in backups_to_remove:
        try:
            os.remove(old_bak)
            print(f"  Removed old backup: {os.path.basename(old_bak)}")
        except Exception as e:
            print(f"  ⚠️ Could not remove {old_bak}: {e}")

def main():
    local_versions = load_local_versions()
    updated_versions = local_versions.copy()
    changes_made = False

    print(f"Starting nightly check for {len(REPOS_TO_CHECK)} repositories...")

    for repo in REPOS_TO_CHECK:
        print(f"\nChecking: {repo}")
        local_ver = local_versions.get(repo, "0.0.0")
        print(f"  Local version: {local_ver}")

        remote_ver, download_url = get_latest_github_release(repo)
        if not remote_ver or not download_url:
            print("  Skipping repository due to missing info or assets.")
            continue
        print(f"  Latest remote: {remote_ver}")

        if parse_version(remote_ver) > parse_version(local_ver):
            print(f"  🚀 New version detected! Downloading custom zip asset...")
            
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            repo_short_name = repo.split('/')[-1]
            
            # Matches target zip format for local storage
            filename = f"{repo_short_name}-web-{remote_ver.lstrip('v')}.zip"
            dest_path = os.path.join(DOWNLOAD_DIR, filename)

            try:
                urllib.request.urlretrieve(download_url, dest_path)
                print(f"  ✅ Asset downloaded to: {dest_path}")
                
                updated_versions[repo] = remote_ver
                changes_made = True
            except Exception as e:
                print(f"  ❌ Failed to download asset: {e}")
        else:
            print("  ✅ Up to date.")

    if changes_made:
        print("\n💾 Finalizing files...")
        
        if os.path.exists(LOCAL_VERSION_FILE):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            backup_file = f"{LOCAL_VERSION_FILE}.{timestamp}.bak"
            
            try:
                shutil.copy2(LOCAL_VERSION_FILE, backup_file)
                print(f"  Created backup file at: {backup_file}")
            except Exception as e:
                print(f"  ⚠️ Warning: Could not create backup file: {e}")
        
        save_local_versions(updated_versions)
        print("  Local tracking file updated successfully.")
        prune_old_backups()
    else:
        print("\n🔒 No updates needed. Tracking file unchanged.")

if __name__ == "__main__":
    main()
