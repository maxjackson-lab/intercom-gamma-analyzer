# Frontend Migration & Modernization Plan

**Date:** November 28, 2025
**Status:** In Progress (Phase 1: Infrastructure Ready)

## 1. Executive Summary

We are migrating the legacy HTML/Vanilla JS frontend (served via FastAPI templates) to a modern, component-based architecture. After evaluating React, Vue 3, and SvelteKit, **SvelteKit** was selected for its performance, simplicity, and alignment with the project's Python-centric team structure.

To ensure zero downtime, we have implemented a **Parallel "Sidecar" Deployment Strategy**. The new frontend runs at `/v2`, while the existing dashboard remains untouched at `/`.

---

## 2. Framework Selection Analysis

### **Why SvelteKit?**

| Feature | React | Vue 3 | SvelteKit | Winner |
| :--- | :--- | :--- | :--- | :--- |
| **Learning Curve** | High (Hooks, Context) | Medium (Options vs Composition) | **Low** (HTML/JS/CSS feel) | **Svelte** |
| **Boilerplate** | High | Medium | **Low** | **Svelte** |
| **State Management** | Context/Redux/Zustand | Pinia | **Built-in Stores** | **Svelte** |
| **Performance** | Virtual DOM overhead | Virtual DOM | **Compiled (No VDOM)** | **Svelte** |
| **Python Alignment** | Low | Medium | **High** (Simple syntax) | **Svelte** |

**Key Driver:** Svelte's "compiler" approach removes the need for a heavy runtime, making it ideal for embedding within a Python application container.

---

## 3. Architecture: The "Monolithic Monorepo"

We are maintaining a single repository to simplify deployment and version control.

### **Folder Structure**
```text
/
├── deploy/
│   └── railway_web.py       # FastAPI entry point
├── frontend/                # [NEW] SvelteKit Project
│   ├── src/
│   │   ├── routes/          # File-system routing
│   │   └── lib/             # Shared logic/components
│   └── svelte.config.js     # Configured for static adapter
├── static/                  # [LEGACY] Existing JS/CSS
└── Dockerfile               # Multi-stage build
```

### **Deployment Workflow (Railway)**
1.  **Build Stage (Node.js):** 
    - Compiles SvelteKit app to static HTML/JS/CSS.
    - Output: `/app/frontend/build`
2.  **Runtime Stage (Python):**
    - Installs Python dependencies.
    - Copies compiled frontend assets from Build Stage.
    - Starts FastAPI.
3.  **Serving:**
    - `/` → Serves Legacy `static/` files.
    - `/v2` → Serves Modern `frontend/build` files.

---

## 4. Migration Roadmap

### **Phase 1: Infrastructure (✅ Completed)**
- [x] Scaffold SvelteKit project in `frontend/`
- [x] Configure `adapter-static` for SPA mode
- [x] Update `Dockerfile` for multi-stage build
- [x] Mount `/v2` route in FastAPI

### **Phase 2: Foundation (Next Steps)**
- [ ] **Shared State:** Create Svelte Stores to mirror `app.js` polling logic (Execution ID, Status).
- [ ] **API Client:** strict typed wrapper around backend endpoints (`/execute`, `/status`).
- [ ] **Layout:** Port the navigation bar and basic container styles to Svelte components.

### **Phase 3: Feature Migration**
*Order of migration based on complexity and risk:*

1.  **File Browser:** Low complexity, read-only. Good for testing API integration.
2.  **Console/Terminal:** Medium complexity. Requires handling SSE (Server-Sent Events) in Svelte.
3.  **Configuration Form:** High complexity. Form state, validation, and dynamic options.
4.  **Visualizations:** Port Chart.js logic to Svelte wrappers.

---

## 5. Developer Guide

### **Running Locally**

**Option A: Full Stack (Python + Svelte Dev Server)**
*Best for feature development.*
1.  Run Backend: `python deploy/railway_web.py` (Port 8000)
2.  Run Frontend: `cd frontend && npm run dev` (Port 5173)
3.  *Note:* You will need to configure Vite proxy or CORS to talk to port 8000.

**Option B: Production Simulation**
*Best for testing deployment.*
1.  Build Frontend: `cd frontend && npm run build`
2.  Run Backend: `python deploy/railway_web.py`
3.  Access at `http://localhost:8000/v2`

### **Key Files**
- **Legacy:** `static/app.js` (Reference logic here)
- **New:** `frontend/src/routes/+page.svelte` (Home page)
- **Config:** `frontend/svelte.config.js` (Base path settings)

