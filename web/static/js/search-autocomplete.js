/**
 * Search Autocomplete System
 * Provides autocomplete suggestions for search form fields
 */

class SearchAutocomplete {
    constructor() {
        this.debounceDelay = 300;
        this.minQueryLength = 2;
        this.maxSuggestions = 10;
        this.activeRequests = new Map();
        
        this.init();
    }

    init() {
        this.setupAutocomplete();
        this.bindEvents();
    }

    /**
     * Setup autocomplete for all search input fields
     */
    setupAutocomplete() {
        const autocompleteFields = [
            {
                inputId: 'trial-title',
                endpoint: '/api/autocomplete/titles',
                minLength: 2
            },
            {
                inputId: 'organization',
                endpoint: '/api/autocomplete/organizations',
                minLength: 2
            },
            {
                inputId: 'nct-id',
                endpoint: '/api/autocomplete/nct_ids',
                minLength: 3
            },
            {
                inputId: 'user-email',
                endpoint: '/api/autocomplete/user_emails',
                minLength: 2
            }
        ];

        autocompleteFields.forEach(field => {
            const input = document.getElementById(field.inputId);
            if (input) {
                this.initializeField(input, field.endpoint, field.minLength);
            }
        });
    }

    /**
     * Initialize autocomplete for a specific input field
     */
    initializeField(input, endpoint, minLength) {
        // Create suggestions container
        const container = this.createSuggestionsContainer(input);
        
        // Store field configuration
        input.autocompleteConfig = {
            endpoint: endpoint,
            minLength: minLength,
            container: container,
            selectedIndex: -1,
            isOpen: false
        };

        // Bind input events
        this.bindInputEvents(input);
    }

    /**
     * Create suggestions dropdown container
     */
    createSuggestionsContainer(input) {
        const container = document.createElement('div');
        container.className = 'autocomplete-suggestions';
        container.style.display = 'none';
        
        // Insert after the input field
        input.parentNode.style.position = 'relative';
        input.parentNode.appendChild(container);
        
        return container;
    }

    /**
     * Bind events to input field
     */
    bindInputEvents(input) {
        let debounceTimeout;

        // Input event for typing
        input.addEventListener('input', (e) => {
            clearTimeout(debounceTimeout);
            debounceTimeout = setTimeout(() => {
                this.handleInput(input, e.target.value);
            }, this.debounceDelay);
        });

        // Keydown for navigation
        input.addEventListener('keydown', (e) => {
            this.handleKeydown(input, e);
        });

        // Focus event
        input.addEventListener('focus', () => {
            if (input.value.length >= input.autocompleteConfig.minLength) {
                this.handleInput(input, input.value);
            }
        });

        // Blur event to hide suggestions
        input.addEventListener('blur', (e) => {
            // Delay hiding to allow clicking on suggestions
            setTimeout(() => {
                this.hideSuggestions(input);
            }, 150);
        });
    }

