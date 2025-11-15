# Railway Persistent Storage Setup (5 Minutes)
**So Your Files Don't Disappear After Every Deploy**

**Cost:** ~$5-10/month  
**Benefit:** Keep ALL past analysis runs forever

---

## The Problem

**Current:** Files saved to `/app/outputs/` get WIPED on every Railway redeploy.

```
You run analysis → files saved
    ↓
You push code update
    ↓
Railway redeploys
    ↓
ALL YOUR FILES: GONE 💥
```

---

## The Solution: Railway Persistent Volume

**1. Go to Railway Dashboard**
- Click your service (`agile-exploration`)
- Go to "Variables" tab

**2. Add Volume**
- Click "New Variable"
- Select "Add Volume"
- Name: `persistent-storage`
- Mount path: `/mnt/persistent`
- Size: 10 GB (more than enough)
- Click "Add"

**3. Set Environment Variable**
Add this variable:
```
PERSISTENT_OUTPUTS=true
```

**4. Redeploy**
Railway will automatically redeploy with the persistent volume.

---

## What Changes

**Before (Ephemeral):**
```
/app/outputs/  ← WIPED on every redeploy!
```

**After (Persistent):**
```
/mnt/persistent/outputs/  ← SURVIVES redeploys! ✅
```

**Your files:**
- ✅ Analysis results from last week: STILL THERE
- ✅ Analysis results from last month: STILL THERE
- ✅ All .log files for debugging: ACCESSIBLE
- ✅ SQLite database with execution history: PERSISTS

---

## Cost

**Railway Volume Pricing:**
- 10 GB: ~$5/month
- 20 GB: ~$10/month

**For your use case:** 10 GB is MORE than enough
- Each analysis: ~10 MB
- 1,000 analyses: ~10 GB
- You run ~4-8 per week = years of storage

---

## Testing After Setup

**1. Run an analysis:**
```bash
voice-of-customer --time-period week
```

**2. Push a code update to Railway**

**3. Check if files still exist:**
- Go to Railway UI
- Click "Files" tab
- Files should STILL BE THERE! ✅

**4. Execution history will work:**
- Dropdown shows all past runs
- Click any past run → files load
- Download .log files anytime

---

## Alternative: Just Download Files Immediately

**If you don't want to pay $5/month:**

**After EVERY analysis:**
1. Go to Files tab
2. Download .json and .log files
3. Store locally

**Pro:** Free  
**Con:** Manual process after each run

---

## My Recommendation

**ADD THE VOLUME.** It's $5/month and you'll never lose data again.

Then execution history, SQLite tracking, and file browser all ACTUALLY WORK.

Without it, everything resets on redeploy and you're wasting time debugging ephemeral storage issues.

