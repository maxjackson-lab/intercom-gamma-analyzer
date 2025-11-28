import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://svelte.dev/docs/kit/integrations
	// for more information about preprocessors
	preprocess: vitePreprocess(),

	kit: {
		// Use adapter-static for SPA mode served by FastAPI
		adapter: adapter({
			fallback: 'index.html', // Fallback for SPA routing
            pages: 'build',
            assets: 'build',
            precompress: false,
            strict: true
		}),
        paths: {
            base: '/v2' // Serve from /v2 subdirectory
        }
	}
};

export default config;
