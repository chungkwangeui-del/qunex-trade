// Finviz-style D3.js Treemap Implementation

function createFinvizTreemap() {
    console.log('=== createFinvizTreemap called ===');
    const container = document.getElementById('sector-treemap');
    console.log('Container:', container);

    if (!container) {
        console.error('Container #sector-treemap not found!');
        return;
    }

    // Clear existing content
    container.innerHTML = '';

    // Get container dimensions
    const width = container.offsetWidth;
    const height = 600;

    // Create SVG
    const svg = d3.select('#sector-treemap')
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .style('font-family', '"Space Grotesk", sans-serif');

    // Get data
    const data = generateFinvizData();

    // Create hierarchy
    const root = d3.hierarchy(data)
        .sum(d => d.value)
        .sort((a, b) => b.value - a.value);

    // Create treemap layout
    d3.treemap()
        .size([width, height])
        .paddingInner(2)
        .paddingOuter(4)
        .paddingTop(20)
        .round(true)
        (root);

    // Helper: Get color based on performance
    function getColor(change) {
        const val = parseFloat(change);
        if (val >= 3) return '#00b050';
        if (val >= 1.5) return '#26c281';
        if (val >= 0.5) return '#5dd39e';
        if (val >= 0.1) return '#a8ddb5';
        if (val >= -0.1) return '#7f8c8d';
        if (val >= -0.5) return '#fc9272';
        if (val >= -1.5) return '#ef6548';
        if (val >= -3) return '#d7301f';
        return '#a50f15';
    }

    // Create groups for each node
    const nodes = svg.selectAll('g')
        .data(root.descendants())
        .join('g')
        .attr('transform', d => `translate(${d.x0},${d.y0})`);

    // Add rectangles
    nodes.append('rect')
        .attr('width', d => d.x1 - d.x0)
        .attr('height', d => d.y1 - d.y0)
        .attr('fill', d => {
            if (d.depth === 0) return '#0a0e1a'; // Root
            if (d.depth === 1) return '#1a1f3a'; // Sector
            if (d.depth === 2) return '#131829'; // Subcategory
            return getColor(d.data.change); // Stock
        })
        .attr('stroke', '#000')
        .attr('stroke-width', d => d.depth === 1 ? 2 : 1)
        .attr('opacity', d => d.depth <= 2 ? 0.9 : 1);

    // Add sector labels (depth 1)
    nodes.filter(d => d.depth === 1)
        .append('text')
        .attr('x', 5)
        .attr('y', 15)
        .text(d => d.data.name.toUpperCase())
        .attr('font-size', '11px')
        .attr('font-weight', '700')
        .attr('fill', '#fff')
        .attr('text-shadow', '0 1px 3px rgba(0,0,0,0.9)')
        .style('pointer-events', 'none');

    // Add subcategory labels (depth 2)
    nodes.filter(d => d.depth === 2)
        .append('text')
        .attr('x', 3)
        .attr('y', 10)
        .text(d => {
            const width = d.x1 - d.x0;
            if (width < 120) return '';
            const text = d.data.name.toUpperCase();
            // Truncate if too long
            if (text.length > 25) return text.substring(0, 22) + '...';
            return text;
        })
        .attr('font-size', '8px')
        .attr('font-weight', '600')
        .attr('fill', '#999')
        .attr('text-shadow', '0 1px 2px rgba(0,0,0,0.9)')
        .style('pointer-events', 'none');

    // Add stock labels (depth 3 - leaf nodes)
    const stockNodes = nodes.filter(d => d.depth === 3);

    // Add ticker
    stockNodes.append('text')
        .attr('x', d => (d.x1 - d.x0) / 2)
        .attr('y', d => (d.y1 - d.y0) / 2 - 3)
        .text(d => {
            const width = d.x1 - d.x0;
            const height = d.y1 - d.y0;
            if (width < 35 || height < 25) return '';
            return d.data.name;
        })
        .attr('font-size', '10px')
        .attr('font-weight', '700')
        .attr('fill', '#fff')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('text-shadow', '0 1px 4px rgba(0,0,0,1)')
        .style('pointer-events', 'none');

    // Add change percentage
    stockNodes.append('text')
        .attr('x', d => (d.x1 - d.x0) / 2)
        .attr('y', d => (d.y1 - d.y0) / 2 + 9)
        .text(d => {
            const width = d.x1 - d.x0;
            const height = d.y1 - d.y0;
            if (width < 45 || height < 35) return '';
            const val = parseFloat(d.data.change);
            return (val >= 0 ? '+' : '') + val + '%';
        })
        .attr('font-size', '9px')
        .attr('font-weight', '600')
        .attr('fill', '#fff')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('text-shadow', '0 1px 4px rgba(0,0,0,1)')
        .style('pointer-events', 'none');

    // Add hover effect
    nodes.filter(d => d.depth === 3)
        .on('mouseover', function() {
            d3.select(this).select('rect')
                .attr('opacity', 1.2)
                .attr('stroke', '#fff')
                .attr('stroke-width', 2);
        })
        .on('mouseout', function() {
            d3.select(this).select('rect')
                .attr('opacity', 1)
                .attr('stroke', '#000')
                .attr('stroke-width', 1);
        });
}

// Initialize on page load
function initTreemap() {
    console.log('Initializing Finviz treemap...');
    console.log('D3 available:', typeof d3 !== 'undefined');
    console.log('Container exists:', document.getElementById('sector-treemap') !== null);

    if (typeof d3 === 'undefined') {
        console.error('D3.js not loaded!');
        return;
    }

    if (typeof generateFinvizData === 'undefined') {
        console.error('Finviz data not loaded!');
        return;
    }

    try {
        createFinvizTreemap();
        console.log('Treemap created successfully!');

        // Refresh every 60 seconds
        setInterval(createFinvizTreemap, 60000);
    } catch (error) {
        console.error('Error creating treemap:', error);
    }
}

// Try both methods
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTreemap);
} else {
    // DOM already loaded
    initTreemap();
}
