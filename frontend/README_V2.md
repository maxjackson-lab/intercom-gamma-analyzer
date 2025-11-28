# Intercom Analysis Tool - Frontend (v2)

This is the modern SvelteKit frontend for the Intercom Analysis Tool. It is served alongside the legacy HTML/JS frontend.

## Architecture

- **Framework:** SvelteKit (Svelte 5) + TypeScript
- **Build Mode:** Single Page App (SPA) using `@sveltejs/adapter-static`
- **Serving:** Built files are output to `build/` and mounted by FastAPI at `/v2`.

## Development

1. **Install Dependencies:**
   ```bash
   npm install
   ```

2. **Run Dev Server:**
   ```bash
   npm run dev
   ```
   This starts the SvelteKit dev server at `http://localhost:5173`.

3. **Proxying to Backend:**
   To interact with the real Python API during development, configure Vite proxy in `vite.config.ts` (if needed) or run the Python backend locally and point API calls to `http://localhost:8000`.

## Deployment

The `Dockerfile` in the root directory handles the build process:
1. Builds this frontend using Node.js.
2. Copies the `build/` directory to the Python container.
3. FastAPI serves it at `/v2`.

## Directory Structure

- `src/routes`: Pages and routing (File-system based).
- `static`: Static assets.
- `svelte.config.js`: Adapter configuration (configured for `/v2` base path).

