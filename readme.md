# Immich to Paperless Integration

Automatically identify and copy documents and receipts from Immich to Paperless-NGX using AI-powered smart search.

## What It Does

This tool uses Immich's smart search API to find images containing documents, receipts, invoices, and bills, then automatically copies them to your Paperless-NGX consume folder for processing.

- 🔍 Uses Immich's AI to identify documents
- 📄 Searches for receipts, invoices, bills, and more
- 🚀 Copies files directly to Paperless consume folder
- ✅ Tracks processed files to avoid duplicates
- 🐳 Runs in Docker alongside Immich and Paperless

## Prerequisites

- Immich running in Docker
- Paperless-NGX running in Docker
- Both on the same host machine
- Immich API key

## Setup Instructions

### Step 1: Create API Key in Immich

1. Open Immich web interface
2. Go to **Settings** → **Account Settings** → **API Keys**
3. Click **New API Key**
4. Copy the generated key

### Step 2: Find Required Paths

#### Find Immich Data Path

```bash
docker inspect immich_server | grep -A 10 '"Mounts"' | grep Source
```

Look for the source path that maps to `/data` or `/usr/src/app/upload` in the container.

Example output:
```
"Source": "/mnt/immich/upload"
```

#### Find Paperless Consume Path

```bash
docker ps | grep paperless  # Get the container name
docker inspect <paperless-container-name> | grep -A 10 '"Mounts"' | grep consume
```

Look for the consume folder path.

Example output:
```
"Source": "/opt/paperless/consume"
```

#### Find Immich Network Name

```bash
docker network ls | grep immich
```

Example output:
```
immich_default
```

### Step 3: Create Project Directory

```bash
mkdir ~/immich-to-paperless
cd ~/immich-to-paperless
```

### Step 4: Download Files

Download the following files to this directory:
- `immich_to_paperless.py` (the Python script)
- `docker-compose.yml` (see below)
- `.env` (see below)

### Step 5: Create `docker-compose.yml`

Create `docker-compose.yml` with the following content:

```yaml
name: immich-to-paperless

services:
  immich-to-paperless:
    container_name: immich_to_paperless
    image: python:3.11-slim
    restart: "no"
    networks:
      - immich_default  # Change if your network name is different
    volumes:
      # UPDATE THESE PATHS based on Step 2
      - /mnt/immich/upload:/immich-data:ro  # Immich data path (read-only)
      - /opt/paperless/consume:/paperless-consume  # Paperless consume path
      - ./immich_to_paperless.py:/script/immich_to_paperless.py:ro
    environment:
      IMMICH_API_URL: http://immich_server:2283/api
      IMMICH_API_KEY: ${IMMICH_API_KEY}
      IMMICH_DATA_PATH: /immich-data
      PAPERLESS_CONSUME_PATH: /paperless-consume
    command: >
      sh -c "pip install requests &&
             python3 /script/immich_to_paperless.py"

networks:
  immich_default:  # Change if your network name is different
    external: true
```

**Important:** Update the following in the file above:
- Volume paths (both Immich and Paperless paths from Step 2)
- Network name (from Step 2)
- Container name `immich_server` if yours is different

### Step 6: Create `.env` File

Create `.env` file:

```bash
IMMICH_API_KEY=your-api-key-from-step-1
```

Replace `your-api-key-from-step-1` with the actual API key from Step 1.

### Step 7: Place the Python Script

Place the `immich_to_paperless.py` file in the `~/immich-to-paperless` directory.

## Usage

### Run On-Demand

From the `~/immich-to-paperless` directory:

```bash
docker compose run --rm immich-to-paperless
```

This will:
1. Search Immich for documents/receipts
2. Show you what it found
3. Copy new documents to Paperless
4. Track processed files to avoid duplicates

### First Run

The first time you run it, it will process all existing documents. Subsequent runs will only process new documents.

### Check What Was Found

The script outputs:
- Number of total assets found
- Number already processed
- Number of new assets to copy
- Details of each file copied

Example output:
```
🔍 Searching Immich for documents and receipts...
📁 Paperless consume folder: /paperless-consume

Searching for: document
  Found 15 results
Searching for: receipt
  Found 8 results

📊 Total unique assets found: 20
📊 Already processed: 5
📊 New assets to process: 15

📄 receipt_2024_01_15.jpg
   Path: /data/upload/2024/receipts/receipt_2024_01_15.jpg
  ✓ Copied to: immich_20260101_180000_abc123.jpg

✅ Done! Copied 15 new documents to Paperless
```

