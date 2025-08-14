/**
 * Theme Manager for CTGov Compliance Application
 * Handles dark/light theme switching, system preference detection, and user preferences
 */
class ThemeManager {
    constructor() {
        this.storageKey = 'ctgov-theme-preference';
        this.themes = {
            light: 'light',
            dark: 'dark',
            auto: 'auto'
        };
        
        // Initialize theme on construction
        this.init();
    }

    /**
     * Initialize the theme system
     */
    init() {
        // Set up system preference detection
        this.setupSystemPreferenceDetection();
        
        // Apply initial theme
        this.applyTheme(this.getCurrentTheme());
        
        // Set up theme toggle controls
        this.setupThemeControls();
        
        // Dispatch theme ready event
        this.dispatchThemeEvent('theme-ready', { theme: this.getCurrentTheme() });
    }

    /**
     * Get the current theme preference
     * @returns {string} The current theme ('light', 'dark', or 'auto')
     */
    getCurrentTheme() {
        const stored = localStorage.getItem(this.storageKey);
        if (stored && Object.values(this.themes).includes(stored)) {
            return stored;
        }
        // Default to auto if no preference is stored
        // return this.themes.auto;
        return this.themes.light;
    }

    /**
     * Get the effective theme (resolves 'auto' to 'light' or 'dark')
     * @returns {string} The effective theme ('light' or 'dark')
     */
    getEffectiveTheme() {
        const current = this.getCurrentTheme();
        if (current === this.themes.auto) {
            return this.getSystemPreference();
        }
        return current;
    }

