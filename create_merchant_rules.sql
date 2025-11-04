-- Tabuľka pre učiace sa pravidlá kategorizácie
CREATE TABLE IF NOT EXISTS MerchantRules (
    RuleID INTEGER PRIMARY KEY AUTOINCREMENT,
    MerchantPattern TEXT NOT NULL,
    CategoryID INTEGER NOT NULL,
    MatchType TEXT DEFAULT 'contains' CHECK(MatchType IN ('exact', 'contains', 'starts_with')),
    Confidence REAL DEFAULT 1.0,
    LearnedFrom TEXT DEFAULT 'Manual' CHECK(LearnedFrom IN ('Manual', 'AI', 'System')),
    UsageCount INTEGER DEFAULT 0,
    LastUsed DATETIME,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID) ON DELETE CASCADE
);

-- Index pre rýchle vyhľadávanie
CREATE INDEX IF NOT EXISTS idx_merchant_pattern ON MerchantRules(MerchantPattern);
CREATE INDEX IF NOT EXISTS idx_category_id ON MerchantRules(CategoryID);

-- Trigger pre update timestamp
CREATE TRIGGER IF NOT EXISTS update_merchant_rules_timestamp 
AFTER UPDATE ON MerchantRules
BEGIN
    UPDATE MerchantRules SET UpdatedAt = CURRENT_TIMESTAMP WHERE RuleID = NEW.RuleID;
END;
