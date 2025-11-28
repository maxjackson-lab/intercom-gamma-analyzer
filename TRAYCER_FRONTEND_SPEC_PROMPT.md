# Traycer Specification Prompt: SvelteKit "Sidecar" Migration

**Context:**
We have successfully implemented Phase 1 of our frontend modernization strategy: a "Sidecar" SvelteKit app running alongside our legacy FastAPI frontend. The infrastructure is live:
- Legacy Frontend: `http://app/` (served from `static/`)
- Modern Frontend: `http://app/v2/` (served from `frontend/build/`)
- Repository: Monorepo with `/frontend` and `/deploy/railway_web.py` handling the dual mount.

**The Goal:**
We need a comprehensive technical specification to guide the full migration of features from the legacy `app.js` (Vanilla JS) to the new SvelteKit architecture. This spec will be used by developers to port features one by one without breaking the existing tool.

**Your Task:**
Spec out the full migration plan, architectural standards, and feature parity requirements for the `/v2` frontend.

---

## 🎯 Architecture & Standards

### 1. **Shared State Management**
The legacy app uses a global `currentExecutionId` variable and loose polling functions.
- **Spec Request:** Define how we should manage execution state in SvelteKit.
- **Recommendation:** Use Svelte Stores (`svelte/store`).
- **Requirement:**
  - `executionStore`: Tracks `status`, `executionId`, `logs` (array), and `isPolling`.
  - `toastStore`: Global notification system to replace `showToast()`.
  - **Question:** How do we persist this state across page reloads (localStorage integration)?

### 2. **API Client Layer**
The legacy app has scattered `fetch()` calls in `runAnalysis()`, `pollExecutionStatus()`, etc.
- **Spec Request:** Design a typed API client in `src/lib/api`.
- **Requirement:**
  - Strong TypeScript interfaces for all backend responses (`ExecutionStatus`, `AnalysisResult`).
  - Centralized error handling (auto-toast on failure).
  - **Endpoints to cover:** `/execute`, `/execute/status/{id}`, `/execute/cancel/{id}`, `/outputs`.

### 3. **UI/UX & Styling**
- **Spec Request:** Define the styling strategy.
- **Current:** `styles.css` (global CSS).
- **Target:** Modern component-scoped styles or Tailwind CSS?
- **Question:** Should we adopt a component library (e.g., Skeleton UI, Flowbite, or shadcn-svelte) or keep custom styles?
- **Requirement:** Match the "Hacker Terminal" aesthetic of the current tool but with better responsiveness.

---

## 🛠 Feature Migration Checklist

For each feature below, provide a **Svelte Component Spec** (inputs, outputs, stores used):

### 1. **Configuration Form (`AnalysisForm.svelte`)**
- **Legacy:** `runAnalysis()` function reading 15+ DOM IDs.
- **New:** Reactive form with validation.
- **Complexity:** High. Dynamic dropdowns (e.g., "Sample Mode" toggles visibility of sub-options).
- **Requirement:** Map all 18+ CLI flags from the Python backend to form controls.

### 2. **Terminal Output (`Console.svelte`)**
- **Legacy:** `appendToTerminal()` with `ansi_up` and regex parsing for Gamma links.
- **New:** A virtualized list or efficient DOM renderer for logs.
- **Requirement:**
  - Auto-scroll to bottom.
  - Parse "Gamma URL" and "File Generated" lines into clickable rich elements.
  - **Crucial:** Handle SSE (Server-Sent Events) connection robustly.

### 3. **File Browser (`FileBrowser.svelte`)**
- **Legacy:** `loadOutputFiles()` fetches JSON and renders list.
- **New:** Data table with sorting/filtering.
- **Requirement:** "Download" and "View" actions. Preview modal for JSON/Markdown files.

### 4. **Execution History (`HistoryPanel.svelte`)**
- **Legacy:** Dropdown to switch execution contexts.
- **New:** Sidebar or dedicated "Runs" page?
- **Requirement:** Ability to load a past execution ID and repopulate the Terminal/Files views.

---

## 🔄 Cutover Strategy

**Spec Request:** Define the criteria for when `/v2` becomes `/`.
- **Parity Checklist:**
  - [ ] Can run all 18 analysis types?
  - [ ] Does terminal output look identical (or better)?
  - [ ] Do file downloads work?
  - [ ] Is polling reliable on disconnect/reconnect?
- **Strategy:**
  - Phase 1: `/v2` is "Beta".
  - Phase 2: `/v2` is default, `/legacy` is old app.
  - Phase 3: Remove legacy `static/` code.

---

## 📝 Deliverables Expected

1.  **Folder Structure:** Detailed `src/` layout (`lib/`, `routes/`, `components/`).
2.  **Interface Definitions:** TypeScript definitions for `AgentContext`, `ExecutionState`, etc.
3.  **Component Graph:** Which components own which state?
4.  **Migration Order:** Detailed step-by-step plan (e.g., "Step 1: Build API Client").

---

**End of Prompt**

