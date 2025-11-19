# Railway File Access Guide

**Problem:** Files created but not visible in browser (especially VOC files)

---

## Option 1: Railway CLI (Easiest)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to your project
railway link

# List files
railway run ls -la /app/outputs/

# Download specific file
railway run cat /app/outputs/VoC_Report_*.md > local_file.md

# Or download entire outputs directory
railway run tar -czf outputs.tar.gz /app/outputs/
railway run cat outputs.tar.gz > outputs.tar.gz
```

---

## Option 2: Railway Web Dashboard

1. Go to Railway dashboard → Your project
2. Click on your service (intercom-gamma-analyzer)
3. Go to **Settings** → **Volumes**
4. Click **"Open Volume"** or **"Browse Files"**
5. Navigate to `/app/outputs/` or `/mnt/persistent/outputs/`

**Note:** Files might be in:
- `/app/outputs/` (ephemeral - lost on restart)
- `/mnt/persistent/outputs/` (persistent volume - survives restarts)

---

## Option 3: Railway Shell (SSH-like)

```bash
# Open shell
railway shell

# Navigate to outputs
cd /app/outputs

# List files
ls -la

# Find VOC files
find . -name "*VoC*" -o -name "*voice_of_customer*"

# View file
cat voice_of_customer_*.json | head -100

# Download via Railway CLI
railway run cat /app/outputs/voice_of_customer_*.json > local_file.json
```

---

## Finding Your Files

### Sample-Mode Files (Should be visible):
```
/app/outputs/executions/<execution_id>/sample_mode_*.json
/app/outputs/executions/<execution_id>/sample_mode_*.log
```

### VOC Files (Might be in root, not executions/):
```
/app/outputs/VoC_Report_*.md          ← OLD LOCATION (before fix)
/app/outputs/VoC_Analysis_*.json      ← OLD LOCATION (before fix)
/app/outputs/executions/<id>/voice_of_customer_*.md  ← NEW LOCATION (after fix)
```

---

## After Next Deploy (With Fixes)

All files will be in:
```
/app/outputs/executions/<execution_id>/
  ├── voice_of_customer_*.md
  ├── voice_of_customer_*.json
  ├── voice_of_customer_*.log
  ├── agent_thinking_*.log
  └── agent_thinking_*.observability.json  ← NEW! Structured data
```

**All visible in browser Files tab!**

