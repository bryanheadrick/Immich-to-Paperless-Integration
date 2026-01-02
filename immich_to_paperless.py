#!/usr/bin/env python3
"""
Script to find documents and receipts in Immich using smart search
and copy them to Paperless-NGX consume folder
"""

import os
import shutil
import requests
import json
from pathlib import Path
from datetime import datetime

# Configuration from environment variables
IMMICH_API_URL = os.getenv("IMMICH_API_URL", "http://localhost:2283/api")
IMMICH_API_KEY = os.getenv("IMMICH_API_KEY", "your-api-key-here")
IMMICH_DATA_PATH = os.getenv("IMMICH_DATA_PATH", "/data")
PAPERLESS_CONSUME_DIR = os.getenv("PAPERLESS_CONSUME_PATH", os.path.expanduser("~/paperless/consume"))

# Search queries for documents and receipts
SEARCH_QUERIES = [
    "document",
    "receipt", 
    "invoice",
    "bill",
    "paper",
    "text document"
]

# Keep track of already processed files
PROCESSED_FILE = os.path.expanduser("~/.immich_paperless_processed.txt")

def translate_immich_path(immich_path):
    """
    Translate Immich's container path to the mounted volume path
    Example: /data/upload/... -> /immich-data/upload/...
    """
    # Immich typically stores files under /data in its container
    # We mount that to IMMICH_DATA_PATH in our container
    if immich_path.startswith('/data'):
        return immich_path.replace('/data', IMMICH_DATA_PATH, 1)
    return immich_path

def load_processed_assets():
    """Load list of already processed asset IDs"""
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f:
            return set(line.strip() for line in f)
    return set()

def save_processed_asset(asset_id):
    """Save processed asset ID to file"""
    with open(PROCESSED_FILE, 'a') as f:
        f.write(f"{asset_id}\n")

def smart_search(query):
    """Use Immich's smart search to find assets matching query"""
    url = f"{IMMICH_API_URL}/search/smart"
    headers = {
        "x-api-key": IMMICH_API_KEY,
        "Content-Type": "application/json"
    }
    
    data = {
        "query": query,
        "page": 1,
        "size": 100
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        # API returns different structures depending on version
        if isinstance(result, dict):
            assets = result.get('assets', {}).get('items', [])
        else:
            assets = result
            
        return assets
    except Exception as e:
        print(f"Error searching for '{query}': {e}")
        return []

def get_asset_info(asset_id):
    """Get detailed asset information including file path"""
    url = f"{IMMICH_API_URL}/assets/{asset_id}"
    headers = {"x-api-key": IMMICH_API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error getting asset info for {asset_id}: {e}")
        return None

def copy_to_paperless(immich_path, asset_id, original_filename):
    """Copy file to Paperless consume folder with timestamp"""
    # Translate Immich container path to our mounted path
    source_path = translate_immich_path(immich_path)
    
    if not os.path.exists(source_path):
        print(f"  ⚠️  Source file not found: {source_path}")
        print(f"      (Original path: {immich_path})")
        return False
    
    # Create consume directory if it doesn't exist
    os.makedirs(PAPERLESS_CONSUME_DIR, exist_ok=True)
    
    # Create filename with timestamp to avoid conflicts
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_ext = Path(original_filename).suffix
    dest_filename = f"immich_{timestamp}_{asset_id}{file_ext}"
    dest_path = os.path.join(PAPERLESS_CONSUME_DIR, dest_filename)
    
    try:
        shutil.copy2(source_path, dest_path)
        print(f"  ✓ Copied to: {dest_filename}")
        return True
    except Exception as e:
        print(f"  ✗ Error copying file: {e}")
        return False

def main():
    print(f"🔍 Searching Immich for documents and receipts...")
    print(f"📁 Paperless consume folder: {PAPERLESS_CONSUME_DIR}\n")
    
    processed_assets = load_processed_assets()
    all_assets = {}
    
    # Search for each query
    for query in SEARCH_QUERIES:
        print(f"Searching for: {query}")
        assets = smart_search(query)
        
        for asset in assets:
            asset_id = asset.get('id')
            if asset_id and asset_id not in all_assets:
                all_assets[asset_id] = asset
        
        print(f"  Found {len(assets)} results")
    
    print(f"\n📊 Total unique assets found: {len(all_assets)}")
    print(f"📊 Already processed: {len(processed_assets)}")
    
    new_assets = {k: v for k, v in all_assets.items() if k not in processed_assets}
    print(f"📊 New assets to process: {len(new_assets)}\n")
    
    if not new_assets:
        print("✓ No new documents to process!")
        return
    
    copied_count = 0
    
    for asset_id, asset in new_assets.items():
        # Get full asset info with file path
        asset_info = get_asset_info(asset_id)
        if not asset_info:
            continue
        
        original_path = asset_info.get('originalPath')
        original_filename = asset_info.get('originalFileName', 'unknown')
        
        print(f"\n📄 {original_filename}")
        print(f"   Path: {original_path}")
        
        if original_path:
            if copy_to_paperless(original_path, asset_id, original_filename):
                save_processed_asset(asset_id)
                copied_count += 1
    
    print(f"\n✅ Done! Copied {copied_count} new documents to Paperless")

if __name__ == "__main__":
    main()