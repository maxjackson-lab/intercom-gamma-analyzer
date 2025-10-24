# Intercom Links and UI Improvements Plan

## Problems to Solve

### 1. **Intercom Links Not Prominent in Gamma Slides**
- Links are embedded in text but not visually prominent
- Gamma doesn't make them clickable/highlighted enough
- Need to instruct Gamma to format links as prominent elements

### 2. **Web UI Tabs Not Updating**
- Gamma tab doesn't show clickable link
- Output tab doesn't show file info
- Download tab empty/not functional

### 3. **Poor Filenames**
- Using generic timestamps (e.g., `voc_analysis_20241024_163045.json`)
- Should use descriptive names (e.g., `VoC_Week_42_Oct_17-24.json`)
- Hard to identify which file is which

### 4. **No Interactive Links in Web UI**
- Can't click to open files
- Can't download from browser
- URLs shown as text, not hyperlinks

---

## Solution Architecture

### **Part 1: Gamma Prompt Enhancement**
**File**: `src/config/gamma_prompts.py`

**Changes Needed:**
1. Add explicit link formatting instructions to additional_instructions
2. Emphasize prominent, clickable link placement
3. Request button-style or highlighted link formatting

**Expected Result:**
- Gamma slides will have bold, clickable "View in Intercom" links
- Links will be on separate lines, not buried in paragraphs
- Visual emphasis (icons, colors, buttons)

---

### **Part 2: Web UI Tab Population**
**Files**: 
- `static/app.js` (main changes)
- `static/styles.css` (styling)
- `server.py` (add download endpoint)

**Changes Needed:**

#### A. JavaScript Tab Updates (`static/app.js`)
1. **Parse output for key information:**
   - Gamma URL (regex: `Gamma URL:\s*(https://gamma.app/[^\s]+)`)
   - Output file paths (regex: `saved to:\s*([^\n]+)`)
   - Markdown files, JSON files, URL files

2. **Populate Gamma Tab:**
   ```javascript
   - Extract Gamma URL from output
   - Create clickable button/link
   - Show generation metadata (credits, time)
   - Display URL for copying
   ```

3. **Populate Output Tab:**
   ```javascript
   - Show primary output file with nice filename
   - Display file size, generation time
   - Add "View JSON" button
   - Show file path
   ```

4. **Populate Download Tab:**
   ```javascript
   - List all generated files (JSON, MD, TXT)
   - Group by type (Analysis, Markdown, URLs)
   - Add download buttons for each
   - Show file sizes
   ```

5. **Add download functionality:**
   ```javascript
   async function downloadFile(filePath) {
       // Fetch file from server
       // Trigger browser download
   }
   ```

#### B. Backend Download Endpoint (`server.py`)
```python
@app.route('/download')
async def download_file():
    file_path = request.args.get('file')
    # Validate path is in outputs directory
    # Return file for download
```

#### C. CSS Styling (`static/styles.css`)
```css
.gamma-link-button {
    /* Prominent button styling */
}

.download-item {
    /* File list item styling */
}

.file-type-badge {
    /* Badge for file types */
}
```

---

### **Part 3: Descriptive Filenames**
**Files**: `src/main.py` (multiple functions)

**Changes Needed:**

Replace timestamp-based filenames with descriptive ones:

**Current:**
```python
output_file = output_dir / f"voc_analysis_{timestamp}.json"
gamma_url_file = output_dir / f"gamma_url_{timestamp}.txt"
```

**New:**
```python
output_file = output_dir / f"VoC_Analysis_Week_{week_id}.json"
gamma_url_file = output_dir / f"Gamma_URL_VoC_Week_{week_id}.txt"
markdown_file = output_dir / f"Report_VoC_Week_{week_id}.md"
```

**Pattern for all analysis types:**
- VOC: `VoC_Week_{week_id}_{start_date}-{end_date}`
- Canny: `Canny_Analysis_{start_date}-{end_date}`
- Topic-based: `Topic_Analysis_{period_label}`
- Custom: `Custom_Analysis_{start_date}-{end_date}`

---

### **Part 4: Enhanced Link Formatting in Examples**
**File**: `src/agents/output_formatter_agent.py`

**Changes Needed:**

Current format:
```markdown
1. "Preview text..." - [View conversation](url)
```

Enhanced format:
```markdown
1. "Preview text..."  
   **[📎 View in Intercom →](url)**
```

Or use a more prominent format:
```markdown
**Example 1:**
> "Preview text..."

[🔗 Open this conversation in Intercom](url)

---
```

---

## Implementation Order

1. ✅ **Gamma Prompts** (easiest, high impact)
   - Update additional_instructions in gamma_prompts.py
   - Test with next Gamma generation

2. ✅ **Descriptive Filenames** (medium effort, good UX)
   - Update all filename generation in main.py
   - Ensure backwards compatibility

3. ✅ **Web UI Tab Population** (complex, best UX)
   - Update app.js with parsing logic
   - Add CSS styling
   - Add download endpoint to server.py
   - Test in browser

4. ✅ **Enhanced Link Formatting** (optional polish)
   - Update output_formatter_agent.py
   - Makes links even more visible in markdown

---

## Testing Plan

### Test 1: Gamma Links Prominence
```bash
python -m src.main topic-based --start-date 2024-10-17 --end-date 2024-10-24 --generate-gamma
```
**Verify:**
- Open Gamma presentation
- Check if "View conversation" links are clickable
- Verify links stand out visually

### Test 2: Descriptive Filenames
```bash
python -m src.main voc-analysis --generate-gamma
```
**Verify:**
- Check outputs/ directory
- Filenames should be descriptive, not timestamps
- Easy to identify which analysis it is

### Test 3: Web UI Tabs
```bash
# Start web server
python server.py

# Run analysis through web UI
# Verify:
# - Gamma tab shows clickable link
# - Output tab shows file info
# - Download tab has download buttons
```

---

## Rollback Plan

If any issues arise:

1. **Gamma Prompts**: Revert additional_instructions changes
2. **Filenames**: Keep timestamp pattern as fallback
3. **Web UI**: Feature flag to disable tab parsing
4. **Link Format**: Keep existing format

---

## Estimated Effort

- **Gamma Prompts**: 15 minutes
- **Filenames**: 30 minutes  
- **Web UI**: 1-2 hours (most complex)
- **Testing**: 30 minutes

**Total**: ~2.5-3 hours

---

## Priority

**High Priority:**
1. Gamma prompts (quick win)
2. Descriptive filenames (quality of life)

**Medium Priority:**
3. Web UI tabs (nice to have, complex)

**Low Priority:**
4. Enhanced link formatting (polish)

---

## Questions to Confirm

1. Do you want ALL four improvements, or just some?
2. For filenames: Do you want timestamps removed completely, or kept as suffix?
3. For web UI: Should we add a file browser/manager?
4. For Gamma links: Any specific format/style preference?

---

## Ready to Implement

Once confirmed, I'll implement in this order:
1. Gamma prompts enhancement
2. Descriptive filenames
3. Web UI tab updates
4. Link formatting polish

Let me know if you want to proceed with all of these, or pick specific ones!