## Running on a Schedule

### Option 1: Cron Job on Host

Create a cron job to run periodically:

```bash
crontab -e
```

Add this line to run every 6 hours:

```
0 */6 * * * cd /home/your-username/immich-to-paperless && /usr/bin/docker compose run --rm immich-to-paperless >> /tmp/immich-paperless.log 2>&1
```

### Option 2: Keep Container Running with Cron

Modify the `docker-compose.yml` service:

```yaml
  immich-to-paperless:
    # ... other settings ...
    restart: unless-stopped
    environment:
      # ... existing env vars ...
      CRON_SCHEDULE: "0 */6 * * *"  # Every 6 hours
    command: >
      sh -c "
      apt-get update && apt-get install -y cron &&
      pip install requests &&
      echo '0 */6 * * * python3 /script/immich_to_paperless.py >> /var/log/cron.log 2>&1' | crontab - &&
      cron &&
      tail -f /var/log/cron.log
      "
```

Then:
```bash
docker compose up -d
```

## Customization

### Change Search Queries

Edit the `SEARCH_QUERIES` list in `immich_to_paperless.py`:

```python
SEARCH_QUERIES = [
    "document",
    "receipt", 
    "invoice",
    "bill",
    "paper",
    "text document",
    "business card",  # Add custom searches
    "contract",
]
```

### Change File Naming

Files are copied with names like: `immich_20260101_143022_abc123.jpg`

To change this, edit the `copy_to_paperless` function in the script:

```python
dest_filename = f"immich_{timestamp}_{asset_id}{file_ext}"
```

## Troubleshooting

### No Documents Found

**Problem:** Script runs but finds 0 albums/documents

**Solutions:**
1. Make sure Immich has finished analyzing your photos (check Jobs in Immich UI)
2. Try searching manually in Immich for "document" to verify smart search works
3. Check that your photos actually contain documents/text

### Source File Not Found

**Problem:** Error message "⚠️ Source file not found"

**Solutions:**
1. Verify Immich data path is correct:
   ```bash
   docker inspect immich_server | grep -A 10 '"Mounts"'
   ```
2. Make sure the volume mount in docker-compose.yml matches exactly
3. Check file permissions - the script container needs read access

### API Connection Failed

**Problem:** Can't connect to Immich API

**Solutions:**
1. Verify network name is correct (should match Immich's network)
2. Check Immich container name: `docker ps | grep immich`
3. Update `IMMICH_API_URL` if your container has a different name
4. Verify API key is correct

### Files Not Appearing in Paperless

**Solutions:**
1. Check Paperless consume folder path is correct
2. Verify Paperless has permissions to read the consume folder
3. Check Paperless logs: `docker logs paperless-ngx`
4. Make sure Paperless consumption is enabled in settings

### Network Not Found

**Problem:** Error about network not found

**Solution:**
```bash
# List all networks
docker network ls

# Update docker-compose.yml with the correct network name
```

## File Tracking

The script keeps track of processed files in `~/.immich_paperless_processed.txt` inside the container. This file persists in the container but not across container recreations.

To persist the tracking file, add a volume:

```yaml
volumes:
  - ./processed.txt:/root/.immich_paperless_processed.txt
```

## Advanced Configuration

### Use External Immich URL

If you prefer not to use Docker networks:

```yaml
services:
  immich-to-paperless:
    # Remove networks section
    network_mode: host
    environment:
      IMMICH_API_URL: http://localhost:2283/api  # or https://your-domain.com/api
      # ... other vars
```

### Dry Run Mode

To see what would be copied without actually copying:

Add this to the script or modify the `copy_to_paperless` function to return `True` without actually copying.

## Security Notes

- API key is stored in `.env` file - keep this file secure
- Script has read-only access to Immich data
- Script has write access to Paperless consume folder only

## Support

If you encounter issues:

1. Check the troubleshooting section
2. Verify all paths and settings
3. Check Docker logs: `docker compose logs`
4. Ensure Immich smart search is working in the UI

## License

This integration script is provided as-is for personal use.