ALTER TABLE messages
    ADD COLUMN model VARCHAR(100) NULL AFTER token_usage;
