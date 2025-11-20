(function () {
    const chartElement = document.getElementById('reporting-chart');
    const reportingData = window.reportingData || {};
    const dataset = reportingData.time_series || [];
    const statusKeys = reportingData.status_keys || [];

    if (!chartElement) {
        return;
    }

    if (typeof window.d3 === 'undefined') {
        chartElement.innerHTML = '<p class="usa-hint">D3 failed to load. Please refresh the page.</p>';
        return;
    }

    const d3 = window.d3;

    const renderChart = () => {
        chartElement.innerHTML = '';

        if (!dataset.length || !statusKeys.length) {
            chartElement.innerHTML = '<p class="usa-hint">No data available for the selected range.</p>';
            return;
        }

        const width = chartElement.clientWidth || 960;
        const height = 360;
        const margin = { top: 20, right: 24, bottom: 40, left: 56 };

        const svg = d3.select(chartElement)
            .append('svg')
            .attr('width', width)
            .attr('height', height + margin.top + margin.bottom)
            .append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        const innerWidth = width - margin.left - margin.right;
        const innerHeight = height - margin.top - margin.bottom;

        const parsedDates = dataset.map((item) => new Date(item.date + 'T00:00:00'));
        const timeExtent = d3.extent(parsedDates);
        const xScale = d3.scaleTime()
            .domain(timeExtent)
            .range([0, innerWidth]);

        const maxCumulative = d3.max(dataset, (item) => {
            return d3.max(statusKeys, (status) => {
                return Number(item.statuses?.[status.key]?.cumulative || 0);
            });
        }) || 0;
        const yScale = d3.scaleLinear()
            .domain([0, maxCumulative * 1.05 || 1])
            .nice()
            .range([innerHeight, 0]);

        const xAxis = d3.axisBottom(xScale)
            .ticks(Math.min(dataset.length, 8))
            .tickFormat(d3.timeFormat('%b %Y'));
        const yAxis = d3.axisLeft(yScale).ticks(6).tickFormat(d3.format('d'));

        svg.append('g')
            .attr('transform', `translate(0,${innerHeight})`)
            .call(xAxis)
            .selectAll('text')
            .style('text-anchor', 'end')
            .attr('transform', 'rotate(-35)');

        svg.append('g').call(yAxis);

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

        const tooltip = d3.select(chartElement)
            .append('div')
            .attr('class', 'reporting-tooltip')
            .style('position', 'absolute')
            .style('pointer-events', 'none')
            .style('background', 'rgba(0,0,0,0.75)')
            .style('color', '#fff')
            .style('padding', '0.5rem 0.75rem')
            .style('border-radius', '4px')
            .style('font-size', '0.85rem')
            .style('display', 'none');

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
                    const bounds = chartElement.getBoundingClientRect();
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

        const legendElement = document.getElementById('reporting-chart-legend');
        if (legendElement) {
            legendElement.innerHTML = '';
            const list = document.createElement('ul');
            list.className = 'usa-list usa-list--unstyled display-flex flex-wrap';

            statusKeys.forEach((status) => {
                const item = document.createElement('li');
                item.className = 'margin-right-3 margin-bottom-1 display-flex flex-align-center';
                const swatch = document.createElement('span');
                swatch.style.backgroundColor = colors(status.key);
                swatch.style.width = '1rem';
                swatch.style.height = '1rem';
                swatch.style.display = 'inline-block';
                swatch.style.marginRight = '0.5rem';
                swatch.style.borderRadius = '999px';
                const label = document.createElement('span');
                label.textContent = status.label;
                item.appendChild(swatch);
                item.appendChild(label);
                list.appendChild(item);
            });

            legendElement.appendChild(list);
        }
    };

    renderChart();
    window.addEventListener('resize', () => {
        window.requestAnimationFrame(renderChart);
    });
})();
