-- Azure SQL Database Schema pre správu financií

-- Tabuľka kategórií
CREATE TABLE Categories (
    CategoryID INT PRIMARY KEY IDENTITY(1,1),
    Name NVARCHAR(100) NOT NULL,
    ParentCategoryID INT NULL,
    Icon NVARCHAR(50),
    Color NVARCHAR(7),
    CreatedAt DATETIME2 DEFAULT GETDATE(),
    FOREIGN KEY (ParentCategoryID) REFERENCES Categories(CategoryID)
);

-- Tabuľka obchodníkov/firiem
CREATE TABLE Merchants (
    MerchantID INT PRIMARY KEY IDENTITY(1,1),
    Name NVARCHAR(200) NOT NULL,
    IBAN NVARCHAR(34),
    AccountNumber NVARCHAR(50),
    ICO NVARCHAR(20),
    FinstatData NVARCHAR(MAX), -- JSON z Finstat API
    DefaultCategoryID INT,
    Website NVARCHAR(500),
    Description NVARCHAR(MAX),
    LastUpdated DATETIME2 DEFAULT GETDATE(),
    FOREIGN KEY (DefaultCategoryID) REFERENCES Categories(CategoryID)
);

-- Tabuľka transakcií
CREATE TABLE Transactions (
    TransactionID INT PRIMARY KEY IDENTITY(1,1),
    TransactionDate DATETIME2 NOT NULL,
    Amount DECIMAL(18,2) NOT NULL,
    Currency NVARCHAR(3) DEFAULT 'EUR',
    MerchantID INT,
    MerchantName NVARCHAR(200),
    AccountNumber NVARCHAR(50),
    IBAN NVARCHAR(34),
    CategoryID INT,
    Description NVARCHAR(MAX),
    VariableSymbol NVARCHAR(20),
    ConstantSymbol NVARCHAR(20),
    SpecificSymbol NVARCHAR(20),
    TransactionType NVARCHAR(20), -- 'Debit' alebo 'Credit'
    PaymentMethod NVARCHAR(50), -- 'Card', 'Transfer', 'Cash', atď.
    CO2Footprint DECIMAL(10,2), -- kg CO2e z B-mail
    IsRecurring BIT DEFAULT 0,
    Notes NVARCHAR(MAX),
    RawEmailData NVARCHAR(MAX), -- Pôvodný email pre debug
    AIConfidence DECIMAL(5,2), -- Istota AI kategorizácie (0-100)
    CategorySource NVARCHAR(50), -- 'Manual', 'AI', 'Rule', 'Finstat'
    CreatedAt DATETIME2 DEFAULT GETDATE(),
    UpdatedAt DATETIME2 DEFAULT GETDATE(),
    FOREIGN KEY (MerchantID) REFERENCES Merchants(MerchantID),
    FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID)
);

-- Tabuľka pre AI učenie sa
CREATE TABLE CategoryTraining (
    TrainingID INT PRIMARY KEY IDENTITY(1,1),
    MerchantName NVARCHAR(200),
    CategoryID INT NOT NULL,
    UserCorrected BIT DEFAULT 0,
    OriginalAICategory INT,
    CreatedAt DATETIME2 DEFAULT GETDATE(),
    FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID),
    FOREIGN KEY (OriginalAICategory) REFERENCES Categories(CategoryID)
);

-- Tabuľka pre kategorizačné pravidlá
CREATE TABLE CategoryRules (
    RuleID INT PRIMARY KEY IDENTITY(1,1),
    Pattern NVARCHAR(200) NOT NULL,
    CategoryID INT NOT NULL,
    Priority INT DEFAULT 0,
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME2 DEFAULT GETDATE(),
    FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID)
);

-- Indexy pre výkon
CREATE INDEX IX_Transactions_Date ON Transactions(TransactionDate);
CREATE INDEX IX_Transactions_Merchant ON Transactions(MerchantID);
CREATE INDEX IX_Transactions_Category ON Transactions(CategoryID);
CREATE INDEX IX_Merchants_IBAN ON Merchants(IBAN);
CREATE INDEX IX_Merchants_ICO ON Merchants(ICO);

-- Vloženie základných kategórií
INSERT INTO Categories (Name, Icon, Color) VALUES
('Potraviny', '🛒', '#4CAF50'),
('Drogéria', '🧴', '#2196F3'),
('Reštaurácie a Kaviarne', '☕', '#FF9800'),
('Donáška jedla', '🍕', '#FF5722'),
('Doprava', '🚗', '#9C27B0'),
('Bývanie', '🏠', '#607D8B'),
('Zdravie', '⚕️', '#E91E63'),
('Zábava', '🎬', '#3F51B5'),
('Oblečenie', '👕', '#00BCD4'),
('Telefón a Internet', '📱', '#795548'),
('Vzdelávanie', '📚', '#009688'),
('Šport', '⚽', '#8BC34A'),
('Iné', '📦', '#9E9E9E');

-- View pre prehľad výdavkov
CREATE VIEW vw_MonthlyExpenses AS
SELECT 
    YEAR(TransactionDate) AS Year,
    MONTH(TransactionDate) AS Month,
    c.Name AS Category,
    COUNT(*) AS TransactionCount,
    SUM(Amount) AS TotalAmount,
    AVG(Amount) AS AvgAmount,
    SUM(CO2Footprint) AS TotalCO2
FROM Transactions t
LEFT JOIN Categories c ON t.CategoryID = c.CategoryID
WHERE TransactionType = 'Debit'
GROUP BY YEAR(TransactionDate), MONTH(TransactionDate), c.Name;

-- View pre top obchodníkov
CREATE VIEW vw_TopMerchants AS
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

