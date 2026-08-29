-- NarrateBI SQLite Database Schema
-- Version 2.0 — Realistic multi-dimensional time-series schema

DROP TABLE IF EXISTS kpi_values;
DROP TABLE IF EXISTS sales_data;
DROP TABLE IF EXISTS payment_data;
DROP TABLE IF EXISTS web_data;
DROP TABLE IF EXISTS system_logs;
DROP TABLE IF EXISTS deployment_events;
DROP TABLE IF EXISTS marketing_data;
DROP TABLE IF EXISTS feedback;

-- 1. Aggregated KPI Values table (computed from time-series; not pre-baked outcomes)
--    current_value  = aggregate over the "analysis period" (e.g. last 7 days)
--    baseline_value = aggregate over the prior comparable period (e.g. prev 7 days)
CREATE TABLE kpi_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id TEXT NOT NULL DEFAULT 'default',
    kpi_key TEXT NOT NULL,
    current_value REAL NOT NULL,
    baseline_value REAL NOT NULL,
    change_pct REAL NOT NULL,
    unit TEXT,
    history_days INTEGER NOT NULL DEFAULT 30,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. Source 1: ERP / Sales Transactions  (daily grain × product × region × channel)
CREATE TABLE sales_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id TEXT NOT NULL DEFAULT 'default',
    date DATE NOT NULL,              -- YYYY-MM-DD
    product TEXT NOT NULL,           -- 'Electronics','Apparel','Home & Kitchen','Beauty','Sports'
    category TEXT NOT NULL,          -- product category grouping
    region TEXT NOT NULL,            -- 'North','South','East','West','Metro'
    channel TEXT NOT NULL,           -- 'Web','Mobile App','Marketplace','In-Store'
    customer_segment TEXT NOT NULL,  -- 'New','Returning','Premium','Enterprise'
    sessions INTEGER NOT NULL DEFAULT 0,
    orders INTEGER NOT NULL DEFAULT 0,
    units INTEGER NOT NULL DEFAULT 0,
    revenue REAL NOT NULL DEFAULT 0.0,
    aov REAL NOT NULL DEFAULT 0.0,
    conversion_rate REAL NOT NULL DEFAULT 0.0,  -- as percentage, e.g. 4.5 means 4.5%
    discount_rate REAL NOT NULL DEFAULT 0.0,     -- average discount % applied
    returns INTEGER NOT NULL DEFAULT 0,
    marketing_spend REAL NOT NULL DEFAULT 0.0
);

-- 3. Source 2: Payment & Checkout telemetry  (hourly grain)
CREATE TABLE payment_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id TEXT NOT NULL DEFAULT 'default',
    timestamp DATETIME NOT NULL,     -- YYYY-MM-DD HH:MM:SS
    region TEXT NOT NULL DEFAULT 'All',
    sessions INTEGER NOT NULL,
    orders INTEGER NOT NULL,
    conversion_rate REAL NOT NULL,
    payment_success INTEGER NOT NULL,
    payment_failures INTEGER NOT NULL,
    checkout_errors INTEGER NOT NULL,
    avg_checkout_latency_ms INTEGER NOT NULL DEFAULT 800
);

-- 4. Source 2 (Web / Mobile analytics — daily grain by device)
CREATE TABLE web_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id TEXT NOT NULL DEFAULT 'default',
    date DATE NOT NULL,
    device TEXT NOT NULL,            -- 'Desktop','Mobile','Tablet'
    channel TEXT NOT NULL DEFAULT 'Organic',
    sessions INTEGER NOT NULL,
    bounce_rate REAL,
    avg_session_duration_sec INTEGER DEFAULT 180
);

-- 5. Source 3: System / Application Logs  (event level)
CREATE TABLE system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id TEXT NOT NULL DEFAULT 'default',
    timestamp DATETIME NOT NULL,
    service TEXT NOT NULL,
    log_level TEXT NOT NULL,         -- 'DEBUG','INFO','WARN','ERROR','FATAL'
    message TEXT NOT NULL
);

-- 6. Source 3: Deployment & Release Events
CREATE TABLE deployment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id TEXT NOT NULL DEFAULT 'default',
    timestamp DATETIME NOT NULL,
    service TEXT NOT NULL,
    version TEXT NOT NULL,
    status TEXT NOT NULL,            -- 'started','completed','rolled_back','failed'
    deployed_by TEXT,
    environment TEXT DEFAULT 'production'
);

-- 7. Source 4: Marketing Campaigns  (daily grain × campaign × region)
CREATE TABLE marketing_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id TEXT NOT NULL DEFAULT 'default',
    date DATE NOT NULL,
    campaign TEXT NOT NULL,          -- campaign name
    channel TEXT NOT NULL,           -- 'Paid Search','Social','Email','Display','Affiliate'
    region TEXT NOT NULL DEFAULT 'All',
    spend REAL NOT NULL DEFAULT 0.0,
    impressions INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    attributed_orders INTEGER NOT NULL DEFAULT 0,
    attributed_revenue REAL NOT NULL DEFAULT 0.0,
    roas REAL NOT NULL DEFAULT 0.0   -- Return on Ad Spend = attributed_revenue / spend
);

-- 8. Diagnostic User Feedback
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id TEXT NOT NULL,
    kpi_key TEXT NOT NULL,
    rating TEXT NOT NULL CHECK(rating IN ('up', 'down')),
    persona TEXT NOT NULL,
    comment TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast scenario querying
CREATE INDEX idx_kpi_scenario ON kpi_values(scenario_id, kpi_key);
CREATE INDEX idx_sales_scenario_date ON sales_data(scenario_id, date);
CREATE INDEX idx_sales_region ON sales_data(scenario_id, region, date);
CREATE INDEX idx_payment_scenario ON payment_data(scenario_id, timestamp);
CREATE INDEX idx_web_scenario_date ON web_data(scenario_id, date);
CREATE INDEX idx_logs_scenario ON system_logs(scenario_id, timestamp);
CREATE INDEX idx_deployments_scenario ON deployment_events(scenario_id, timestamp);
CREATE INDEX idx_marketing_scenario_date ON marketing_data(scenario_id, date);