    /**
     * Get the system preference for theme
     * @returns {string} 'light' or 'dark'
     */
    getSystemPreference() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return this.themes.dark;
        }
        return this.themes.light;
    }

    /**
     * Set up system preference change detection
     */
    setupSystemPreferenceDetection() {
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            
            // Listen for system preference changes
            const handleChange = (e) => {
                // Only apply changes if user preference is set to auto
                if (this.getCurrentTheme() === this.themes.auto) {
                    this.applyTheme(this.themes.auto);
                    this.dispatchThemeEvent('theme-auto-changed', { 
                        systemPreference: e.matches ? this.themes.dark : this.themes.light 
                    });
                }
            };

            // Modern browsers
            if (mediaQuery.addEventListener) {
                mediaQuery.addEventListener('change', handleChange);
            } else if (mediaQuery.addListener) {
                // Legacy browsers
                mediaQuery.addListener(handleChange);
            }
        }
    }

    /**
     * Apply the specified theme
     * @param {string} theme - The theme to apply ('light', 'dark', or 'auto')
     */
    applyTheme(theme) {
        const effectiveTheme = theme === this.themes.auto ? this.getSystemPreference() : theme;
        
        // Apply theme to document - always set explicit theme attribute
        if (theme === this.themes.auto) {
            document.documentElement.setAttribute('data-theme', 'auto');
        } else if (theme === this.themes.dark) {
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
        }

        // Update active control indicators
        this.updateThemeControls(theme);
        
        // Dispatch theme change event
        this.dispatchThemeEvent('theme-changed', { 
            theme: theme, 
            effectiveTheme: effectiveTheme 
        });
    }

    /**
     * Set the theme preference
     * @param {string} theme - The theme to set ('light', 'dark', or 'auto')
     */
    setTheme(theme) {
        if (!Object.values(this.themes).includes(theme)) {
            console.warn(`Invalid theme: ${theme}. Valid themes are: ${Object.values(this.themes).join(', ')}`);
            return;
        }

        // Store preference
        localStorage.setItem(this.storageKey, theme);
        
        // Apply theme
        this.applyTheme(theme);
    }

    /**
     * Toggle between light and dark themes
     * If current theme is auto, toggle to the opposite of system preference
     */
    toggleTheme() {
        const current = this.getCurrentTheme();
        const effective = this.getEffectiveTheme();
        
        if (current === this.themes.auto || effective === this.themes.light) {
            this.setTheme(this.themes.dark);
        } else {
            this.setTheme(this.themes.light);
        }
    }

    /**
     * Cycle through all theme options (light -> dark -> auto -> light)
     */
    cycleTheme() {
        const current = this.getCurrentTheme();
        const themes = Object.values(this.themes);
        const currentIndex = themes.indexOf(current);
        const nextIndex = (currentIndex + 1) % themes.length;
        this.setTheme(themes[nextIndex]);
    }

    /**
     * Set up theme controls in the UI
     */
    setupThemeControls() {
        // Theme toggle button
        const toggleButton = document.getElementById('theme-toggle');
        if (toggleButton) {
            toggleButton.addEventListener('click', () => this.toggleTheme());
        }

        // Theme selector dropdown
        const themeSelector = document.getElementById('theme-selector');
        if (themeSelector) {
            themeSelector.addEventListener('change', (e) => {
                this.setTheme(e.target.value);
            });
        }

        // Individual theme buttons
        Object.values(this.themes).forEach(theme => {
            const button = document.getElementById(`theme-${theme}`);
            if (button) {
                button.addEventListener('click', () => this.setTheme(theme));
            }
        });

        // Keyboard shortcut (Ctrl/Cmd + Shift + T)
        // document.addEventListener('keydown', (e) => {
        //     if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'T') {
        //         e.preventDefault();
        //         this.toggleTheme();
        //     }
        // });
    }

    /**
     * Update theme control indicators
     * @param {string} currentTheme - The current theme preference
     */
    updateThemeControls(currentTheme) {
        const effectiveTheme = this.getEffectiveTheme();
        
        // Update toggle button icon/text
        const toggleButton = document.getElementById('theme-toggle');
        if (toggleButton) {
            const icon = toggleButton.querySelector('i');
            const text = toggleButton.querySelector('.theme-toggle-text');
            
            if (icon) {
                icon.className = effectiveTheme === this.themes.dark 
                    ? 'ri-sun-line' 
                    : 'ri-moon-line';
            }
            
            if (text) {
                text.textContent = this.getThemeDisplayText(currentTheme, effectiveTheme);
            }
            
            // Update aria-label for accessibility
            toggleButton.setAttribute('aria-label', 
                `Switch to ${effectiveTheme === this.themes.dark ? 'light' : 'dark'} theme`);
        }

        // Update theme selector
        const themeSelector = document.getElementById('theme-selector');
        if (themeSelector) {
            themeSelector.value = currentTheme;
        }

        // Update individual theme buttons
        Object.values(this.themes).forEach(theme => {
            const button = document.getElementById(`theme-${theme}`);
            if (button) {
                if (theme === currentTheme) {
                    button.classList.add('active', 'usa-button--active');
                    button.setAttribute('aria-pressed', 'true');
                } else {
                    button.classList.remove('active', 'usa-button--active');
                    button.setAttribute('aria-pressed', 'false');
                }
            }
        });
    }

    /**
     * Get display text for theme toggle button
     * @param {string} currentTheme - The current theme preference
     * @param {string} effectiveTheme - The effective theme being displayed
     * @returns {string} Display text
     */
    getThemeDisplayText(currentTheme, effectiveTheme) {
        if (currentTheme === this.themes.auto) {
            return `Auto (${effectiveTheme === this.themes.dark ? 'Dark' : 'Light'})`;
        }
        return currentTheme.charAt(0).toUpperCase() + currentTheme.slice(1);
    }

    /**
     * Dispatch a custom theme event
     * @param {string} eventName - The event name
     * @param {object} detail - Event detail data
     */
    dispatchThemeEvent(eventName, detail) {
        const event = new CustomEvent(eventName, {
            detail: detail,
            bubbles: true
        });
        document.dispatchEvent(event);
    }

    /**
     * Get theme information for external use
     * @returns {object} Theme information
     */
    getThemeInfo() {
        const current = this.getCurrentTheme();
        const effective = this.getEffectiveTheme();
        const system = this.getSystemPreference();
        
        return {
            current: current,
            effective: effective,
            system: system,
            isAuto: current === this.themes.auto,
            isDark: effective === this.themes.dark,
            isLight: effective === this.themes.light
        };
    }

    /**
     * Reset theme to default (auto)
     */
    resetTheme() {
        localStorage.removeItem(this.storageKey);
        this.applyTheme(this.themes.auto);
    }

    /**
     * Debug function to log current theme state
     */
    debugTheme() {
        const info = this.getThemeInfo();
        console.log('Theme Debug Info:', {
            current: info.current,
            effective: info.effective,
            system: info.system,
            documentAttribute: document.documentElement.getAttribute('data-theme'),
            localStorage: localStorage.getItem(this.storageKey)
        });
    }
}

// Initialize theme manager when DOM is ready
let themeManager;

function initializeTheme() {
    themeManager = new ThemeManager();
    
    // Make theme manager globally accessible
    window.themeManager = themeManager;
    
    // Expose commonly used methods globally
    window.setTheme = (theme) => themeManager.setTheme(theme);
    window.toggleTheme = () => themeManager.toggleTheme();
    window.getThemeInfo = () => themeManager.getThemeInfo();
    window.debugTheme = () => themeManager.debugTheme();
}

// Initialize immediately if DOM is already ready, otherwise wait for DOMContentLoaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeTheme);
} else {
    initializeTheme();
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ThemeManager;
} 