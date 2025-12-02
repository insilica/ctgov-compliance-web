(function () {
    const reportingData = window.reportingData || {};
    const dataset = reportingData.time_series || [];
    const statusKeys = reportingData.status_keys || [];
    const kpiData = reportingData.kpis || {};

    const timelineElement = document.getElementById('reporting-chart');
    const newCompletedElement = document.getElementById('reporting-new-completed-chart');

    if (typeof window.d3 === 'undefined') {
        if (timelineElement) {
            timelineElement.innerHTML = '<p class="usa-hint">D3 failed to load. Please refresh the page.</p>';
        }
        return;
    }

    const d3 = window.d3;
    const parsedDates = dataset.map((item) => new Date(`${item.date}T00:00:00`));

    const formatComma = d3.format(',');
    const formatPercent = d3.format('.1f');
    const formatDays = (value) => {
        if (typeof value !== 'number') {
            return '—';
        }
        const formatted = d3.format('.1f')(value || 0);
        return formatted.replace(/\.0$/, '');
    };

    const getTimeBounds = () => {
        if (!parsedDates.length) {
            const today = new Date();
            const nextMonth = new Date(today.getTime());
            nextMonth.setMonth(nextMonth.getMonth() + 1);
            return [today, nextMonth];
        }
        const extent = d3.extent(parsedDates);
        const [start, end] = extent;
        if (start && end && start.getTime() !== end.getTime()) {
            return extent;
        }
        const anchor = start || end || new Date();
        const paddedEnd = new Date(anchor.getTime());
        paddedEnd.setMonth(paddedEnd.getMonth() + 1);
        return [anchor, paddedEnd];
    };

    const getTimeDomainMeta = () => {
        const bounds = getTimeBounds();
        const baseScale = d3.scaleTime().domain(bounds);
        const tickCount = dataset.length ? Math.min(dataset.length, 8) : 4;
        return {
            bounds,
            ticks: baseScale.ticks(tickCount)
        };
    };

    const createTooltip = (container) => {
        return d3.select(container)
            .append('div')
            .attr('class', 'reporting-tooltip')
            .style('display', 'none');
    };

    const renderTimelineChart = () => {
        if (!timelineElement) {
            return;
        }
        timelineElement.innerHTML = '';

        if (!dataset.length || !statusKeys.length) {
            timelineElement.innerHTML = '<p class="usa-hint">No data available for the selected range.</p>';
            return;
        }

        const width = timelineElement.clientWidth || 960;
        const height = 360;
        const margin = { top: 20, right: 24, bottom: 40, left: 56 };

        const svg = d3.select(timelineElement)
            .append('svg')
            .attr('width', width)
            .attr('height', height + margin.top + margin.bottom)
            .append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        const innerWidth = width - margin.left - margin.right;
        const innerHeight = height - margin.top - margin.bottom;

        const { bounds, ticks } = getTimeDomainMeta();
        const xScale = d3.scaleTime().domain(bounds).range([0, innerWidth]);
        const maxCumulative = d3.max(dataset, (item) => {
            return d3.max(statusKeys, (status) => {
                return Number(item.statuses?.[status.key]?.cumulative || 0);
            });
        }) || 0;

        const yScale = d3.scaleLinear()
            .domain([0, maxCumulative ? maxCumulative * 1.05 : 1])
            .nice()
            .range([innerHeight, 0]);

        const xAxis = d3.axisBottom(xScale)
            .tickValues(ticks)
            .tickFormat(d3.timeFormat('%b %Y'));
        const yAxis = d3.axisLeft(yScale).ticks(6).tickFormat(d3.format('d'));

        svg.append('g')
            .attr('transform', `translate(0,${innerHeight})`)
            .call(xAxis)
            .selectAll('text')
            .style('text-anchor', 'end')
            .attr('transform', 'rotate(-35)');

        svg.append('g').call(yAxis);

        const hoverLine = svg.append('line')
            .attr('class', 'reporting-hover-line')
            .attr('y1', 0)
            .attr('y2', innerHeight)
            .attr('stroke', '#6b6b6b')
            .attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '4 4')
            .style('opacity', 0);

        const hoverCapture = svg.append('rect')
            .attr('class', 'reporting-hover-capture')
            .attr('width', innerWidth)
            .attr('height', innerHeight)
            .attr('fill', 'transparent')
            .style('pointer-events', 'all');

        const handleHoverMove = (event) => {
            const [x] = d3.pointer(event);
            const clampedX = Math.max(0, Math.min(innerWidth, x));
            hoverLine
                .attr('x1', clampedX)
                .attr('x2', clampedX)
                .style('opacity', 1);
        };

        hoverCapture.on('mousemove.hoverline', handleHoverMove);

        const colors = d3.scaleOrdinal()
            .domain(statusKeys.map((s) => s.key))
            .range(['#005ea2', '#e52207', '#fdb81e', '#4aae99', '#7d48a1', '#d85da0']);

        const series = statusKeys.map((status) => ({
            label: status.label,
            key: status.key,
            values: dataset.map((item, index) => ({
                date: parsedDates[index],
                cumulative: Number(item.statuses?.[status.key]?.cumulative || 0),
                monthly: Number(item.statuses?.[status.key]?.monthly || 0),
                monthLabel: item.month_label
            }))
        }));

        const lineGenerator = d3.line()
            .curve(d3.curveMonotoneX)
            .x((d) => xScale(d.date))
            .y((d) => yScale(d.cumulative));

        series.forEach((statusSeries) => {
            svg.append('path')
                .datum(statusSeries.values)
                .attr('fill', 'none')
                .attr('stroke', colors(statusSeries.key))
                .attr('stroke-width', 2)
                .attr('d', lineGenerator);
        });

        const tooltip = createTooltip(timelineElement);

        series.forEach((statusSeries) => {
            svg.selectAll(`.reporting-point-${statusSeries.key}`)
                .data(statusSeries.values)
                .enter()
                .append('circle')
                .attr('class', `reporting-point reporting-point-${statusSeries.key}`)
                .attr('cx', (d) => xScale(d.date))
                .attr('cy', (d) => yScale(d.cumulative))
                .attr('r', 4)
                .attr('fill', colors(statusSeries.key))
                .on('mouseenter', function (event, d) {
                    const bounds = timelineElement.getBoundingClientRect();
                    tooltip.style('display', 'block')
                        .style('left', `${event.clientX - bounds.left + 12}px`)
                        .style('top', `${event.clientY - bounds.top - 28}px`)
                        .html(`<strong>${statusSeries.label}</strong><br>${d.monthLabel}<br>${d.monthly} new · ${d.cumulative} cumulative`);
                    d3.select(this).attr('r', 6);
                })
                .on('mouseleave', function () {
                    tooltip.style('display', 'none');
                    d3.select(this).attr('r', 4);
                });
        });
    };

    const renderNewCompletedChart = () => {
        if (!newCompletedElement) {
            return;
        }
        newCompletedElement.innerHTML = '';

        if (!dataset.length) {
            newCompletedElement.innerHTML = '<p class="usa-hint">No trial data available for this range.</p>';
            return;
        }

        const width = newCompletedElement.clientWidth || 500;
        const height = 260;
        const margin = { top: 16, right: 16, bottom: 52, left: 56 };
        const svg = d3.select(newCompletedElement)
            .append('svg')
            .attr('width', width)
            .attr('height', height + margin.top + margin.bottom)
            .append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        const innerWidth = width - margin.left - margin.right;
        const innerHeight = height - margin.top - margin.bottom;
        const { bounds, ticks } = getTimeDomainMeta();
        const xScale = d3.scaleTime().domain(bounds).range([0, innerWidth]);

        const stackData = dataset.map((item, index) => {
            const newCount = Math.max(0, Number(item.new_trials || 0));
            const completedCount = Math.max(0, Number(item.completed_trials || 0));
            return {
                date: parsedDates[index],
                monthLabel: item.month_label,
                totals: {
                    newCount,
                    completedCount
                },
                segments: [
                    { key: 'new_trials', value: newCount },
                    { key: 'completed_trials', value: completedCount }
                ]
            };
        });

        const maxCount = d3.max(stackData, (item) => {
            return item.segments.reduce((sum, segment) => sum + segment.value, 0);
        }) || 0;

        const yScale = d3.scaleLinear()
            .domain([0, maxCount ? maxCount * 1.2 : 1])
            .nice()
            .range([innerHeight, 0]);

        const xAxis = d3.axisBottom(xScale)
            .tickValues(ticks)
            .tickFormat(d3.timeFormat('%b %Y'));
        const yAxis = d3.axisLeft(yScale).ticks(5).tickFormat(d3.format('d'));

        svg.append('g')
            .attr('transform', `translate(0,${innerHeight})`)
            .call(xAxis)
            .selectAll('text')
            .style('text-anchor', 'end')
            .attr('transform', 'rotate(-35)');

        svg.append('g').call(yAxis);

        const computeBarWidth = () => {
            if (parsedDates.length < 2) {
                return Math.min(48, Math.max(18, innerWidth * 0.15));
            }
            const gaps = [];
            for (let i = 1; i < parsedDates.length; i += 1) {
                gaps.push(Math.abs(xScale(parsedDates[i]) - xScale(parsedDates[i - 1])));
            }
            const avgGap = gaps.length ? d3.mean(gaps) : innerWidth / parsedDates.length;
            return Math.min(56, Math.max(14, (avgGap || 20) * 0.5));
        };

        const barWidth = computeBarWidth();
        const colors = { new_trials: '#DC602E', completed_trials: '#450920' };
        const tooltip = createTooltip(newCompletedElement);
        const bars = svg.selectAll('.stack-bar')
            .data(stackData)
            .enter()
            .append('g')
            .attr('class', 'stack-bar')
            .attr('transform', (d) => {
                const xPos = Math.max(2, xScale(d.date) - (barWidth / 2));
                return `translate(${xPos},0)`;
            });

        bars.selectAll('rect')
            .data((d) => {
                let offset = 0;
                return d.segments.map((segment) => {
                    const start = offset;
                    offset += segment.value;
                    return {
                        key: segment.key,
                        value: segment.value,
                        y0: start,
                        y1: offset,
                        monthLabel: d.monthLabel,
                        date: d.date,
                        totals: d.totals,
                        color: colors[segment.key],
                        label: segment.key === 'new_trials' ? 'New trials' : 'Completed trials'
                    };
                }).filter((segment) => segment.value > 0);
            })
            .enter()
            .append('rect')
            .attr('x', 0)
            .attr('width', barWidth)
            .attr('y', (segment) => yScale(segment.y1))
            .attr('height', (segment) => yScale(segment.y0) - yScale(segment.y1))
            .attr('fill', (segment) => segment.color)
            .attr('rx', 2)
            .on('mouseenter', (event, segment) => {
                const bounds = newCompletedElement.getBoundingClientRect();
                const total = segment.totals.newCount + segment.totals.completedCount;
                tooltip.style('display', 'block')
                    .style('left', `${event.clientX - bounds.left + 12}px`)
                    .style('top', `${event.clientY - bounds.top - 28}px`)
                    .html(`<strong>${segment.monthLabel}</strong><br>${segment.label}: ${formatComma(segment.value)}<br>New: ${formatComma(segment.totals.newCount)} · Completed: ${formatComma(segment.totals.completedCount)}<br>Total: ${formatComma(total)}`);
            })
            .on('mouseleave', () => {
                tooltip.style('display', 'none');
            });

        const legend = d3.select(newCompletedElement)
            .append('div')
            .attr('class', 'reporting-chart-legend');

        [
            { label: 'New trials', color: colors.new_trials },
            { label: 'Completed trials', color: colors.completed_trials }
        ].forEach((item) => {
            const entry = legend.append('div').attr('class', 'reporting-chart-legend__item');
            entry.append('span')
                .attr('class', 'reporting-chart-legend__swatch')
                .style('background', item.color);
            entry.append('span').text(item.label);
        });
    };

    const renderCharts = () => {
        renderTimelineChart();
        renderNewCompletedChart();
    };

    const renderKpis = () => {
        if (!kpiData || typeof kpiData !== 'object') {
            return;
        }

        const totalNode = document.querySelector('[data-kpi="totalTrials"]');
        const complianceNode = document.querySelector('[data-kpi="complianceGauge"]');
        const issueNode = document.querySelector('[data-kpi="issueCount"]');
        const delayNode = document.querySelector('[data-kpi="avgDelay"]');

        if (totalNode) {
            const totalValue = Number(kpiData.total_trials || 0);
            const node = d3.select(totalNode);
            node.html('');
            const wrapper = node.append('div').attr('class', 'kpi-value');
            wrapper.append('span')
                .attr('class', 'kpi-value__number')
                .text(formatComma(totalValue));
        }

        if (issueNode) {
            const issueValue = Number(kpiData.trials_with_issues_count || 0);
            const node = d3.select(issueNode);
            node.html('');
            const wrapper = node.append('div').attr('class', 'kpi-value');
            wrapper.append('span')
                .attr('class', 'kpi-value__number')
                .text(formatComma(issueValue));
        }

        if (delayNode) {
            const delayValue = Number(kpiData.avg_reporting_delay_days || 0);
            const node = d3.select(delayNode);
            node.html('');
            const wrapper = node.append('div').attr('class', 'kpi-value');
            wrapper.append('span')
                .attr('class', 'kpi-value__number')
                .text(`${formatDays(delayValue)} days`);
        }

        if (complianceNode) {
            const node = d3.select(complianceNode);
            node.html('');
            const rate = Math.max(0, Math.min(100, Number(kpiData.overall_compliance_rate || 0)));
            const compliantColor = '#005ea2';
            const remainderColor = '#e52207';
            const size = 120;
            const thickness = 14;
            const radius = (size / 2) - 6;
            const center = size / 2;
            const startAngle = -Math.PI / 2;
            const arcGenerator = d3.arc()
                .innerRadius(radius - thickness)
                .outerRadius(radius);

            const svg = node.append('svg')
                .attr('class', 'kpi-gauge')
                .attr('viewBox', `0 0 ${size} ${size}`)
                .attr('aria-hidden', 'true')
                .attr('focusable', 'false');

            svg.append('path')
                .attr('class', 'kpi-gauge__track')
                .attr('d', arcGenerator({ startAngle: 0, endAngle: Math.PI * 2 }))
                .attr('transform', `translate(${center},${center})`)
                .attr('fill', remainderColor)
                .attr('opacity', 0.25);

            svg.append('path')
                .attr('class', 'kpi-gauge__value')
                .attr('d', arcGenerator({
                    startAngle,
                    endAngle: startAngle + (Math.PI * 2 * (rate / 100))
                }))
                .attr('transform', `translate(${center},${center})`)
                .attr('fill', compliantColor);

            svg.append('text')
                .attr('class', 'kpi-gauge__label')
                .attr('x', center)
                .attr('y', center + 6)
                .attr('text-anchor', 'middle')
                .text(`${formatPercent(rate)}%`)
                .attr('fill', compliantColor);
        }
    };

    renderCharts();
    renderKpis();

    window.addEventListener('resize', () => {
        window.requestAnimationFrame(() => {
            renderCharts();
            renderKpis();
        });
    });
})();
