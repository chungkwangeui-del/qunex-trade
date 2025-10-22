// Finviz-style comprehensive stock data with subcategories
// This mimics the real Finviz sector map structure

function generateFinvizData() {
    const r = () => (Math.random() * 6 - 3).toFixed(2); // Random change -3% to +3%

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
                            {name: "PLTR", value: 45, change: r()},
                            {name: "SNPS", value: 78, change: r()},
                            {name: "XYZ", value: 25, change: r()},
                            {name: "FTNT", value: 35, change: r()}
                        ]
                    },
                    {
                        name: "Consumer Electronics",
                        children: [
                            {name: "AAPL", value: 3000, change: r()}
                        ]
                    },
                    {
                        name: "Semiconductors",
                        children: [
                            {name: "NVDA", value: 1200, change: r()},
                            {name: "AVGO", value: 700, change: r()},
                            {name: "AMD", value: 240, change: r()},
                            {name: "QCOM", value: 195, change: r()},
                            {name: "TXN", value: 165, change: r()},
                            {name: "INTC", value: 180, change: r()},
                            {name: "NXPI", value: 60, change: r()},
                            {name: "AMAT", value: 145, change: r()},
                            {name: "LRCX", value: 95, change: r()},
                            {name: "ADI", value: 95, change: r()},
                            {name: "MU", value: 115, change: r()},
                            {name: "KLAC", value: 75, change: r()}
                        ]
                    },
                    {
                        name: "Software - Application",
                        children: [
                            {name: "CRM", value: 280, change: r()},
                            {name: "NOW", value: 145, change: r()},
                            {name: "ADBE", value: 250, change: r()},
                            {name: "INTU", value: 140, change: r()},
                            {name: "IBM", value: 180, change: r()},
                            {name: "UBER", value: 125, change: r()},
                            {name: "ADP", value: 110, change: r()},
                            {name: "ROP", value: 55, change: r()},
                            {name: "FIS", value: 48, change: r()},
                            {name: "BR", value: 30, change: r()}
                        ]
                    },
                    {
                        name: "Semiconductor Equipment",
                        children: [
                            {name: "ANET", value: 85, change: r()}
                        ]
                    },
                    {
                        name: "Computer Hardware",
                        children: [
                            {name: "CSCO", value: 215, change: r()},
                            {name: "MSI", value: 62, change: r()},
                            {name: "CDNS", value: 75, change: r()},
                            {name: "ADSK", value: 65, change: r()}
                        ]
                    },
                    {
                        name: "Electronics",
                        children: [
                            {name: "APH", value: 68, change: r()},
                            {name: "GLW", value: 28, change: r()},
                            {name: "TEL", value: 145, change: r()}
                        ]
                    },
                    {
                        name: "Scientific & Technical",
                        children: [
                            {name: "SCIENTI", value: 22, change: r()}
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
                            {name: "META", value: 1300, change: r()}
                        ]
                    },
                    {
                        name: "Entertainment",
                        children: [
                            {name: "NFLX", value: 280, change: r()},
                            {name: "DIS", value: 200, change: r()},
                            {name: "LYV", value: 28, change: r()},
                            {name: "TKO", value: 18, change: r()}
                        ]
                    },
                    {
                        name: "Telecom Services",
                        children: [
                            {name: "TMUS", value: 185, change: r()},
                            {name: "VZ", value: 175, change: r()},
                            {name: "T", value: 145, change: r()}
                        ]
                    },
                    {
                        name: "Advertising",
                        children: [
                            {name: "APP", value: 12, change: r()},
                            {name: "EA", value: 38, change: r()}
                        ]
                    }
                ]
            },
            {
                name: "Consumer Cyclical",
                children: [
                    {
                        name: "Internet Retail",
                        children: [
                            {name: "AMZN", value: 1900, change: r()},
                            {name: "DASH", value: 42, change: r()},
                            {name: "EBAY", value: 28, change: r()},
                            {name: "GM", value: 55, change: r()},
                            {name: "F", value: 48, change: r()}
                        ]
                    },
                    {
                        name: "Auto Manufacturers",
                        children: [
                            {name: "TSLA", value: 800, change: r()}
                        ]
                    },
                    {
                        name: "Home Improvement",
                        children: [
                            {name: "HD", value: 380, change: r()},
                            {name: "BKNG", value: 125, change: r()}
                        ]
                    },
                    {
                        name: "Travel Services",
                        children: [
                            {name: "RCL", value: 35, change: r()}
                        ]
                    },
                    {
                        name: "Auto Parts",
                        children: [
                            {name: "AUTO PA", value: 15, change: r()}
                        ]
                    },
                    {
                        name: "Lodging",
                        children: [
                            {name: "MAR", value: 68, change: r()},
                            {name: "LODG", value: 12, change: r()},
                            {name: "IP", value: 8, change: r()}
                        ]
                    },
                    {name: "Footwear",
                     children: [
                         {name: "NKE", value: 180, change: r()},
                         {name: "FOOT", value: 8, change: r()},
                         {name: "LVS", value: 42, change: r()}
                     ]
                    },
                    {
                        name: "Restaurants",
                        children: [
                            {name: "MCD", value: 210, change: r()},
                            {name: "CMG", value: 88, change: r()},
                            {name: "SBUX", value: 105, change: r()},
                            {name: "YUM", value: 38, change: r()},
                            {name: "DPH", value: 15, change: r()}
                        ]
                    },
                    {
                        name: "Apparel Retail",
                        children: [
                            {name: "ABNB", value: 95, change: r()},
                            {name: "TJX", value: 115, change: r()}
                        ]
                    }
                ]
            },
            {
                name: "Consumer Defensive",
                children: [
                    {
                        name: "Discount Stores",
                        children: [
                            {name: "WMT", value: 550, change: r()},
                            {name: "COST", value: 385, change: r()}
                        ]
                    },
                    {
                        name: "Household & Personal Products",
                        children: [
                            {name: "PG", value: 390, change: r()},
                            {name: "CL", value: 72, change: r()}
                        ]
                    },
                    {
                        name: "Tobacco",
                        children: [
                            {name: "PM", value: 165, change: r()},
                            {name: "MO", value: 95, change: r()}
                        ]
                    },
                    {
                        name: "Beverages - Non-Alcoholic",
                        children: [
                            {name: "KO", value: 280, change: r()},
                            {name: "PEP", value: 230, change: r()},
                            {name: "DG", value: 35, change: r()}
                        ]
                    },
                    {
                        name: "Packaged Foods",
                        children: [
                            {name: "PACKA", value: 22, change: r()},
                            {name: "K", value: 25, change: r()},
                            {name: "CONFEC", value: 15, change: r()},
                            {name: "KR", value: 42, change: r()}
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
                            {name: "WFC", value: 210, change: r()},
                            {name: "C", value: 120, change: r()},
                            {name: "BK", value: 52, change: r()}
                        ]
                    },
                    {
                        name: "Credit Services",
                        children: [
                            {name: "V", value: 550, change: r()},
                            {name: "MA", value: 420, change: r()},
                            {name: "AXP", value: 175, change: r()},
                            {name: "COF", value: 58, change: r()},
                            {name: "SYF", value: 42, change: r()}
                        ]
                    },
                    {
                        name: "Insurance - Diversified",
                        children: [
                            {name: "BRK-B", value: 900, change: r()}
                        ]
                    },
                    {
                        name: "Capital Markets",
                        children: [
                            {name: "MS", value: 155, change: r()},
                            {name: "GS", value: 145, change: r()},
                            {name: "SCHW", value: 125, change: r()},
                            {name: "HOOD", value: 22, change: r()}
                        ]
                    },
                    {
                        name: "Asset Management",
                        children: [
                            {name: "BX", value: 135, change: r()},
                            {name: "KKR", value: 95, change: r()},
                            {name: "APO", value: 65, change: r()},
                            {name: "CB", value: 95, change: r()},
                            {name: "PGR", value: 78, change: r()},
                            {name: "ALL", value: 48, change: r()},
                            {name: "TRV", value: 52, change: r()}
                        ]
                    },
                    {
                        name: "Insurance - Property",
                        children: [
                            {name: "L", value: 28, change: r()}
                        ]
                    },
                    {
                        name: "Banks",
                        children: [
                            {name: "USB", value: 68, change: r()},
                            {name: "PNC", value: 72, change: r()},
                            {name: "TFC", value: 55, change: r()}
                        ]
                    },
                    {
                        name: "Insurance - Life",
                        children: [
                            {name: "MMC", value: 85, change: r()},
                            {name: "INSUR", value: 18, change: r()}
                        ]
                    },
                    {
                        name: "Financial Data",
                        children: [
                            {name: "SPGI", value: 125, change: r()},
                            {name: "ICE", value: 78, change: r()},
                            {name: "COIN", value: 48, change: r()},
                            {name: "RF", value: 22, change: r()},
                            {name: "CME", value: 85, change: r()},
                            {name: "MSCI", value: 52, change: r()}
                        ]
                    },
                    {
                        name: "Insurance - Unknown",
                        children: [
                            {name: "AIG", value: 55, change: r()}
                        ]
                    }
                ]
            },
            {
                name: "Healthcare",
                children: [
                    {
                        name: "Drug Manufacturers - General",
                        children: [
                            {name: "LLY", value: 750, change: r()},
                            {name: "JNJ", value: 380, change: r()},
                            {name: "MRK", value: 280, change: r()},
                            {name: "ABBV", value: 320, change: r()},
                            {name: "GILD", value: 105, change: r()},
                            {name: "AMGN", value: 145, change: r()},
                            {name: "BMY", value: 115, change: r()}
                        ]
                    },
                    {
                        name: "Medical Devices",
                        children: [
                            {name: "ABT", value: 210, change: r()},
                            {name: "SYK", value: 115, change: r()},
                            {name: "MDT", value: 108, change: r()},
                            {name: "BSX", value: 85, change: r()},
                            {name: "EW", value: 58, change: r()}
                        ]
                    },
                    {
                        name: "Healthcare Plans",
                        children: [
                            {name: "UNH", value: 500, change: r()},
                            {name: "CVS", value: 88, change: r()},
                            {name: "CI", value: 92, change: r()},
                            {name: "ELV", value: 125, change: r()}
                        ]
                    },
                    {
                        name: "Diagnostics & Research",
                        children: [
                            {name: "TMO", value: 210, change: r()},
                            {name: "DHR", value: 195, change: r()}
                        ]
                    },
                    {
                        name: "Medical Instruments",
                        children: [
                            {name: "ISRG", value: 145, change: r()},
                            {name: "BDX", value: 68, change: r()},
                            {name: "MCK", value: 78, change: r()}
                        ]
                    },
                    {
                        name: "Biotechnology",
                        children: [
                            {name: "BIOTEC", value: 25, change: r()},
                            {name: "HCA", value: 78, change: r()}
                        ]
                    }
                ]
            },
            {
                name: "Industrials",
                children: [
                    {
                        name: "Aerospace & Defense",
                        children: [
                            {name: "GE", value: 180, change: r()},
                            {name: "RTX", value: 150, change: r()},
                            {name: "BA", value: 125, change: r()},
                            {name: "LMT", value: 115, change: r()},
                            {name: "NOC", value: 78, change: r()},
                            {name: "GD", value: 68, change: r()}
                        ]
                    },
                    {
                        name: "Farm & Heavy Equipment",
                        children: [
                            {name: "CAT", value: 170, change: r()},
                            {name: "DE", value: 125, change: r()},
                            {name: "PCAR", value: 42, change: r()}
                        ]
                    },
                    {
                        name: "Railroads",
                        children: [
                            {name: "UNP", value: 145, change: r()},
                            {name: "NSC", value: 58, change: r()},
                            {name: "CSX", value: 72, change: r()}
                        ]
                    },
                    {
                        name: "Building Materials",
                        children: [
                            {name: "BUILDI", value: 35, change: r()},
                            {name: "TT", value: 28, change: r()}
                        ]
                    },
                    {
                        name: "Industrial Products",
                        children: [
                            {name: "INTEGR", value: 22, change: r()},
                            {name: "FDX", value: 78, change: r()},
                            {name: "WM", value: 88, change: r()}
                        ]
                    },
                    {
                        name: "Waste Management",
                        children: [
                            {name: "WASTE", value: 22, change: r()},
                            {name: "DAL", value: 32, change: r()}
                        ]
                    },
                    {
                        name: "Specialty Industrial M",
                        children: [
                            {name: "GEV", value: 28, change: r()},
                            {name: "PH", value: 65, change: r()},
                            {name: "EMR", value: 58, change: r()},
                            {name: "CMI", value: 42, change: r()}
                        ]
                    },
                    {
                        name: "Engineering",
                        children: [
                            {name: "JCI", value: 68, change: r()},
                            {name: "ETN", value: 95, change: r()},
                            {name: "ITW", value: 75, change: r()},
                            {name: "IR", value: 58, change: r()}
                        ]
                    },
                    {
                        name: "Conglomerates",
                        children: [
                            {name: "CONG", value: 22, change: r()},
                            {name: "HON", value: 145, change: r()},
                            {name: "MMM", value: 68, change: r()}
                        ]
                    },
                    {
                        name: "Misc",
                        children: [
                            {name: "CTAS", value: 85, change: r()},
                            {name: "PWR", value: 42, change: r()},
                            {name: "J", value: 28, change: r()},
                            {name: "CPRT", value: 55, change: r()}
                        ]
                    },
                    {
                        name: "Integrated Freight",
                        children: [
                            {name: "UPS", value: 120, change: r()},
                            {name: "AXON", value: 68, change: r()},
                            {name: "TDG", value: 92, change: r()}
                        ]
                    },
                    {
                        name: "Utilities",
                        children: [
                            {name: "URI", value: 48, change: r()},
                            {name: "FAST", value: 32, change: r()}
                        ]
                    }
                ]
            },
            {
                name: "Energy",
                children: [
                    {
                        name: "Oil & Gas I&P",
                        children: [
                            {name: "XOM", value: 480, change: r()},
                            {name: "CVX", value: 280, change: r()}
                        ]
                    },
                    {
                        name: "Oil & Gas E&P",
                        children: [
                            {name: "COP", value: 140, change: r()},
                            {name: "EOG", value: 72, change: r()}
                        ]
                    },
                    {
                        name: "Oil & Gas",
                        children: [
                            {name: "OKE", value: 35, change: r()}
                        ]
                    }
                ]
            },
            {
                name: "Materials",
                children: [
                    {
                        name: "Specialty Chemicals",
                        children: [
                            {name: "LIN", value: 210, change: r()},
                            {name: "APD", value: 70, change: r()},
                            {name: "ECL", value: 60, change: r()}
                        ]
                    },
                    {
                        name: "Basic Materials",
                        children: [
                            {name: "NEM", value: 45, change: r()},
                            {name: "FCX", value: 52, change: r()}
                        ]
                    }
                ]
            },
            {
                name: "Real Estate",
                children: [
                    {
                        name: "REIT - Specialty",
                        children: [
                            {name: "PLD", value: 120, change: r()},
                            {name: "AMT", value: 100, change: r()},
                            {name: "CCI", value: 70, change: r()},
                            {name: "DLR", value: 42, change: r()}
                        ]
                    },
                    {
                        name: "REIT - Industrial",
                        children: [
                            {name: "PSA", value: 52, change: r()}
                        ]
                    },
                    {
                        name: "REIT - Healthcare",
                        children: [
                            {name: "WELL", value: 35, change: r()}
                        ]
                    },
                    {
                        name: "REIT - Retail",
                        children: [
                            {name: "O", value: 28, change: r()}
                        ]
                    }
                ]
            },
            {
                name: "Utilities",
                children: [
                    {
                        name: "Utilities - Regulated",
                        children: [
                            {name: "NEE", value: 150, change: r()},
                            {name: "DUK", value: 80, change: r()},
                            {name: "SO", value: 90, change: r()},
                            {name: "XEL", value: 38, change: r()},
                            {name: "EXC", value: 42, change: r()}
                        ]
                    },
                    {
                        name: "Utilities",
                        children: [
                            {name: "AEP", value: 48, change: r()},
                            {name: "D", value: 42, change: r()},
                            {name: "AEE", value: 22, change: r()}
                        ]
                    },
                    {
                        name: "Utilities - Independent",
                        children: [
                            {name: "VST", value: 38, change: r()},
                            {name: "CEG", value: 52, change: r()},
                            {name: "SRE", value: 45, change: r()},
                            {name: "ETR", value: 28, change: r()},
                            {name: "ES", value: 22, change: r()},
                            {name: "ED", value: 28, change: r()}
                        ]
                    }
                ]
            }
        ]
    };
}
