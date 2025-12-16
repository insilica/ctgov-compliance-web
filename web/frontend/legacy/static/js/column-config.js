/**
 * Table Column Configuration System
 * Manages customizable table columns with localStorage persistence
 */

class TableColumnConfig {
    constructor(tableType = 'trials') {
        this.tableType = tableType;
        this.storageKey = `ctgov_table_columns_${tableType}`;
        this.defaultColumns = this.getDefaultColumns();
        this.availableColumns = this.getAvailableColumns();
        this.currentConfig = this.loadConfig();
        
        this.init();
    }

    /**
     * Get default visible columns for different table types
     */
    getDefaultColumns() {
        const defaults = {
            'trials': ['title', 'nct_id', 'organization', 'status', 'start_date', 'end_date', 'reporting_due_date'],
            'compare': ['sponsor', 'total_trials', 'compliant_trials', 'late_submissions', 'compliance_rate']
        };
        return defaults[this.tableType] || defaults['trials'];
    }

    /**
     * Get all available columns for different table types
     */
    getAvailableColumns() {
        const columns = {
            'trials': {
                'title': {
                    label: 'Title',
                    description: 'Clinical trial title',
                    sortable: true,
                    required: true // Cannot be hidden
                },
                'nct_id': {
                    label: 'NCT ID',
                    description: 'ClinicalTrials.gov identifier',
                    sortable: true,
                    required: true
                },
                'organization': {
                    label: 'Organization',
                    description: 'Sponsor organization',
                    sortable: true,
                    required: false
                },
                'user': {
                    label: 'User',
                    description: 'Responsible user email',
                    sortable: true,
                    required: false
                },
                'status': {
                    label: 'Status',
                    description: 'Compliance status',
                    sortable: true,
                    required: false
                },
                'start_date': {
                    label: 'Start Date',
                    description: 'Trial start date',
                    sortable: true,
                    required: false
                },
                'end_date': {
                    label: 'End Date',
                    description: 'Trial completion date',
                    sortable: true,
                    required: false
                },
                'reporting_due_date': {
                    label: 'Reporting Due Date',
                    description: 'Compliance reporting due date',
                    sortable: true,
                    required: false
                },
                'last_checked': {
                    label: 'Last Checked',
                    description: 'Last compliance check date',
                    sortable: true,
                    required: false
                },
                'user_role': {
                    label: 'User Role',
                    description: 'User role in organization',
                    sortable: true,
                    required: false
                },
                'org_created_at': {
                    label: 'Org Created',
                    description: 'Organization creation date',
                    sortable: true,
                    required: false
                }
            },
            'compare': {
                'sponsor': {
                    label: 'Sponsor',
                    description: 'Organization name',
                    sortable: true,
                    required: true
                },
                'funding_source': {
                    label: 'Funding Source',
                    description: 'Source of funding',
                    sortable: true,
                    required: false
                },
                'total_trials': {
                    label: 'Total Trials',
                    description: 'Number of trials',
                    sortable: true,
                    required: false
                },
                'reporting_rate': {
                    label: 'Reporting Rate',
                    description: 'Percentage of trials reported',
                    sortable: true,
                    required: false
                },
                'compliant_trials': {
                    label: 'Compliant Trials',
                    description: 'Number of compliant trials',
                    sortable: true,
                    required: false
                },
                'late_submissions': {
                    label: 'Late Submissions',
                    description: 'Number of late submissions',
                    sortable: true,
                    required: false
                },
                'compliance_rate': {
                    label: 'Compliance Rate',
                    description: 'Overall compliance percentage',
                    sortable: true,
                    required: false
                },
                'wilson_lcb_score': {
                    label: 'Wilson LCB Score',
                    description: 'Wilson Lower Confidence Bound score',
                    sortable: true,
                    required: false
                },
                'email_domain': {
                    label: 'Email Domain',
                    description: 'Organization email domain',
                    sortable: true,
                    required: false
                },
                'created_at': {
                    label: 'Created Date',
                    description: 'Organization creation date',
                    sortable: true,
                    required: false
                }
            }
        };
        return columns[this.tableType] || columns['trials'];
    }

    /**
     * Initialize the column configuration system
     */
    init() {
        this.bindEvents();
        this.applyColumnConfiguration();
    }