    /**
     * Handle input changes
     */
    async handleInput(input, query) {
        const config = input.autocompleteConfig;
        
        if (query.length < config.minLength) {
            this.hideSuggestions(input);
            return;
        }

        // Cancel previous request for this input
        if (this.activeRequests.has(input)) {
            this.activeRequests.get(input).abort();
        }

        // Create new AbortController for this request
        const controller = new AbortController();
        this.activeRequests.set(input, controller);

        try {
            const response = await fetch(`${config.endpoint}?q=${encodeURIComponent(query)}`, {
                signal: controller.signal
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const suggestions = await response.json();
            this.displaySuggestions(input, suggestions);
            
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('Autocomplete error:', error);
                this.hideSuggestions(input);
            }
        } finally {
            this.activeRequests.delete(input);
        }
    }

    /**
     * Display suggestions dropdown
     */
    displaySuggestions(input, suggestions) {
        const config = input.autocompleteConfig;
        const container = config.container;

        if (!suggestions || suggestions.length === 0) {
            this.hideSuggestions(input);
            return;
        }

        // Clear previous suggestions
        container.innerHTML = '';
        config.selectedIndex = -1;

        // Create suggestion items
        suggestions.forEach((suggestion, index) => {
            const item = document.createElement('div');
            item.className = 'autocomplete-suggestion';
            item.textContent = suggestion;
            item.dataset.index = index;

            // Click handler
            item.addEventListener('click', () => {
                this.selectSuggestion(input, suggestion);
            });

            // Hover handler
            item.addEventListener('mouseenter', () => {
                this.highlightSuggestion(input, index);
            });

            container.appendChild(item);
        });

        // Show container
        this.showSuggestions(input);
    }

    /**
     * Handle keyboard navigation
     */
    handleKeydown(input, event) {
        const config = input.autocompleteConfig;
        
        if (!config.isOpen) {
            return;
        }

        const suggestions = config.container.children;
        
        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                config.selectedIndex = Math.min(config.selectedIndex + 1, suggestions.length - 1);
                this.updateHighlight(input);
                break;
                
            case 'ArrowUp':
                event.preventDefault();
                config.selectedIndex = Math.max(config.selectedIndex - 1, -1);
                this.updateHighlight(input);
                break;
                
            case 'Enter':
                event.preventDefault();
                if (config.selectedIndex >= 0 && suggestions[config.selectedIndex]) {
                    const suggestion = suggestions[config.selectedIndex].textContent;
                    this.selectSuggestion(input, suggestion);
                }
                break;
                
            case 'Escape':
                event.preventDefault();
                this.hideSuggestions(input);
                break;
        }
    }

    /**
     * Highlight a specific suggestion
     */
    highlightSuggestion(input, index) {
        const config = input.autocompleteConfig;
        config.selectedIndex = index;
        this.updateHighlight(input);
    }

    /**
     * Update visual highlighting
     */
    updateHighlight(input) {
        const config = input.autocompleteConfig;
        const suggestions = config.container.children;

        // Remove previous highlighting
        Array.from(suggestions).forEach(item => {
            item.classList.remove('autocomplete-suggestion-highlighted');
        });

        // Add highlighting to selected item
        if (config.selectedIndex >= 0 && suggestions[config.selectedIndex]) {
            suggestions[config.selectedIndex].classList.add('autocomplete-suggestion-highlighted');
        }
    }

    /**
     * Select a suggestion
     */
    selectSuggestion(input, suggestion) {
        input.value = suggestion;
        this.hideSuggestions(input);
        
        // Trigger change event
        input.dispatchEvent(new Event('change', { bubbles: true }));
        
        // Focus back to input
        input.focus();
    }

    /**
     * Show suggestions container
     */
    showSuggestions(input) {
        const config = input.autocompleteConfig;
        config.container.style.display = 'block';
        config.isOpen = true;
        
        // Position the container
        this.positionContainer(input);
    }

    /**
     * Hide suggestions container
     */
    hideSuggestions(input) {
        const config = input.autocompleteConfig;
        config.container.style.display = 'none';
        config.isOpen = false;
        config.selectedIndex = -1;
    }

    /**
     * Position suggestions container
     */
    positionContainer(input) {
        const config = input.autocompleteConfig;
        const container = config.container;
        const inputRect = input.getBoundingClientRect();
        const parentRect = input.parentNode.getBoundingClientRect();
        
        // Position relative to parent
        container.style.top = `${input.offsetTop + input.offsetHeight}px`;
        container.style.left = `${input.offsetLeft}px`;
        container.style.width = `${input.offsetWidth}px`;
    }

    /**
     * Bind global events
     */
    bindEvents() {
        // Hide suggestions when clicking outside
        document.addEventListener('click', (e) => {
            const autocompleteInputs = document.querySelectorAll('#trial-title, #organization, #nct-id, #user-email');
            autocompleteInputs.forEach(input => {
                if (input.autocompleteConfig && 
                    !input.contains(e.target) && 
                    !input.autocompleteConfig.container.contains(e.target)) {
                    this.hideSuggestions(input);
                }
            });
        });

        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            this.activeRequests.forEach(controller => controller.abort());
        });
    }
}

// Initialize autocomplete when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new SearchAutocomplete();
}); 