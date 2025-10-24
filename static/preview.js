// VERSION MARKER: v1.0.0 - Preview rendering module
console.log('✅ Preview.js v1.0.0 loaded successfully');

/**
 * Preview Rendering Module
 *
 * Provides markdown preview rendering capabilities with:
 * - DOMPurify sanitization for security
 * - Marked.js for markdown parsing
 * - Prism.js for syntax highlighting
 * - Collapsible sections for better UX
 * - Stats cards for summary data display
 */

// Global preview renderer object exposed for app.js
window.PreviewRenderer = (function() {
    'use strict';

    /**
     * Sanitize HTML content using DOMPurify
     * @param {string} dirty - Raw HTML content
     * @returns {string} - Sanitized HTML
     */
    function sanitizeHTML(dirty) {
        if (typeof DOMPurify === 'undefined') {
            console.warn('DOMPurify not available, returning unsanitized content (unsafe!)');
            return dirty;
        }

        return DOMPurify.sanitize(dirty, {
            ALLOWED_TAGS: [
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'p', 'br', 'hr',
                'strong', 'em', 'u', 'code', 'pre',
                'ul', 'ol', 'li',
                'a', 'img',
                'table', 'thead', 'tbody', 'tr', 'th', 'td',
                'div', 'span',
                'blockquote'
            ],
            ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class', 'id', 'style'],
            ALLOW_DATA_ATTR: false
        });
    }

    /**
     * Parse markdown to HTML using Marked.js
     * @param {string} markdown - Markdown content
     * @returns {string} - HTML content
     */
    function parseMarkdown(markdown) {
        if (typeof marked === 'undefined') {
            console.warn('Marked.js not available, returning raw markdown');
            return markdown.replace(/\n/g, '<br>');
        }

        // Configure marked options
        marked.setOptions({
            breaks: true,
            gfm: true,
            headerIds: true,
            mangle: false,
            sanitize: false  // We'll use DOMPurify for sanitization
        });

        try {
            return marked.parse(markdown);
        } catch (error) {
            console.error('Marked parsing error:', error);
            return markdown.replace(/\n/g, '<br>');
        }
    }

    /**
     * Apply Prism syntax highlighting to code blocks
     * @param {HTMLElement} container - Container element with code blocks
     */
    function applySyntaxHighlighting(container) {
        if (typeof Prism === 'undefined') {
            console.warn('Prism.js not available, skipping syntax highlighting');
            return;
        }

        try {
            // Find all code blocks
            const codeBlocks = container.querySelectorAll('pre code');
            codeBlocks.forEach(block => {
                // Auto-detect language or use default
                if (!block.className.includes('language-')) {
                    block.className = 'language-markup';
                }
                Prism.highlightElement(block);
            });
        } catch (error) {
            console.error('Prism highlighting error:', error);
        }
    }

    /**
     * Convert heading elements into collapsible sections
     * @param {HTMLElement} container - Container with heading elements
     */
    function convertHeadingsToCollapsible(container) {
        const headings = container.querySelectorAll('h2, h3');

        headings.forEach((heading, index) => {
            // Skip if already processed
            if (heading.classList.contains('collapsible-header')) {
                return;
            }

            // Get content between this heading and the next heading
            const content = [];
            let nextElement = heading.nextElementSibling;

            while (nextElement && !nextElement.matches('h2, h3')) {
                content.push(nextElement);
                nextElement = nextElement.nextElementSibling;
            }

            // Create collapsible wrapper
            const wrapper = document.createElement('div');
            wrapper.className = 'collapsible-section';

            // Create header with toggle button
            const header = document.createElement('div');
            header.className = 'collapsible-header';
            header.setAttribute('data-collapsed', 'false');

            const toggleIcon = document.createElement('span');
            toggleIcon.className = 'toggle-icon';
            toggleIcon.textContent = '▼';

            const headingText = document.createElement('span');
            headingText.className = 'heading-text';
            headingText.innerHTML = heading.innerHTML;

            header.appendChild(toggleIcon);
            header.appendChild(headingText);

            // Create content container
            const contentContainer = document.createElement('div');
            contentContainer.className = 'collapsible-content';
            contentContainer.setAttribute('data-visible', 'true');

            // Move content elements into container
            content.forEach(el => {
                contentContainer.appendChild(el.cloneNode(true));
            });

            // Add click handler
            header.addEventListener('click', function() {
                const isCollapsed = this.getAttribute('data-collapsed') === 'true';
                this.setAttribute('data-collapsed', !isCollapsed);
                contentContainer.setAttribute('data-visible', isCollapsed);
                toggleIcon.textContent = isCollapsed ? '▼' : '▶';
            });

            // Replace original heading with collapsible section
            wrapper.appendChild(header);
            wrapper.appendChild(contentContainer);
            heading.parentNode.replaceChild(wrapper, heading);

            // Remove original content elements
            content.forEach(el => {
                if (el.parentNode) {
                    el.parentNode.removeChild(el);
                }
            });
        });
    }

    /**
     * Create a collapsible section component
     * @param {string} title - Section title
     * @param {string} content - Section content (HTML)
     * @returns {HTMLElement} - Collapsible section element
     */
    function createCollapsibleSection(title, content) {
        const section = document.createElement('div');
        section.className = 'collapsible-section';

        // Create header
        const header = document.createElement('div');
        header.className = 'collapsible-header';
        header.setAttribute('data-collapsed', 'false');

        const toggleIcon = document.createElement('span');
        toggleIcon.className = 'toggle-icon';
        toggleIcon.textContent = '▼';

        const titleText = document.createElement('span');
        titleText.className = 'heading-text';
        titleText.textContent = title;

        header.appendChild(toggleIcon);
        header.appendChild(titleText);

        // Create content container
        const contentContainer = document.createElement('div');
        contentContainer.className = 'collapsible-content';
        contentContainer.setAttribute('data-visible', 'true');
        contentContainer.innerHTML = sanitizeHTML(content);

        // Add click handler
        header.addEventListener('click', function() {
            const isCollapsed = this.getAttribute('data-collapsed') === 'true';
            this.setAttribute('data-collapsed', !isCollapsed);
            contentContainer.setAttribute('data-visible', isCollapsed);
            toggleIcon.textContent = isCollapsed ? '▼' : '▶';
        });

        section.appendChild(header);
        section.appendChild(contentContainer);

        return section;
    }

    /**
     * Create stats cards from summary data
     * @param {Object} summary - Summary data object
     * @returns {HTMLElement} - Container with stats cards
     */
    function createStatsCards(summary) {
        const container = document.createElement('div');
        container.className = 'stats-cards-container';

        if (!summary || typeof summary !== 'object') {
            console.warn('Invalid summary data provided to createStatsCards');
            return container;
        }

        // Common stats to display
        const statsConfig = [
            { key: 'conversations', label: 'Conversations', icon: '💬', formatter: (v) => v.toLocaleString() },
            { key: 'dateRange', label: 'Date Range', icon: '📅', formatter: (v) => v },
            { key: 'totalTopics', label: 'Topics', icon: '🏷️', formatter: (v) => v },
            { key: 'sentiment', label: 'Avg Sentiment', icon: '😊', formatter: (v) => v },
            { key: 'topCategories', label: 'Top Categories', icon: '📊', formatter: (v) => Array.isArray(v) ? v.join(', ') : v },
            { key: 'responseTime', label: 'Avg Response Time', icon: '⏱️', formatter: (v) => v }
        ];

        statsConfig.forEach(stat => {
            if (summary[stat.key] !== undefined && summary[stat.key] !== null && summary[stat.key] !== '') {
                const card = document.createElement('div');
                card.className = 'stats-card';

                const iconSpan = document.createElement('span');
                iconSpan.className = 'stats-icon';
                iconSpan.textContent = stat.icon;

                const labelDiv = document.createElement('div');
                labelDiv.className = 'stats-label';
                labelDiv.textContent = stat.label;

                const valueDiv = document.createElement('div');
                valueDiv.className = 'stats-value';

                try {
                    valueDiv.textContent = stat.formatter(summary[stat.key]);
                } catch (error) {
                    console.error(`Error formatting stat ${stat.key}:`, error);
                    valueDiv.textContent = summary[stat.key];
                }

                card.appendChild(iconSpan);
                card.appendChild(labelDiv);
                card.appendChild(valueDiv);

                container.appendChild(card);
            }
        });

        return container;
    }

    /**
     * Main function to render markdown preview
     * @param {string} markdownContent - Markdown content to render
     * @param {Object} summary - Optional summary data for stats cards
     * @returns {HTMLElement} - Rendered preview container
     */
    function renderMarkdownPreview(markdownContent, summary) {
        console.log('🎨 Rendering markdown preview...');

        // Create main container
        const container = document.createElement('div');
        container.className = 'markdown-preview-container';

        try {
            // Add stats cards if summary provided
            if (summary) {
                const statsCards = createStatsCards(summary);
                if (statsCards.children.length > 0) {
                    container.appendChild(statsCards);
                }
            }

            // Parse markdown to HTML
            let htmlContent = parseMarkdown(markdownContent);

            // Sanitize HTML
            htmlContent = sanitizeHTML(htmlContent);

            // Create content div
            const contentDiv = document.createElement('div');
            contentDiv.className = 'markdown-content';
            contentDiv.innerHTML = htmlContent;

            // Convert headings to collapsible sections
            convertHeadingsToCollapsible(contentDiv);

            // Apply syntax highlighting
            applySyntaxHighlighting(contentDiv);

            container.appendChild(contentDiv);

            console.log('✅ Markdown preview rendered successfully');
            return container;

        } catch (error) {
            console.error('❌ Error rendering markdown preview:', error);

            // Return error message
            const errorDiv = document.createElement('div');
            errorDiv.className = 'preview-error';
            errorDiv.innerHTML = `
                <h3>⚠️ Preview Error</h3>
                <p>Failed to render markdown preview: ${error.message}</p>
                <pre>${markdownContent.substring(0, 500)}...</pre>
            `;
            container.appendChild(errorDiv);

            return container;
        }
    }

    // Public API
    return {
        renderMarkdownPreview: renderMarkdownPreview,
        createCollapsibleSection: createCollapsibleSection,
        createStatsCards: createStatsCards,
        sanitizeHTML: sanitizeHTML,
        parseMarkdown: parseMarkdown,
        applySyntaxHighlighting: applySyntaxHighlighting
    };
})();

// Convenience aliases for backward compatibility
window.renderMarkdownPreview = window.PreviewRenderer.renderMarkdownPreview;
window.createCollapsibleSection = window.PreviewRenderer.createCollapsibleSection;
window.createStatsCards = window.PreviewRenderer.createStatsCards;

console.log('📦 Preview module ready:', Object.keys(window.PreviewRenderer).join(', '));
