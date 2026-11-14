// Price & break-even chart (TradingView Lightweight Charts, vendored in /static/vendor)
//
// Draws the daily BTC close plus today's live price, the user's break-even price as
// a step line that moves at each trade, and a marker per trade. Colours come from
// the style guide tokens in style.css.

const PriceChart = (() => {
    const RANGE_DAYS = { '1M': 30, '3M': 90, '1Y': 365, '3Y': 1095, '5Y': 1825, 'ALL': null };

    let chart = null;
    let priceSeries = null;
    let breakEvenSeries = null;
    let markersApi = null;

    let closes = [];          // [{date, close}] from /api/bitcoin/history
    let trades = [];          // from /api/trades, newest first
    let livePrice = null;
    let range = '1Y';
    let rangeFrom = null;
    let showTrades = true;

    let priceData = [];
    let breakEvenData = [];
    let markers = [];         // [{time, side, ...lightweight-charts marker}]

    const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    const todayUtc = () => new Date().toISOString().slice(0, 10);

    function shiftDate(isoDate, days) {
        const d = new Date(`${isoDate}T00:00:00Z`);
        d.setUTCDate(d.getUTCDate() + days);
        return d.toISOString().slice(0, 10);
    }

    function create() {
        const { createChart, createSeriesMarkers, LineSeries, LineType, LineStyle } = LightweightCharts;
        chart = createChart(document.getElementById('price-chart'), {
            autoSize: true,
            layout: {
                background: { type: 'solid', color: 'transparent' },
                textColor: css('--text-3'),
                fontFamily: css('--font'),
                fontSize: 12,
                attributionLogo: true,  // links to tradingview.com, as the library's licence asks
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
            },
            rightPriceScale: { borderColor: 'rgba(255, 255, 255, 0.1)' },
            timeScale: { borderColor: 'rgba(255, 255, 255, 0.1)' },
            localization: { priceFormatter: value => formatCurrency(value) },
        });
        priceSeries = chart.addSeries(LineSeries, {
            color: css('--amber'),
            lineWidth: 2,
            priceLineVisible: false,
        });
        breakEvenSeries = chart.addSeries(LineSeries, {
            color: css('--s1'),
            lineWidth: 2,
            lineStyle: LineStyle.Dashed,
            lineType: LineType.WithSteps,
            priceLineVisible: false,
            crosshairMarkerVisible: false,
        });
        markersApi = createSeriesMarkers(priceSeries, []);
    }

    // ---------- Data ----------

    function buildPriceData() {
        priceData = closes.map(c => ({ time: c.date, value: Number(c.close) }));
        const today = todayUtc();
        const last = priceData.length ? priceData[priceData.length - 1].time : null;
        if (livePrice !== null && last && last < today) {
            priceData.push({ time: today, value: livePrice });
        }
    }

    // One point per trade day (the break-even after that day's last trade), held until
    // the next trade and extended to the latest price. A negative break-even ("Free")
    // leaves a gap instead of stretching the price axis below zero.
    function buildBreakEvenData() {
        const byDay = new Map();
        [...trades].reverse().forEach(t => byDay.set(t.date, t.break_even === null ? null : Number(t.break_even)));
        breakEvenData = [...byDay.entries()]
            .sort(([a], [b]) => (a < b ? -1 : 1))
            .map(([time, value]) => (value === null || value < 0 ? { time } : { time, value }));

        const lastPoint = breakEvenData[breakEvenData.length - 1];
        const lastPrice = priceData[priceData.length - 1];
        if (lastPoint && lastPoint.value !== undefined && lastPrice && lastPrice.time > lastPoint.time) {
            breakEvenData.push({ time: lastPrice.time, value: lastPoint.value });
        }
    }

    function buildMarkers() {
        const days = new Set(priceData.map(p => p.time));
        const style = {
            buy: { position: 'belowBar', shape: 'arrowUp', color: css('--profit') },
            sell: { position: 'aboveBar', shape: 'arrowDown', color: css('--loss') },
            reward: { position: 'inBar', shape: 'circle', color: css('--s4') },
        };
        markers = [...trades].reverse()
            .filter(t => days.has(t.date))
            .map(t => ({ time: t.date, side: t.side, ...style[t.side] }));
    }

    function draw() {
        if (!chart) return;
        buildPriceData();
        buildBreakEvenData();
        buildMarkers();
        priceSeries.setData(priceData);
        breakEvenSeries.setData(breakEvenData);
        markersApi.setMarkers(showTrades ? markers.map(({ side, ...marker }) => marker) : []);
        applyRange();
    }

    function applyRange() {
        if (!chart || !priceData.length) return;
        const days = RANGE_DAYS[range];
        const lastDate = priceData[priceData.length - 1].time;
        if (days === null) {
            rangeFrom = null;
            chart.timeScale().fitContent();
        } else {
            rangeFrom = shiftDate(lastDate, -days);
            chart.timeScale().setVisibleRange({ from: rangeFrom, to: lastDate });
        }
        document.querySelectorAll('[data-range]').forEach(button => {
            const active = button.dataset.range === range;
            button.classList.toggle('active', active);
            button.setAttribute('aria-pressed', active);
        });
    }

    // ---------- Public API ----------

    async function init(onHistory) {
        document.querySelectorAll('[data-range]').forEach(button => {
            button.addEventListener('click', () => {
                range = button.dataset.range;
                applyRange();
            });
        });
        document.getElementById('show-trades').addEventListener('change', e => {
            showTrades = e.target.checked;
            draw();
        });

        const result = await apiRequest('/api/bitcoin/history');
        const history = result.ok && result.data.success ? result.data : null;
        closes = history ? history.closes : [];
        if (onHistory) onHistory(history);

        const available = closes.length > 0 && window.LightweightCharts;
        document.getElementById('price-chart').classList.toggle('hidden', !available);
        document.querySelector('.chart-legend').classList.toggle('hidden', !available);
        document.getElementById('chart-empty').classList.toggle('hidden', Boolean(available));
        if (!available) return;

        create();
        draw();
    }

    function setTrades(newTrades) {
        trades = newTrades;
        draw();
    }

    function setLivePrice(price) {
        livePrice = price;
        draw();
    }

    // Read-only summary of what is drawn (used by the browser tests)
    function state() {
        const last = priceData[priceData.length - 1];
        return {
            points: priceData.length,
            lastDate: last ? last.time : null,
            lastPrice: last ? last.value : null,
            breakEven: breakEvenData.filter(p => p.value !== undefined),
            markers: showTrades ? markers.map(m => ({ time: m.time, side: m.side })) : [],
            range,
            rangeFrom,
        };
    }

    return { init, setTrades, setLivePrice, state };
})();
