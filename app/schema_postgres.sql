CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  email TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS newsletter_subscription (
  id SERIAL PRIMARY KEY,
  user_id INTEGER,
  email TEXT UNIQUE NOT NULL,
  subscribed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  is_active INTEGER NOT NULL DEFAULT 1,
  FOREIGN KEY (user_id) REFERENCES users (id)
);

-- One row per BTC movement. Amounts are TEXT so they keep exact decimal values.
CREATE TABLE IF NOT EXISTS trades (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  side TEXT NOT NULL,                       -- buy | sell | reward
  trade_date TIMESTAMP NOT NULL,
  btc_amount TEXT NOT NULL,
  fiat_amount TEXT NOT NULL,
  fee_amount TEXT NOT NULL DEFAULT '0',
  fee_asset TEXT NOT NULL,                  -- BTC or the trade currency
  currency TEXT NOT NULL DEFAULT 'USD',
  source TEXT NOT NULL DEFAULT 'manual',    -- manual | kraken | coinbase
  import_id INTEGER,                        -- set by CSV import (Phase 5)
  trade_hash TEXT,                          -- duplicate detection for imports (Phase 5)
  notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_trades_user_hash ON trades (user_id, trade_hash);
CREATE INDEX IF NOT EXISTS idx_trades_user_date ON trades (user_id, trade_date);

-- One row per imported exchange file. Its trades point back here via trades.import_id.
CREATE TABLE IF NOT EXISTS imports (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  provider TEXT NOT NULL,                   -- kraken | coinbase
  filename TEXT NOT NULL,
  file_hash TEXT NOT NULL,                  -- SHA-256 of the file, to refuse the same file twice
  trade_count INTEGER NOT NULL,
  date_from TIMESTAMP,
  date_to TIMESTAMP,
  imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_imports_user_file ON imports (user_id, file_hash);
