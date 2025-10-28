// Real-time Finviz-style stock data
// Fetches actual market data from backend API

// Market cap values (in billions) for sizing - these are static/approximate
const marketCaps = {
    // Technology
    'AAPL': 3000, 'MSFT': 2800, 'NVDA': 1200, 'AVGO': 700, 'ORCL': 350, 'CRM': 280,
    'ADBE': 250, 'AMD': 240, 'QCOM': 195, 'INTC': 180, 'TXN': 165, 'AMAT': 145,
    'LRCX': 95, 'ADI': 95, 'MU': 115, 'KLAC': 75, 'PANW': 100, 'CRWD': 85,
    'NOW': 120, 'SNOW': 45, 'INTU': 150, 'UBER': 145, 'WDAY': 65, 'TEAM': 55,
    'SMCI': 25, 'HPQ': 35, 'DELL': 85, 'NTAP': 25,

    // Financials
    'BRK-B': 900, 'JPM': 580, 'V': 550, 'MA': 420, 'BAC': 320, 'WFC': 195,
    'C': 125, 'AXP': 175, 'MS': 160, 'GS': 145, 'SCHW': 130, 'SPGI': 145,
    'BLK': 135, 'MCO': 110, 'MSCI': 55, 'PGR': 85, 'TRV': 55, 'ALL': 45,
    'PRU': 40, 'MET': 35,

    // Healthcare
    'LLY': 750, 'UNH': 500, 'JNJ': 380, 'ABBV': 320, 'MRK': 280, 'PFE': 145,
    'BMY': 95, 'CVS': 80, 'CI': 95, 'ELV': 115, 'HUM': 75, 'ISRG': 140,
    'ABT': 195, 'MDT': 115, 'TMO': 220, 'DHR': 195, 'SYK': 125,
    'AMGN': 145, 'GILD': 110, 'REGN': 95, 'VRTX': 110,

    // Communication
    'GOOGL': 1950, 'META': 1300, 'NFLX': 280, 'DIS': 200, 'T': 125, 'VZ': 170,
    'TMUS': 195, 'WBD': 30,

    // Consumer Discretionary
    'AMZN': 1900, 'TSLA': 800, 'HD': 380, 'MCD': 210, 'NKE': 180, 'BKNG': 140,
    'EBAY': 28, 'F': 45, 'GM': 55, 'SBUX': 105, 'CMG': 75, 'YUM': 38,
    'LOW': 145, 'TJX': 115, 'LULU': 45,

    // Consumer Staples
    'WMT': 550, 'PG': 390, 'KO': 280, 'PEP': 230, 'COST': 380, 'TGT': 68,
    'CL': 75, 'KMB': 48, 'MDLZ': 92, 'GIS': 35, 'K': 25, 'PM': 175,
    'MO': 85, 'BTI': 75,

    // Industrials
    'GE': 180, 'CAT': 170, 'RTX': 150, 'UPS': 120, 'LMT': 125, 'BA': 135,
    'NOC': 75, 'DE': 125, 'UNP': 145, 'NSC': 55, 'CSX': 70, 'FDX': 75,

    // Energy
    'XOM': 480, 'CVX': 280, 'COP': 140, 'EOG': 68, 'PXD': 65, 'MRO': 18,

    // Materials
    'LIN': 210, 'APD': 70, 'ECL': 60, 'SHW': 85, 'NUE': 35,

    // Real Estate
    'PLD': 120, 'AMT': 100, 'CCI': 70,

    // Utilities
    'NEE': 150, 'DUK': 80, 'SO': 90, 'D': 68, 'EXC': 45
};

// Global variable to store fetched data
let globalStockData = null;

// Fetch real-time stock data from backend
async function fetchRealTimeData() {
    try {
        console.log('Fetching real-time stock data from /api/sector-stocks-v2...');
        const response = await fetch('/api/sector-stocks-v2');

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Real-time data fetched successfully:', data);

        globalStockData = data;
        return data;

    } catch (error) {
        console.error('Error fetching real-time data:', error);
        // Return null to trigger fallback to random data
        return null;
    }
}

