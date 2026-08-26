-- NarrateBI SQLite Database Schema

DROP TABLE IF EXISTS kpi_values;
DROP TABLE IF EXISTS sales_data;
DROP TABLE IF EXISTS payment_data;
DROP TABLE IF EXISTS web_data;
DROP TABLE IF EXISTS system_logs;
DROP TABLE IF EXISTS deployment_events;
DROP TABLE IF EXISTS feedback;

-- 1. Aggregated KPI Values table
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

-- 2. Source 1: ERP / Sales Transactions
CREATE TABLE sales_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id TEXT NOT NULL DEFAULT 'default',
    timestamp DATETIME NOT NULL,
    orders INTEGER NOT NULL,
    revenue REAL NOT NULL,
    aov REAL NOT NULL,
    cogs REAL
);

-- 3. Source 2: Website / Payments
CREATE TABLE payment_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id TEXT NOT NULL DEFAULT 'default',
    timestamp DATETIME NOT NULL,
    sessions INTEGER NOT NULL,
    orders INTEGER NOT NULL,
    conversion_rate REAL NOT NULL,
    payment_success INTEGER NOT NULL,
    payment_failures INTEGER NOT NULL,
    checkout_errors INTEGER NOT NULL
);

-- 4. Source 2 (Web analytics detail)
CREATE TABLE web_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id TEXT NOT NULL DEFAULT 'default',
    timestamp DATETIME NOT NULL,
    sessions INTEGER NOT NULL,
    bounce_rate REAL,
    device TEXT
);

-- 5. Source 3: Operations & System Logs
CREATE TABLE system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id TEXT NOT NULL DEFAULT 'default',
    timestamp DATETIME NOT NULL,
    service TEXT NOT NULL,
    log_level TEXT NOT NULL,
    message TEXT NOT NULL
);

-- 6. Source 3: Deployment Events
CREATE TABLE deployment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id TEXT NOT NULL DEFAULT 'default',
    timestamp DATETIME NOT NULL,
    service TEXT NOT NULL,
    version TEXT NOT NULL,
    status TEXT NOT NULL,
    deployed_by TEXT
);

-- 7. Diagnostic User Feedback
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
CREATE INDEX idx_sales_scenario ON sales_data(scenario_id, timestamp);
CREATE INDEX idx_payment_scenario ON payment_data(scenario_id, timestamp);
CREATE INDEX idx_logs_scenario ON system_logs(scenario_id, timestamp);
CREATE INDEX idx_deployments_scenario ON deployment_events(scenario_id, timestamp);
