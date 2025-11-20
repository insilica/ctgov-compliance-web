(function () {
    const chartElement = document.getElementById('reporting-chart');
    const legendElement = document.getElementById('reporting-chart-legend');
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
    const colors = d3.scaleOrdinal()
        .domain(statusKeys.map((s) => s.key))
        .range(['#005ea2', '#e52207', '#fdb81e', '#4aae99', '#7d48a1']);

    const renderChart = () => {
        chartElement.innerHTML = '';
        if (legendElement) {
            legendElement.innerHTML = '';
        }

        if (!dataset.length || !statusKeys.length || !window.d3) {
            chartElement.innerHTML = '<p class="usa-hint">Unable to display chart data.</p>';
            return;
        }

        const width = chartElement.clientWidth || 960;
        const height = 360;
        const margin = { top: 20, right: 24, bottom: 40, left: 48 };

        const series = statusKeys.map((status) => ({
            label: status.label,
            key: status.key,
            values: dataset.map((item) => ({
                date: new Date(item.date + 'T00:00:00'),
                count: Number(item[status.key] || 0),
            })),
        }));

        const allCounts = series.flatMap((s) => s.values.map((v) => v.count));
        const maxCount = Math.max(5, d3.max(allCounts));

        const svg = d3.select(chartElement)
            .append('svg')
            .attr('width', width)
            .attr('height', height + margin.top + margin.bottom)
            .append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        const innerWidth = width - margin.left - margin.right;
        const innerHeight = height - margin.top - margin.bottom;

        const timeExtent = d3.extent(dataset, (d) => new Date(d.date + 'T00:00:00'));
        const xScale = d3.scaleTime()
            .domain(timeExtent)
            .range([0, innerWidth]);

        const yScale = d3.scaleLinear()
            .domain([0, maxCount])
            .nice()
            .range([innerHeight, 0]);

        const xAxis = d3.axisBottom(xScale).ticks(6).tickFormat(d3.timeFormat('%b %d'));
        const yAxis = d3.axisLeft(yScale).ticks(5).tickFormat(d3.format('d'));

        svg.append('g')
            .attr('transform', `translate(0,${innerHeight})`)
            .call(xAxis);

        svg.append('g')
            .call(yAxis);

        const lineGenerator = d3.line()
            .curve(d3.curveMonotoneX)
            .x((d) => xScale(d.date))
            .y((d) => yScale(d.count));

        series.forEach((statusSeries) => {
            svg.append('path')
                .datum(statusSeries.values)
                .attr('class', 'reporting-line')
                .attr('fill', 'none')
                .attr('stroke', colors(statusSeries.key))
                .attr('stroke-width', 2)
                .attr('d', lineGenerator);
        });

        // Points and tooltip
        const tooltip = d3.select(chartElement)
            .append('div')
            .attr('class', 'reporting-tooltip')
            .style('position', 'absolute')
            .style('pointer-events', 'none')
            .style('background', 'rgba(0,0,0,0.75)')
            .style('color', '#fff')
            .style('padding', '0.5rem')
            .style('border-radius', '4px')
            .style('font-size', '0.85rem')
            .style('display', 'none');

        const formatDate = d3.timeFormat('%B %d, %Y');

        series.forEach((statusSeries) => {
            svg.selectAll(`.reporting-point-${statusSeries.key}`)
                .data(statusSeries.values)
                .enter()
                .append('circle')
                .attr('class', `reporting-point reporting-point-${statusSeries.key}`)
                .attr('cx', (d) => xScale(d.date))
                .attr('cy', (d) => yScale(d.count))
                .attr('r', 3)
                .attr('fill', colors(statusSeries.key))
                .on('mouseenter', (event, d) => {
                    tooltip.style('display', 'block')
                        .style('left', `${event.offsetX + 20}px`)
                        .style('top', `${event.offsetY}px`)
                        .html(`<strong>${statusSeries.label}</strong><br>${formatDate(d.date)}<br>${d.count} checks`);
                })
                .on('mouseleave', () => {
                    tooltip.style('display', 'none');
                });
        });

        if (legendElement) {
            const latest = dataset[dataset.length - 1];
            const legendList = document.createElement('ul');
            legendList.className = 'usa-list usa-list--unstyled display-flex flex-wrap';

            statusKeys.forEach((status) => {
                const item = document.createElement('li');
                item.className = 'margin-right-4 margin-bottom-1 display-flex flex-align-center';
                const swatch = document.createElement('span');
                swatch.style.backgroundColor = colors(status.key);
                swatch.style.display = 'inline-block';
                swatch.style.width = '1rem';
                swatch.style.height = '1rem';
                swatch.style.marginRight = '0.5rem';
                swatch.style.borderRadius = '999px';
                const label = document.createElement('span');
                const latestValue = latest ? Number(latest[status.key] || 0) : 0;
                label.textContent = `${status.label} (${latestValue})`;
                item.appendChild(swatch);
                item.appendChild(label);
                legendList.appendChild(item);
            });
            legendElement.appendChild(legendList);
        }
    };

    renderChart();
    window.addEventListener('resize', () => {
        window.requestAnimationFrame(renderChart);
    });
})();
