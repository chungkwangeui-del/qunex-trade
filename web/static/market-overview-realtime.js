// Market Overview Real-time Data Script

// Update Market Overview with real-time data
async function updateMarketOverview() {
    try {
        const response = await fetch('/api/market-overview-v2');
        const data = await response.json();

        // Update S&P 500
        updateIndexCard('sp500', data.sp500);

        // Update DOW
        updateIndexCard('dow', data.dow);

        // Update NASDAQ
        updateIndexCard('nasdaq', data.nasdaq);

        // Update VIX
        updateIndexCard('vix', data.vix);

        // Update Fear & Greed
        if (data.fearGreed) {
            const fearGreedElement = document.getElementById('fear-greed-value');
            const fearGreedLabel = document.getElementById('fear-greed-label');
            if (fearGreedElement) {
                fearGreedElement.textContent = data.fearGreed.value;
            }
            if (fearGreedLabel) {
                fearGreedLabel.textContent = data.fearGreed.label;
            }
        }
    } catch (error) {
        // Error updating market overview - silent fail
    }
}

function updateIndexCard(indexKey, indexData) {
    const valueElement = document.getElementById(`${indexKey}-value`);
    const changeElement = document.getElementById(`${indexKey}-change`);
    const percentElement = document.getElementById(`${indexKey}-percent`);

    if (valueElement) {
        valueElement.textContent = indexData.value.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    if (changeElement && percentElement) {
        const isPositive = indexData.change >= 0;
        const changeText = (isPositive ? '+' : '') + indexData.change.toFixed(2);
        const percentText = '(' + (isPositive ? '+' : '') + indexData.changePercent.toFixed(2) + '%)';

        changeElement.textContent = changeText;
        percentElement.textContent = percentText;

        // Update color
        changeElement.className = isPositive ? 'text-success' : 'text-danger';
        percentElement.className = isPositive ? 'text-success' : 'text-danger';
    }
}

// Load data on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        updateMarketOverview();
        // Refresh every 60 seconds
        setInterval(updateMarketOverview, 60000);
    });
} else {
    updateMarketOverview();
    // Refresh every 60 seconds
    setInterval(updateMarketOverview, 60000);
}