// Generate Finviz data structure with real-time data
async function generateFinvizData() {
    // Fetch real-time data
    const realtimeData = await fetchRealTimeData();

    if (!realtimeData || Object.keys(realtimeData).length === 0) {
        console.warn('Using fallback random data');
        return generateFallbackData();
    }

    // Build D3 hierarchy structure from API data
    const children = [];

    for (const [sectorName, subcategories] of Object.entries(realtimeData)) {
        const sectorChildren = [];

        for (const [subcategoryName, stocks] of Object.entries(subcategories)) {
            const subcategoryChildren = stocks.map(stock => ({
                name: stock.symbol,
                value: marketCaps[stock.symbol] || 100, // Use market cap for sizing
                change: stock.changePercent.toFixed(2)
            }));

            sectorChildren.push({
                name: subcategoryName,
                children: subcategoryChildren
            });
        }

        children.push({
            name: sectorName,
            children: sectorChildren
        });
    }

    return {
        name: "S&P 500",
        children: children
    };
}

// Fallback function with random data (same as before)
function generateFallbackData() {
    const r = () => (Math.random() * 6 - 3).toFixed(2);

    return {
        name: "S&P 500",
        children: [
            {
                name: "Technology",
                children: [
                    {
                        name: "Software - Infrastructure",
                        children: [
                            {name: "MSFT", value: 2800, change: r()},
                            {name: "ORCL", value: 350, change: r()},
                            {name: "PANW", value: 100, change: r()},
                            {name: "CRWD", value: 85, change: r()},
                            {name: "NOW", value: 120, change: r()},
                            {name: "SNOW", value: 45, change: r()}
                        ]
                    },
                    {
                        name: "Semiconductors",
                        children: [
                            {name: "NVDA", value: 1200, change: r()},
                            {name: "AVGO", value: 700, change: r()},
                            {name: "AMD", value: 240, change: r()},
                            {name: "QCOM", value: 195, change: r()},
                            {name: "MU", value: 115, change: r()},
                            {name: "AMAT", value: 145, change: r()},
                            {name: "LRCX", value: 95, change: r()},
                            {name: "KLAC", value: 75, change: r()}
                        ]
                    },
                    {
                        name: "Software - Application",
                        children: [
                            {name: "CRM", value: 280, change: r()},
                            {name: "ADBE", value: 250, change: r()},
                            {name: "INTU", value: 150, change: r()},
                            {name: "UBER", value: 145, change: r()},
                            {name: "WDAY", value: 65, change: r()},
                            {name: "TEAM", value: 55, change: r()}
                        ]
                    },
                    {
                        name: "Consumer Electronics",
                        children: [
                            {name: "AAPL", value: 3000, change: r()},
                            {name: "SMCI", value: 25, change: r()}
                        ]
                    },
                    {
                        name: "Hardware",
                        children: [
                            {name: "HPQ", value: 35, change: r()},
                            {name: "DELL", value: 85, change: r()},
                            {name: "NTAP", value: 25, change: r()}
                        ]
                    }
                ]
            },
            {
                name: "Financials",
                children: [
                    {
                        name: "Banks - Diversified",
                        children: [
                            {name: "JPM", value: 580, change: r()},
                            {name: "BAC", value: 320, change: r()},
                            {name: "WFC", value: 195, change: r()},
                            {name: "C", value: 125, change: r()}
                        ]
                    },
                    {
                        name: "Credit Services",
                        children: [
                            {name: "V", value: 550, change: r()},
                            {name: "MA", value: 420, change: r()},
                            {name: "AXP", value: 175, change: r()}
                        ]
                    },
                    {
                        name: "Capital Markets",
                        children: [
                            {name: "MS", value: 160, change: r()},
                            {name: "GS", value: 145, change: r()},
                            {name: "SCHW", value: 130, change: r()},
                            {name: "SPGI", value: 145, change: r()},
                            {name: "BLK", value: 135, change: r()}
                        ]
                    }
                ]
            },
            // Additional sectors...
            {
                name: "Healthcare",
                children: [
                    {
                        name: "Drug Manufacturers - General",
                        children: [
                            {name: "LLY", value: 750, change: r()},
                            {name: "JNJ", value: 380, change: r()},
                            {name: "ABBV", value: 320, change: r()},
                            {name: "MRK", value: 280, change: r()}
                        ]
                    }
                ]
            },
            {
                name: "Communication",
                children: [
                    {
                        name: "Internet Content & Information",
                        children: [
                            {name: "GOOGL", value: 1950, change: r()},
                            {name: "META", value: 1300, change: r()},
                            {name: "NFLX", value: 280, change: r()}
                        ]
                    }
                ]
            }
        ]
    };
}