    /**
     * Load configuration from localStorage
     */
    loadConfig() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            if (stored) {
                const config = JSON.parse(stored);
                // Ensure all required columns are included
                const requiredColumns = Object.keys(this.availableColumns)
                    .filter(key => this.availableColumns[key].required);
                
                for (const required of requiredColumns) {
                    if (!config.visibleColumns.includes(required)) {
                        config.visibleColumns.push(required);
                    }
                }
                
                return config;
            }
        } catch (e) {
            console.warn('Failed to load column configuration:', e);
        }
        
        return {
            visibleColumns: [...this.defaultColumns],
            columnOrder: [...this.defaultColumns]
        };
    }

    /**
     * Save configuration to localStorage
     */
    saveConfig() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.currentConfig));
        } catch (e) {
            console.warn('Failed to save column configuration:', e);
        }
    }

    /**
     * Show or hide a column
     */
    toggleColumn(columnKey, visible) {
        // Don't allow hiding required columns
        if (!visible && this.availableColumns[columnKey] && this.availableColumns[columnKey].required) {
            return false;
        }

        if (visible && !this.currentConfig.visibleColumns.includes(columnKey)) {
            this.currentConfig.visibleColumns.push(columnKey);
            // Add to column order if not present
            if (!this.currentConfig.columnOrder.includes(columnKey)) {
                this.currentConfig.columnOrder.push(columnKey);
            }
        } else if (!visible) {
            this.currentConfig.visibleColumns = this.currentConfig.visibleColumns
                .filter(col => col !== columnKey);
        }

        this.saveConfig();
        this.applyColumnConfiguration();
        return true;
    }

    /**
     * Get current visible columns in order
     */
    getVisibleColumns() {
        return this.currentConfig.columnOrder
            .filter(col => this.currentConfig.visibleColumns.includes(col));
    }

    /**
     * Check if a column is currently visible
     */
    isColumnVisible(columnKey) {
        return this.currentConfig.visibleColumns.includes(columnKey);
    }

    /**
     * Apply column configuration to the table
     */
    applyColumnConfiguration() {
        const table = document.querySelector(`table[data-table-type="${this.tableType}"]`);
        if (!table) {
            console.warn(`Table with type "${this.tableType}" not found`);
            return;
        }

        const visibleColumns = this.getVisibleColumns();
        
        // Show/hide header columns
        const headers = table.querySelectorAll('thead th[data-column]');
        headers.forEach(header => {
            const columnKey = header.getAttribute('data-column');
            const isVisible = visibleColumns.includes(columnKey);
            header.style.display = isVisible ? '' : 'none';
            
            // Override mobile CSS if user explicitly wants column visible
            if (isVisible) {
                header.style.setProperty('display', '', 'important');
            }
        });

        // Show/hide body columns
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const cells = row.querySelectorAll('td[data-column]');
            cells.forEach(cell => {
                const columnKey = cell.getAttribute('data-column');
                const isVisible = visibleColumns.includes(columnKey);
                cell.style.display = isVisible ? '' : 'none';
                
                // Override mobile CSS if user explicitly wants column visible
                if (isVisible) {
                    cell.style.setProperty('display', '', 'important');
                }
            });
        });

        // Update column toggle UI
        this.updateToggleUI();
        
        // Handle mobile responsive behavior
        this.handleMobileResponsive();
    }

    /**
     * Handle mobile responsive behavior
     */
    handleMobileResponsive() {
        const isMobile = window.innerWidth <= 768; // 48em = 768px
        
        if (isMobile) {
            // Add mobile indicator to dropdown
            const menu = document.getElementById(`column-config-menu-${this.tableType}`);
            if (menu) {
                const existingNote = menu.querySelector('.mobile-note');
                if (!existingNote) {
                    const note = document.createElement('div');
                    note.className = 'mobile-note usa-alert usa-alert--info usa-alert--slim margin-bottom-2';
                    note.innerHTML = `
                        <div class="usa-alert__body">
                            <p class="usa-alert__text font-sans-2xs">
                                On mobile, some columns are hidden by default for better readability. 
                                Use this menu to show/hide specific columns.
                            </p>
                        </div>
                    `;
                    menu.querySelector('.padding-2').insertBefore(note, menu.querySelector('h4'));
                }
            }
        }
    }

    /**
     * Create column toggle UI
     */
    createToggleUI() {
        const container = document.createElement('div');
        container.className = 'column-config-dropdown usa-dropdown position-relative margin-0';
        container.id = `column-config-dropdown-${this.tableType}`;

        container.innerHTML = `
            <button id="column-config-btn-${this.tableType}" 
                    class="usa-button usa-button--secondary margin-0" 
                    type="button"
                    aria-expanded="false" 
                    aria-haspopup="true" 
                    aria-controls="column-config-menu-${this.tableType}"
                    title="Customize table columns">
                <i class="ri-settings-3-line margin-right-05"></i>Columns
                <i class="ri-arrow-down-s-line margin-left-05"></i>
            </button>
            <div id="column-config-menu-${this.tableType}"
                 class="usa-dropdown-menu position-absolute top-auto right-0 bg-white border-1px border-base-lighter shadow-2 z-500 width-card-lg margin-top-05 display-none"
                 role="menu" 
                 aria-labelledby="column-config-btn-${this.tableType}">
                <div class="padding-2">
                    <h4 class="margin-top-0 margin-bottom-2 font-sans-sm text-bold">Show/Hide Columns</h4>
                    <div class="column-toggles">
                        ${this.generateColumnToggles()}
                    </div>
                    <div class="margin-top-2 border-top-1px border-base-lighter padding-top-2">
                        <button type="button" 
                                class="usa-button usa-button--outline usa-button--unstyled font-sans-xs"
                                onclick="columnConfig_${this.tableType}.resetToDefaults()">
                            Reset to defaults
                        </button>
                    </div>
                </div>
            </div>
        `;

        return container;
    }

    /**
     * Generate HTML for column toggle checkboxes
     */
    generateColumnToggles() {
        return Object.entries(this.availableColumns)
            .map(([key, column]) => {
                const isVisible = this.isColumnVisible(key);
                const isRequired = column.required;
                const disabled = isRequired ? 'disabled' : '';
                const requiredText = isRequired ? ' <span class="text-base-light">(required)</span>' : '';
                
                return `
                    <div class="usa-checkbox">
                        <input class="usa-checkbox__input" 
                               id="column-toggle-${this.tableType}-${key}" 
                               type="checkbox" 
                               name="column-toggle"
                               value="${key}"
                               ${isVisible ? 'checked' : ''} 
                               ${disabled}
                               data-column="${key}">
                        <label class="usa-checkbox__label" 
                               for="column-toggle-${this.tableType}-${key}">
                            <span class="column-label-text">
                                ${column.label}${requiredText}
                            </span>
                            <span class="usa-hint">${column.description}</span>
                        </label>
                    </div>
                `;
            }).join('');
    }

    /**
     * Update the toggle UI to reflect current state
     */
    updateToggleUI() {
        Object.keys(this.availableColumns).forEach(columnKey => {
            const checkbox = document.getElementById(`column-toggle-${this.tableType}-${columnKey}`);
            if (checkbox) {
                checkbox.checked = this.isColumnVisible(columnKey);
            }
        });
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Use event delegation for dynamically created elements
        document.addEventListener('click', (e) => {
            // Handle dropdown toggle
            if (e.target.id === `column-config-btn-${this.tableType}` || 
                e.target.closest(`#column-config-btn-${this.tableType}`)) {
                e.stopPropagation();
                this.toggleDropdown();
            }
            
            // Handle column toggle checkboxes
            if (e.target.matches(`input[name="column-toggle"][data-column]`) && 
                e.target.closest(`#column-config-menu-${this.tableType}`)) {
                const columnKey = e.target.getAttribute('data-column');
                this.toggleColumn(columnKey, e.target.checked);
            }

            // Close dropdown when clicking outside
            if (!e.target.closest(`#column-config-dropdown-${this.tableType}`)) {
                this.closeDropdown();
            }
        });

        // Handle keyboard events
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeDropdown();
            }
        });
        
        // Handle window resize for responsive behavior
        window.addEventListener('resize', () => {
            // Debounce the resize event
            clearTimeout(this.resizeTimeout);
            this.resizeTimeout = setTimeout(() => {
                this.handleMobileResponsive();
            }, 250);
        });
    }

    /**
     * Toggle dropdown visibility
     */
    toggleDropdown() {
        const button = document.getElementById(`column-config-btn-${this.tableType}`);
        const menu = document.getElementById(`column-config-menu-${this.tableType}`);
        
        if (!button || !menu) return;

        const isExpanded = button.getAttribute('aria-expanded') === 'true';
        
        if (isExpanded) {
            this.closeDropdown();
        } else {
            this.openDropdown();
        }
    }

    /**
     * Open dropdown
     */
    openDropdown() {
        const button = document.getElementById(`column-config-btn-${this.tableType}`);
        const menu = document.getElementById(`column-config-menu-${this.tableType}`);
        
        if (!button || !menu) return;

        button.setAttribute('aria-expanded', 'true');
        menu.classList.remove('display-none');
    }

    /**
     * Close dropdown
     */
    closeDropdown() {
        const button = document.getElementById(`column-config-btn-${this.tableType}`);
        const menu = document.getElementById(`column-config-menu-${this.tableType}`);
        
        if (!button || !menu) return;

        button.setAttribute('aria-expanded', 'false');
        menu.classList.add('display-none');
    }

    /**
     * Reset to default column configuration
     */
    resetToDefaults() {
        this.currentConfig = {
            visibleColumns: [...this.defaultColumns],
            columnOrder: [...this.defaultColumns]
        };
        this.saveConfig();
        this.applyColumnConfiguration();
    }

    /**
     * Insert the column toggle UI into the specified container
     */
    insertToggleUI(container) {
        if (typeof container === 'string') {
            container = document.querySelector(container);
        }
        
        if (!container) {
            console.warn('Container for column toggle UI not found');
            return;
        }

        const toggleUI = this.createToggleUI();
        container.appendChild(toggleUI);
        
        // Make instance available globally for reset button
        window[`columnConfig_${this.tableType}`] = this;
    }
}

// Export for use in other scripts
window.TableColumnConfig = TableColumnConfig; 