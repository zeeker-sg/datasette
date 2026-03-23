/**
 * Zeeker Base JavaScript
 * Core functionality: body classes, copy-to-clipboard, keyboard shortcuts,
 * scroll-to-top, search enhancements, SQL helpers.
 */

class ZeekerEnhancer {
    constructor() {
        this.init();
    }

    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupFeatures());
        } else {
            this.setupFeatures();
        }
    }

    setupFeatures() {
        this.addBodyClasses();
        this.addSearchEnhancements();
        this.addCopyButtons();
        this.addKeyboardShortcuts();
        this.setupScrollToTop();
        this.setupQueryHelpers();
        this.setupExampleQueries();
    }

    /**
     * Add page-type classes to body for CSS targeting.
     */
    addBodyClasses() {
        document.body.classList.add('zeeker-enhanced');

        const path = window.location.pathname;
        if (path === '/') {
            document.body.classList.add('page-home');
        } else if (path.includes('/query')) {
            document.body.classList.add('page-query');
        } else if (path.match(/\/[^/]+\/[^/]+$/)) {
            document.body.classList.add('page-table');
        } else if (path.match(/\/[^/]+$/)) {
            document.body.classList.add('page-database');
        }
    }

    /**
     * Enhance search inputs with keyboard shortcuts.
     */
    addSearchEnhancements() {
        const searchInputs = document.querySelectorAll('input[type="search"], input[name="q"]');

        searchInputs.forEach(input => {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    input.blur();
                }
                if (e.key === 'Enter' && e.ctrlKey) {
                    input.form?.submit();
                }
            });
        });
    }

    /**
     * Add copy-to-clipboard buttons to code blocks.
     */
    addCopyButtons() {
        const codeElements = document.querySelectorAll('pre code, .highlight, .example-box pre');

        codeElements.forEach(element => {
            if (element.closest('.copy-button-added')) return;

            const codeBlock = element.tagName === 'PRE' ? element : element.closest('pre');
            if (!codeBlock) return;

            // Skip if parent already has a copy button
            if (codeBlock.parentElement.querySelector('.copy-btn')) return;

            const wrapper = codeBlock.parentElement;
            wrapper.classList.add('copy-button-added');
            wrapper.style.position = 'relative';

            const copyButton = document.createElement('button');
            copyButton.className = 'copy-btn';
            copyButton.textContent = 'Copy';
            copyButton.setAttribute('aria-label', 'Copy code');
            copyButton.title = 'Copy to clipboard';

            copyButton.addEventListener('click', () => {
                const text = element.textContent || codeBlock.textContent;
                this.copyToClipboard(text, copyButton);
            });

            wrapper.appendChild(copyButton);
        });

        // Handle existing copy buttons placed in templates
        document.querySelectorAll('.copy-btn').forEach(button => {
            if (!button.hasAttribute('data-enhanced')) {
                button.setAttribute('data-enhanced', 'true');
                button.addEventListener('click', (e) => {
                    e.preventDefault();
                    const codeBlock = button.previousElementSibling;
                    if (codeBlock) {
                        const text = codeBlock.textContent;
                        this.copyToClipboard(text, button);
                    }
                });
            }
        });
    }

    /**
     * Copy text to clipboard with visual feedback on the button.
     */
    copyToClipboard(text, button) {
        navigator.clipboard.writeText(text).then(() => {
            const originalText = button.textContent;
            const originalClass = button.className;

            button.textContent = 'Copied';
            button.classList.add('copied');

            setTimeout(() => {
                button.textContent = originalText;
                button.className = originalClass;
            }, 2000);
        }).catch(() => {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);

            const originalText = button.textContent;
            button.textContent = 'Copied';
            setTimeout(() => {
                button.textContent = originalText;
            }, 2000);
        });
    }

    /**
     * Global keyboard shortcuts:
     *   /       - Focus search input
     *   Ctrl+H  - Go home
     *   Ctrl+B  - Go back
     *   Escape  - Blur active element
     */
    addKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Skip if typing in form fields
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

            switch (e.key) {
                case '/':
                    e.preventDefault();
                    const searchInput = document.querySelector('input[name="q"]');
                    if (searchInput) {
                        searchInput.focus();
                    }
                    break;

                case 'h':
                    if (e.ctrlKey) {
                        e.preventDefault();
                        window.location.href = '/';
                    }
                    break;

                case 'b':
                    if (e.ctrlKey) {
                        e.preventDefault();
                        window.history.back();
                    }
                    break;

                case 'Escape':
                    document.activeElement?.blur();
                    break;
            }
        });
    }

    /**
     * Scroll-to-top button, available on all pages.
     */
    setupScrollToTop() {
        let scrollToTopBtn = document.querySelector('.scroll-to-top');

        if (!scrollToTopBtn) {
            scrollToTopBtn = document.createElement('button');
            scrollToTopBtn.className = 'scroll-to-top';
            scrollToTopBtn.innerHTML = '&uarr;';
            scrollToTopBtn.setAttribute('aria-label', 'Scroll to top');
            scrollToTopBtn.style.cssText = `
                position: fixed;
                bottom: 2rem;
                right: 2rem;
                width: 50px;
                height: 50px;
                background: var(--color-accent-primary);
                color: white;
                border: none;
                border-radius: 50%;
                font-size: 1.2rem;
                cursor: pointer;
                z-index: 1000;
                opacity: 0;
                transform: translateY(100px);
                transition: all 0.3s ease;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
            `;
            document.body.appendChild(scrollToTopBtn);
        }

        window.addEventListener('scroll', () => {
            if (window.pageYOffset > window.innerHeight) {
                scrollToTopBtn.style.opacity = '1';
                scrollToTopBtn.style.transform = 'translateY(0)';
            } else {
                scrollToTopBtn.style.opacity = '0';
                scrollToTopBtn.style.transform = 'translateY(100px)';
            }
        });

        scrollToTopBtn.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    /**
     * SQL query interface enhancements: auto-save, keyboard shortcuts, result interactions.
     */
    setupQueryHelpers() {
        const sqlTextarea = document.querySelector('.sql-textarea');
        if (sqlTextarea) {
            // Auto-save query to localStorage
            let autoSaveTimeout;
            sqlTextarea.addEventListener('input', () => {
                clearTimeout(autoSaveTimeout);
                autoSaveTimeout = setTimeout(() => {
                    if (sqlTextarea.value.trim()) {
                        localStorage.setItem('zeeker_auto_saved_query', sqlTextarea.value);
                    }
                }, 2000);
            });

            // Load auto-saved query if textarea is empty
            if (!sqlTextarea.value.trim()) {
                const saved = localStorage.getItem('zeeker_auto_saved_query');
                if (saved) {
                    sqlTextarea.value = saved;
                }
            }

            // Ctrl+Enter to submit, Tab to indent
            sqlTextarea.addEventListener('keydown', (e) => {
                if (e.ctrlKey && e.key === 'Enter') {
                    e.preventDefault();
                    const form = sqlTextarea.closest('form');
                    if (form) form.submit();
                }

                if (e.key === 'Tab') {
                    e.preventDefault();
                    const start = sqlTextarea.selectionStart;
                    const end = sqlTextarea.selectionEnd;
                    const value = sqlTextarea.value;
                    sqlTextarea.value = value.substring(0, start) + '  ' + value.substring(end);
                    sqlTextarea.selectionStart = sqlTextarea.selectionEnd = start + 2;
                }
            });
        }

        this.enhanceQueryResults();
    }

    /**
     * Enhance query result tables: copy results, selectable cells.
     */
    enhanceQueryResults() {
        const copyResultsButton = document.querySelector('[onclick="copyResults()"]');
        if (copyResultsButton) {
            copyResultsButton.onclick = null;
            copyResultsButton.addEventListener('click', () => {
                const table = document.querySelector('.query-results-table');
                if (table) {
                    const text = Array.from(table.querySelectorAll('tr')).map(row =>
                        Array.from(row.querySelectorAll('th, td')).map(cell =>
                            cell.textContent.trim()
                        ).join('\t')
                    ).join('\n');

                    this.copyToClipboard(text, copyResultsButton);
                }
            });
        }

        const resultTable = document.querySelector('.query-results-table');
        if (resultTable) {
            resultTable.addEventListener('click', (e) => {
                if (e.target.tagName === 'TD') {
                    resultTable.querySelectorAll('.selected-cell').forEach(cell => {
                        cell.classList.remove('selected-cell');
                    });

                    e.target.classList.add('selected-cell');

                    e.target.addEventListener('dblclick', () => {
                        this.copyToClipboard(e.target.textContent.trim(), e.target);
                    }, { once: true });
                }
            });
        }
    }

    /**
     * Wire up example query buttons to load SQL into the editor.
     */
    setupExampleQueries() {
        const exampleButtons = document.querySelectorAll('[onclick*="useExample"]');
        exampleButtons.forEach(button => {
            button.onclick = null;

            button.addEventListener('click', (e) => {
                e.preventDefault();
                const codeBlock = button.previousElementSibling;
                if (codeBlock && codeBlock.tagName === 'PRE') {
                    const query = codeBlock.textContent.trim();
                    const textarea = document.querySelector('.sql-textarea');
                    if (textarea) {
                        textarea.value = query;
                        textarea.focus();

                        button.style.background = 'var(--color-success)';
                        button.textContent = 'Added to Editor';
                        setTimeout(() => {
                            button.style.background = '';
                            button.textContent = button.getAttribute('data-original-text') || 'Try This Query';
                        }, 2000);
                    }
                }
            });

            if (!button.getAttribute('data-original-text')) {
                button.setAttribute('data-original-text', button.textContent);
            }
        });

        const formatButton = document.querySelector('[onclick="formatQuery()"]');
        if (formatButton) {
            formatButton.onclick = null;
            formatButton.addEventListener('click', () => {
                const textarea = document.querySelector('.sql-textarea');
                if (textarea) {
                    textarea.value = this.formatSQL(textarea.value);
                }
            });
        }
    }

    /**
     * Basic SQL formatter: normalizes whitespace and adds line breaks at keywords.
     */
    formatSQL(sql) {
        if (!sql.trim()) return sql;

        let formatted = sql
            .replace(/\s+/g, ' ')
            .replace(/\b(SELECT|FROM|WHERE|GROUP BY|ORDER BY|HAVING|JOIN|LEFT JOIN|RIGHT JOIN|INNER JOIN|OUTER JOIN|ON|AND|OR|UNION|LIMIT|OFFSET)\b/gi, '\n$1')
            .replace(/,(?!\s*\n)/g, ',\n  ')
            .replace(/\n\s*\n/g, '\n')
            .trim();

        return formatted;
    }

    // -- Utility methods --

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}

// Global functions for template compatibility
window.copyCode = function(button) {
    const codeBlock = button.nextElementSibling;
    if (codeBlock) {
        const text = codeBlock.textContent;

        navigator.clipboard.writeText(text).then(() => {
            const originalText = button.textContent;
            button.textContent = 'Copied!';
            button.style.background = 'var(--color-success)';

            setTimeout(() => {
                button.textContent = originalText;
                button.style.background = '';
            }, 2000);
        });
    }
};

window.useExample = function(button) {
    const code = button.previousElementSibling.textContent;
    const textarea = document.querySelector('.sql-textarea');
    if (textarea) {
        textarea.value = code.trim();
        textarea.focus();
    }
};

// Initialize
new ZeekerEnhancer();
