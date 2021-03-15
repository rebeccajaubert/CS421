CREATE INDEX IF NOT EXISTS items_prices
    ON items
    USING btree
    ( price );