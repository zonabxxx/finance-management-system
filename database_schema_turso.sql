-- Turso Database Schema (SQLite/LibSQL syntax)
-- Pre Finance Tracker aplikáciu

-- Tabuľka kategórií
CREATE TABLE IF NOT EXISTS Categories (
    CategoryID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    ParentCategoryID INTEGER NULL,
    Icon TEXT,
    Color TEXT,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ParentCategoryID) REFERENCES Categories(CategoryID)
);

-- Tabuľka obchodníkov/firiem
CREATE TABLE IF NOT EXISTS Merchants (
    MerchantID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    IBAN TEXT,
    AccountNumber TEXT,
    ICO TEXT,
    FinstatData TEXT, -- JSON z Finstat API
    DefaultCategoryID INTEGER,
    Website TEXT,
    Description TEXT,
    LastUpdated DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (DefaultCategoryID) REFERENCES Categories(CategoryID)
);

-- Tabuľka transakcií
CREATE TABLE IF NOT EXISTS Transactions (
    TransactionID INTEGER PRIMARY KEY AUTOINCREMENT,
    TransactionDate DATETIME NOT NULL,
    Amount REAL NOT NULL,
    Currency TEXT DEFAULT 'EUR',
    MerchantID INTEGER,
    MerchantName TEXT,
    AccountNumber TEXT,
    IBAN TEXT,
    CategoryID INTEGER,
    Description TEXT,
    VariableSymbol TEXT,
    ConstantSymbol TEXT,
    SpecificSymbol TEXT,
    TransactionType TEXT, -- 'Debit' alebo 'Credit'
    PaymentMethod TEXT, -- 'Card', 'Transfer', 'Cash', atď.
    CO2Footprint REAL, -- kg CO2e z B-mail
    IsRecurring INTEGER DEFAULT 0,
    Notes TEXT,
    RawEmailData TEXT, -- Pôvodný email pre debug
    AIConfidence REAL, -- Istota AI kategorizácie (0-100)
    CategorySource TEXT, -- 'Manual', 'AI', 'Rule', 'Finstat'
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (MerchantID) REFERENCES Merchants(MerchantID),
    FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID)
);

-- Tabuľka pre AI učenie sa
CREATE TABLE IF NOT EXISTS CategoryTraining (
    TrainingID INTEGER PRIMARY KEY AUTOINCREMENT,
    MerchantName TEXT,
    CategoryID INTEGER NOT NULL,
    UserCorrected INTEGER DEFAULT 0,
    OriginalAICategory INTEGER,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID),
    FOREIGN KEY (OriginalAICategory) REFERENCES Categories(CategoryID)
);

-- Tabuľka pre kategorizačné pravidlá
CREATE TABLE IF NOT EXISTS CategoryRules (
    RuleID INTEGER PRIMARY KEY AUTOINCREMENT,
    Pattern TEXT NOT NULL,
    CategoryID INTEGER NOT NULL,
    Priority INTEGER DEFAULT 0,
    IsActive INTEGER DEFAULT 1,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID)
);

-- Indexy pre výkon
CREATE INDEX IF NOT EXISTS idx_transactions_date ON Transactions(TransactionDate);
CREATE INDEX IF NOT EXISTS idx_transactions_merchant ON Transactions(MerchantID);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON Transactions(CategoryID);
CREATE INDEX IF NOT EXISTS idx_merchants_iban ON Merchants(IBAN);
CREATE INDEX IF NOT EXISTS idx_merchants_ico ON Merchants(ICO);

-- View pre prehľad výdavkov
CREATE VIEW IF NOT EXISTS vw_MonthlyExpenses AS
SELECT 
    CAST(strftime('%Y', TransactionDate) AS INTEGER) AS Year,
    CAST(strftime('%m', TransactionDate) AS INTEGER) AS Month,
    c.Name AS Category,
    COUNT(*) AS TransactionCount,
    SUM(Amount) AS TotalAmount,
    AVG(Amount) AS AvgAmount,
    SUM(CO2Footprint) AS TotalCO2
FROM Transactions t
LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
WHERE TransactionType = 'Debit'
GROUP BY strftime('%Y', TransactionDate), strftime('%m', TransactionDate), c.Name;

-- View pre top obchodníkov
CREATE VIEW IF NOT EXISTS vw_TopMerchants AS
SELECT 
    m.Name,
    c.Name AS Category,
    COUNT(*) AS TransactionCount,
    SUM(t.Amount) AS TotalSpent,
    MAX(t.TransactionDate) AS LastTransaction
FROM Transactions t
JOIN Merchants m ON t.MerchantID = m.MerchantID
LEFT JOIN Categories c ON m.DefaultCategoryID = c.CategoryID
WHERE t.TransactionType = 'Debit'
GROUP BY m.Name, c.Name;

-- Vloženie základných kategórií
INSERT OR IGNORE INTO Categories (CategoryID, Name, Icon, Color) VALUES
(1, 'Potraviny', '🛒', '#4CAF50'),
(2, 'Drogéria', '🧴', '#2196F3'),
(3, 'Reštaurácie a Kaviarne', '☕', '#FF9800'),
(4, 'Donáška jedla', '🍕', '#FF5722'),
(5, 'Doprava', '🚗', '#9C27B0'),
(6, 'Bývanie', '🏠', '#607D8B'),
(7, 'Zdravie', '⚕️', '#E91E63'),
(8, 'Zábava', '🎬', '#3F51B5'),
(9, 'Oblečenie', '👕', '#00BCD4'),
(10, 'Telefón a Internet', '📱', '#795548'),
(11, 'Vzdelávanie', '📚', '#009688'),
(12, 'Šport', '⚽', '#8BC34A'),
(13, 'Iné', '📦', '#9E9E9E');

