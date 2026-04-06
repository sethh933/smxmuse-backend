SET NOCOUNT ON;

IF OBJECT_ID('dbo.RiderProfileAvailabilitySummary', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RiderProfileAvailabilitySummary (
        RiderID INT NOT NULL PRIMARY KEY,
        HasSX BIT NOT NULL,
        HasMX BIT NOT NULL,
        RefreshedAt DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.RiderProfileSXStatsSummary', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RiderProfileSXStatsSummary (
        RiderID INT NOT NULL,
        [Year] INT NULL,
        ClassID INT NOT NULL,
        Class NVARCHAR(10) NULL,
        Brand NVARCHAR(100) NULL,
        Starts INT NOT NULL,
        Best INT NULL,
        AvgMainResult DECIMAL(10,2) NULL,
        Top10Count INT NOT NULL,
        Top10Pct DECIMAL(10,2) NULL,
        Top5Count INT NOT NULL,
        Top5Pct DECIMAL(10,2) NULL,
        Podiums INT NOT NULL,
        PodiumPct DECIMAL(10,2) NULL,
        Wins INT NOT NULL,
        WinPct DECIMAL(10,2) NULL,
        LapsLed INT NOT NULL,
        AvgStart DECIMAL(10,2) NULL,
        Holeshots INT NOT NULL,
        TotalPoints INT NOT NULL,
        RefreshedAt DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.RiderProfileSXQualSummary', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RiderProfileSXQualSummary (
        RiderID INT NOT NULL,
        [Year] INT NULL,
        ClassID INT NOT NULL,
        Class NVARCHAR(10) NULL,
        Brand NVARCHAR(100) NULL,
        QualStarts INT NOT NULL,
        Poles INT NOT NULL,
        BestQual INT NULL,
        AvgQualResult DECIMAL(10,2) NULL,
        HeatStarts INT NOT NULL,
        BestHeat INT NULL,
        HeatWins INT NOT NULL,
        AvgHeatResult DECIMAL(10,2) NULL,
        LcqStarts INT NOT NULL,
        BestLcq INT NULL,
        LcqTransfers INT NOT NULL,
        LcqTransferPct DECIMAL(10,2) NULL,
        LcqWins INT NOT NULL,
        AvgLcqResult DECIMAL(10,2) NULL,
        RefreshedAt DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.RiderProfileMXStatsSummary', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RiderProfileMXStatsSummary (
        RiderID INT NOT NULL,
        [Year] INT NULL,
        ClassID INT NOT NULL,
        Class NVARCHAR(10) NULL,
        Brand NVARCHAR(100) NULL,
        Starts INT NOT NULL,
        BestOverall INT NULL,
        BestMoto INT NULL,
        AvgOverallFinish DECIMAL(10,2) NULL,
        AvgMotoFinish DECIMAL(10,2) NULL,
        AvgMoto1Finish DECIMAL(10,2) NULL,
        AvgMoto2Finish DECIMAL(10,2) NULL,
        Top10s INT NOT NULL,
        Top10Pct DECIMAL(10,2) NULL,
        Top5s INT NOT NULL,
        Top5Pct DECIMAL(10,2) NULL,
        Podiums INT NOT NULL,
        PodiumPct DECIMAL(10,2) NULL,
        Wins INT NOT NULL,
        WinPct DECIMAL(10,2) NULL,
        LapsLed INT NOT NULL,
        Holeshots INT NOT NULL,
        AvgStart DECIMAL(10,2) NULL,
        TotalPoints INT NOT NULL,
        RefreshedAt DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.RiderProfileMXQualSummary', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RiderProfileMXQualSummary (
        RiderID INT NOT NULL,
        [Year] INT NULL,
        ClassID INT NOT NULL,
        Class NVARCHAR(10) NULL,
        Brand NVARCHAR(100) NULL,
        QualAppearances INT NOT NULL,
        AvgQual DECIMAL(10,2) NULL,
        BestQual INT NULL,
        Poles INT NOT NULL,
        ConsiAppearances INT NOT NULL,
        AvgConsi DECIMAL(10,2) NULL,
        BestConsi INT NULL,
        ConsiWins INT NOT NULL,
        RefreshedAt DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_RiderProfileSXStatsSummary_Rider'
      AND object_id = OBJECT_ID('dbo.RiderProfileSXStatsSummary')
)
BEGIN
    CREATE INDEX IX_RiderProfileSXStatsSummary_Rider
        ON dbo.RiderProfileSXStatsSummary (RiderID, [Year], ClassID, Brand);
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_RiderProfileSXQualSummary_Rider'
      AND object_id = OBJECT_ID('dbo.RiderProfileSXQualSummary')
)
BEGIN
    CREATE INDEX IX_RiderProfileSXQualSummary_Rider
        ON dbo.RiderProfileSXQualSummary (RiderID, [Year], ClassID, Brand);
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_RiderProfileMXStatsSummary_Rider'
      AND object_id = OBJECT_ID('dbo.RiderProfileMXStatsSummary')
)
BEGIN
    CREATE INDEX IX_RiderProfileMXStatsSummary_Rider
        ON dbo.RiderProfileMXStatsSummary (RiderID, [Year], ClassID, Brand);
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_RiderProfileMXQualSummary_Rider'
      AND object_id = OBJECT_ID('dbo.RiderProfileMXQualSummary')
)
BEGIN
    CREATE INDEX IX_RiderProfileMXQualSummary_Rider
        ON dbo.RiderProfileMXQualSummary (RiderID, [Year], ClassID, Brand);
END;
GO

TRUNCATE TABLE dbo.RiderProfileAvailabilitySummary;
TRUNCATE TABLE dbo.RiderProfileSXStatsSummary;
TRUNCATE TABLE dbo.RiderProfileSXQualSummary;
TRUNCATE TABLE dbo.RiderProfileMXStatsSummary;
TRUNCATE TABLE dbo.RiderProfileMXQualSummary;
GO

INSERT INTO dbo.RiderProfileAvailabilitySummary (RiderID, HasSX, HasMX)
SELECT
    rl.RiderID,
    CASE WHEN sx.RiderID IS NULL THEN 0 ELSE 1 END AS HasSX,
    CASE WHEN mx.RiderID IS NULL THEN 0 ELSE 1 END AS HasMX
FROM Rider_List rl
LEFT JOIN (
    SELECT DISTINCT RiderID
    FROM (
        SELECT RiderID FROM SX_MAINS
        UNION ALL
        SELECT RiderID FROM SX_HEATS
        UNION ALL
        SELECT RiderID FROM SX_LCQS
        UNION ALL
        SELECT RiderID FROM SX_QUAL
    ) sx_all
) sx ON sx.RiderID = rl.RiderID
LEFT JOIN (
    SELECT DISTINCT RiderID
    FROM (
        SELECT RiderID FROM MX_OVERALLS
        UNION ALL
        SELECT RiderID FROM MX_CONSIS
        UNION ALL
        SELECT RiderID FROM MX_QUAL
    ) mx_all
) mx ON mx.RiderID = rl.RiderID;
GO

WITH sx_base AS (
    SELECT
        m.RiderID,
        r.[Year],
        m.ClassID,
        COALESCE(m.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
        m.Result,
        m.Points,
        m.LapsLed,
        m.[Start],
        m.Holeshot,
        m.Brand
    FROM SX_MAINS m
    JOIN Race_Table r ON r.RaceID = m.RaceID
    LEFT JOIN CoastPool cp
        ON cp.RiderID = m.RiderID
       AND cp.[Year] = r.[Year]
),
sx_year_starts AS (
    SELECT
        RiderID,
        [Year],
        ClassID,
        RiderCoastID,
        CAST(ROUND(AVG(CAST([Start] AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgStart
    FROM (
        SELECT RiderID, [Year], ClassID, RiderCoastID, [Start]
        FROM sx_base
        WHERE [Start] IS NOT NULL
        UNION ALL
        SELECT
            t.RiderID,
            r.[Year],
            t.ClassID,
            COALESCE(t.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
            t.[Start]
        FROM TC_MAINS t
        JOIN Race_Table r ON r.RaceID = t.RaceID
        LEFT JOIN CoastPool cp
            ON cp.RiderID = t.RiderID
           AND cp.[Year] = r.[Year]
        WHERE t.[Start] IS NOT NULL
    ) starts_union
    GROUP BY RiderID, [Year], ClassID, RiderCoastID
),
sx_career_class_starts AS (
    SELECT
        RiderID,
        ClassID,
        CAST(ROUND(AVG(CAST([Start] AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgStart
    FROM (
        SELECT RiderID, ClassID, [Start]
        FROM SX_MAINS
        WHERE [Start] IS NOT NULL
        UNION ALL
        SELECT RiderID, ClassID, [Start]
        FROM TC_MAINS
        WHERE [Start] IS NOT NULL
    ) starts_union
    GROUP BY RiderID, ClassID
),
sx_career_overall_starts AS (
    SELECT
        RiderID,
        CAST(ROUND(AVG(CAST([Start] AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgStart
    FROM (
        SELECT RiderID, [Start]
        FROM SX_MAINS
        WHERE [Start] IS NOT NULL
        UNION ALL
        SELECT RiderID, [Start]
        FROM TC_MAINS
        WHERE [Start] IS NOT NULL
    ) starts_union
    GROUP BY RiderID
),
sx_year_stats AS (
    SELECT
        b.RiderID,
        b.[Year],
        b.ClassID,
        CASE
            WHEN b.ClassID = 1 THEN '450'
            WHEN b.ClassID = 2 AND b.RiderCoastID = 1 THEN '250W'
            WHEN b.ClassID = 2 AND b.RiderCoastID = 2 THEN '250E'
            WHEN b.ClassID = 2 THEN '250'
            WHEN b.ClassID = 3 THEN '500'
        END AS Class,
        b.Brand,
        COUNT(*) AS Starts,
        MIN(b.Result) AS Best,
        CAST(ROUND(AVG(CAST(b.Result AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMainResult,
        SUM(CASE WHEN b.Result <= 10 THEN 1 ELSE 0 END) AS Top10Count,
        CAST(ROUND(100.0 * SUM(CASE WHEN b.Result <= 10 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS Top10Pct,
        SUM(CASE WHEN b.Result <= 5 THEN 1 ELSE 0 END) AS Top5Count,
        CAST(ROUND(100.0 * SUM(CASE WHEN b.Result <= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS Top5Pct,
        SUM(CASE WHEN b.Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
        CAST(ROUND(100.0 * SUM(CASE WHEN b.Result <= 3 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS PodiumPct,
        SUM(CASE WHEN b.Result = 1 THEN 1 ELSE 0 END) AS Wins,
        CAST(ROUND(100.0 * SUM(CASE WHEN b.Result = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS WinPct,
        SUM(COALESCE(b.LapsLed, 0)) AS LapsLed,
        ys.AvgStart,
        SUM(CASE WHEN b.Holeshot = 1 THEN 1 ELSE 0 END) AS Holeshots,
        SUM(COALESCE(b.Points, 0)) AS TotalPoints
    FROM sx_base b
    LEFT JOIN sx_year_starts ys
        ON ys.RiderID = b.RiderID
       AND ys.[Year] = b.[Year]
       AND ys.ClassID = b.ClassID
       AND ((ys.RiderCoastID = b.RiderCoastID) OR (ys.RiderCoastID IS NULL AND b.RiderCoastID IS NULL))
    GROUP BY b.RiderID, b.[Year], b.ClassID, b.RiderCoastID, b.Brand, ys.AvgStart
),
sx_career_class_stats AS (
    SELECT
        b.RiderID,
        NULL AS [Year],
        b.ClassID,
        CASE
            WHEN b.ClassID = 1 THEN '450'
            WHEN b.ClassID = 2 THEN '250'
            WHEN b.ClassID = 3 THEN '500'
        END AS Class,
        NULL AS Brand,
        COUNT(*) AS Starts,
        MIN(b.Result) AS Best,
        CAST(ROUND(AVG(CAST(b.Result AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMainResult,
        SUM(CASE WHEN b.Result <= 10 THEN 1 ELSE 0 END) AS Top10Count,
        CAST(ROUND(100.0 * SUM(CASE WHEN b.Result <= 10 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS Top10Pct,
        SUM(CASE WHEN b.Result <= 5 THEN 1 ELSE 0 END) AS Top5Count,
        CAST(ROUND(100.0 * SUM(CASE WHEN b.Result <= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS Top5Pct,
        SUM(CASE WHEN b.Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
        CAST(ROUND(100.0 * SUM(CASE WHEN b.Result <= 3 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS PodiumPct,
        SUM(CASE WHEN b.Result = 1 THEN 1 ELSE 0 END) AS Wins,
        CAST(ROUND(100.0 * SUM(CASE WHEN b.Result = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS WinPct,
        SUM(COALESCE(b.LapsLed, 0)) AS LapsLed,
        cs.AvgStart,
        SUM(CASE WHEN b.Holeshot = 1 THEN 1 ELSE 0 END) AS Holeshots,
        SUM(COALESCE(b.Points, 0)) AS TotalPoints
    FROM sx_base b
    LEFT JOIN sx_career_class_starts cs
        ON cs.RiderID = b.RiderID
       AND cs.ClassID = b.ClassID
    GROUP BY b.RiderID, b.ClassID, cs.AvgStart
),
sx_career_overall_stats AS (
    SELECT
        b.RiderID,
        NULL AS [Year],
        0 AS ClassID,
        NULL AS Class,
        NULL AS Brand,
        COUNT(*) AS Starts,
        MIN(b.Result) AS Best,
        CAST(ROUND(AVG(CAST(b.Result AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMainResult,
        SUM(CASE WHEN b.Result <= 10 THEN 1 ELSE 0 END) AS Top10Count,
        CAST(ROUND(100.0 * SUM(CASE WHEN b.Result <= 10 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS Top10Pct,
        SUM(CASE WHEN b.Result <= 5 THEN 1 ELSE 0 END) AS Top5Count,
        CAST(ROUND(100.0 * SUM(CASE WHEN b.Result <= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS Top5Pct,
        SUM(CASE WHEN b.Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
        CAST(ROUND(100.0 * SUM(CASE WHEN b.Result <= 3 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS PodiumPct,
        SUM(CASE WHEN b.Result = 1 THEN 1 ELSE 0 END) AS Wins,
        CAST(ROUND(100.0 * SUM(CASE WHEN b.Result = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS WinPct,
        SUM(COALESCE(b.LapsLed, 0)) AS LapsLed,
        os.AvgStart,
        SUM(CASE WHEN b.Holeshot = 1 THEN 1 ELSE 0 END) AS Holeshots,
        SUM(COALESCE(b.Points, 0)) AS TotalPoints
    FROM sx_base b
    LEFT JOIN sx_career_overall_starts os
        ON os.RiderID = b.RiderID
    GROUP BY b.RiderID, os.AvgStart
)
INSERT INTO dbo.RiderProfileSXStatsSummary (
    RiderID, [Year], ClassID, Class, Brand, Starts, Best, AvgMainResult,
    Top10Count, Top10Pct, Top5Count, Top5Pct, Podiums, PodiumPct,
    Wins, WinPct, LapsLed, AvgStart, Holeshots, TotalPoints
)
SELECT * FROM sx_year_stats
UNION ALL
SELECT * FROM sx_career_class_stats
UNION ALL
SELECT * FROM sx_career_overall_stats;
GO

WITH sx_sessions AS (
    SELECT
        q.RiderID,
        r.[Year],
        q.ClassID,
        COALESCE(q.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
        q.Brand,
        'QUAL' AS SessionType,
        q.Result,
        CAST(NULL AS INT) AS IsLcqTransfer
    FROM SX_QUAL q
    JOIN Race_Table r ON r.RaceID = q.RaceID
    LEFT JOIN CoastPool cp ON cp.RiderID = q.RiderID AND cp.[Year] = r.[Year]
    UNION ALL
    SELECT
        h.RiderID,
        r.[Year],
        h.ClassID,
        COALESCE(h.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
        h.Brand,
        'HEAT',
        h.Result,
        CAST(NULL AS INT)
    FROM SX_HEATS h
    JOIN Race_Table r ON r.RaceID = h.RaceID
    LEFT JOIN CoastPool cp ON cp.RiderID = h.RiderID AND cp.[Year] = r.[Year]
    UNION ALL
    SELECT
        l.RiderID,
        r.[Year],
        l.ClassID,
        COALESCE(l.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
        l.Brand,
        'LCQ',
        l.Result,
        CASE WHEN m.RiderID IS NULL THEN 0 ELSE 1 END
    FROM SX_LCQS l
    JOIN Race_Table r ON r.RaceID = l.RaceID
    LEFT JOIN CoastPool cp ON cp.RiderID = l.RiderID AND cp.[Year] = r.[Year]
    LEFT JOIN (
        SELECT DISTINCT RaceID, ClassID, RiderID
        FROM SX_MAINS
    ) m
        ON m.RaceID = l.RaceID
       AND m.ClassID = l.ClassID
       AND m.RiderID = l.RiderID
),
sx_qual_year_stats AS (
    SELECT
        s.RiderID,
        s.[Year],
        s.ClassID,
        CASE
            WHEN s.ClassID = 1 THEN '450'
            WHEN s.ClassID = 2 AND s.RiderCoastID = 1 THEN '250W'
            WHEN s.ClassID = 2 AND s.RiderCoastID = 2 THEN '250E'
            WHEN s.ClassID = 2 THEN '250'
            WHEN s.ClassID = 3 THEN '500'
        END AS Class,
        s.Brand,
        SUM(CASE WHEN s.SessionType = 'QUAL' THEN 1 ELSE 0 END) AS QualStarts,
        SUM(CASE WHEN s.SessionType = 'QUAL' AND s.Result = 1 THEN 1 ELSE 0 END) AS Poles,
        MIN(CASE WHEN s.SessionType = 'QUAL' THEN s.Result END) AS BestQual,
        CAST(ROUND(AVG(CASE WHEN s.SessionType = 'QUAL' THEN CAST(s.Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)) AS AvgQualResult,
        SUM(CASE WHEN s.SessionType = 'HEAT' THEN 1 ELSE 0 END) AS HeatStarts,
        MIN(CASE WHEN s.SessionType = 'HEAT' THEN s.Result END) AS BestHeat,
        SUM(CASE WHEN s.SessionType = 'HEAT' AND s.Result = 1 THEN 1 ELSE 0 END) AS HeatWins,
        CAST(ROUND(AVG(CASE WHEN s.SessionType = 'HEAT' THEN CAST(s.Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)) AS AvgHeatResult,
        SUM(CASE WHEN s.SessionType = 'LCQ' THEN 1 ELSE 0 END) AS LcqStarts,
        MIN(CASE WHEN s.SessionType = 'LCQ' THEN s.Result END) AS BestLcq,
        SUM(CASE WHEN s.SessionType = 'LCQ' AND s.IsLcqTransfer = 1 THEN 1 ELSE 0 END) AS LcqTransfers,
        CAST(ROUND(
            100.0 * SUM(CASE WHEN s.SessionType = 'LCQ' AND s.IsLcqTransfer = 1 THEN 1 ELSE 0 END)
            / NULLIF(SUM(CASE WHEN s.SessionType = 'LCQ' THEN 1 ELSE 0 END), 0),
            2
        ) AS DECIMAL(10,2)) AS LcqTransferPct,
        SUM(CASE WHEN s.SessionType = 'LCQ' AND s.Result = 1 THEN 1 ELSE 0 END) AS LcqWins,
        CAST(ROUND(AVG(CASE WHEN s.SessionType = 'LCQ' THEN CAST(s.Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)) AS AvgLcqResult
    FROM sx_sessions s
    GROUP BY s.RiderID, s.[Year], s.ClassID, s.RiderCoastID, s.Brand
),
sx_qual_career_class_stats AS (
    SELECT
        s.RiderID,
        NULL AS [Year],
        s.ClassID,
        CASE
            WHEN s.ClassID = 1 THEN '450'
            WHEN s.ClassID = 2 THEN '250'
            WHEN s.ClassID = 3 THEN '500'
        END AS Class,
        NULL AS Brand,
        SUM(CASE WHEN s.SessionType = 'QUAL' THEN 1 ELSE 0 END) AS QualStarts,
        SUM(CASE WHEN s.SessionType = 'QUAL' AND s.Result = 1 THEN 1 ELSE 0 END) AS Poles,
        MIN(CASE WHEN s.SessionType = 'QUAL' THEN s.Result END) AS BestQual,
        CAST(ROUND(AVG(CASE WHEN s.SessionType = 'QUAL' THEN CAST(s.Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)) AS AvgQualResult,
        SUM(CASE WHEN s.SessionType = 'HEAT' THEN 1 ELSE 0 END) AS HeatStarts,
        MIN(CASE WHEN s.SessionType = 'HEAT' THEN s.Result END) AS BestHeat,
        SUM(CASE WHEN s.SessionType = 'HEAT' AND s.Result = 1 THEN 1 ELSE 0 END) AS HeatWins,
        CAST(ROUND(AVG(CASE WHEN s.SessionType = 'HEAT' THEN CAST(s.Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)) AS AvgHeatResult,
        SUM(CASE WHEN s.SessionType = 'LCQ' THEN 1 ELSE 0 END) AS LcqStarts,
        MIN(CASE WHEN s.SessionType = 'LCQ' THEN s.Result END) AS BestLcq,
        SUM(CASE WHEN s.SessionType = 'LCQ' AND s.IsLcqTransfer = 1 THEN 1 ELSE 0 END) AS LcqTransfers,
        CAST(ROUND(
            100.0 * SUM(CASE WHEN s.SessionType = 'LCQ' AND s.IsLcqTransfer = 1 THEN 1 ELSE 0 END)
            / NULLIF(SUM(CASE WHEN s.SessionType = 'LCQ' THEN 1 ELSE 0 END), 0),
            2
        ) AS DECIMAL(10,2)) AS LcqTransferPct,
        SUM(CASE WHEN s.SessionType = 'LCQ' AND s.Result = 1 THEN 1 ELSE 0 END) AS LcqWins,
        CAST(ROUND(AVG(CASE WHEN s.SessionType = 'LCQ' THEN CAST(s.Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)) AS AvgLcqResult
    FROM sx_sessions s
    GROUP BY s.RiderID, s.ClassID
),
sx_qual_career_overall_stats AS (
    SELECT
        s.RiderID,
        NULL AS [Year],
        0 AS ClassID,
        NULL AS Class,
        NULL AS Brand,
        SUM(CASE WHEN s.SessionType = 'QUAL' THEN 1 ELSE 0 END) AS QualStarts,
        SUM(CASE WHEN s.SessionType = 'QUAL' AND s.Result = 1 THEN 1 ELSE 0 END) AS Poles,
        MIN(CASE WHEN s.SessionType = 'QUAL' THEN s.Result END) AS BestQual,
        CAST(ROUND(AVG(CASE WHEN s.SessionType = 'QUAL' THEN CAST(s.Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)) AS AvgQualResult,
        SUM(CASE WHEN s.SessionType = 'HEAT' THEN 1 ELSE 0 END) AS HeatStarts,
        MIN(CASE WHEN s.SessionType = 'HEAT' THEN s.Result END) AS BestHeat,
        SUM(CASE WHEN s.SessionType = 'HEAT' AND s.Result = 1 THEN 1 ELSE 0 END) AS HeatWins,
        CAST(ROUND(AVG(CASE WHEN s.SessionType = 'HEAT' THEN CAST(s.Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)) AS AvgHeatResult,
        SUM(CASE WHEN s.SessionType = 'LCQ' THEN 1 ELSE 0 END) AS LcqStarts,
        MIN(CASE WHEN s.SessionType = 'LCQ' THEN s.Result END) AS BestLcq,
        SUM(CASE WHEN s.SessionType = 'LCQ' AND s.IsLcqTransfer = 1 THEN 1 ELSE 0 END) AS LcqTransfers,
        CAST(ROUND(
            100.0 * SUM(CASE WHEN s.SessionType = 'LCQ' AND s.IsLcqTransfer = 1 THEN 1 ELSE 0 END)
            / NULLIF(SUM(CASE WHEN s.SessionType = 'LCQ' THEN 1 ELSE 0 END), 0),
            2
        ) AS DECIMAL(10,2)) AS LcqTransferPct,
        SUM(CASE WHEN s.SessionType = 'LCQ' AND s.Result = 1 THEN 1 ELSE 0 END) AS LcqWins,
        CAST(ROUND(AVG(CASE WHEN s.SessionType = 'LCQ' THEN CAST(s.Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)) AS AvgLcqResult
    FROM sx_sessions s
    GROUP BY s.RiderID
)
INSERT INTO dbo.RiderProfileSXQualSummary (
    RiderID, [Year], ClassID, Class, Brand, QualStarts, Poles, BestQual, AvgQualResult,
    HeatStarts, BestHeat, HeatWins, AvgHeatResult, LcqStarts, BestLcq,
    LcqTransfers, LcqTransferPct, LcqWins, AvgLcqResult
)
SELECT * FROM sx_qual_year_stats
UNION ALL
SELECT * FROM sx_qual_career_class_stats
UNION ALL
SELECT * FROM sx_qual_career_overall_stats;
GO

WITH overall_year_brand AS (
    SELECT
        o.RiderID,
        r.[Year],
        o.ClassID,
        CASE
            WHEN o.ClassID = 1 THEN '450'
            WHEN o.ClassID = 2 THEN '250'
            WHEN o.ClassID = 3 THEN '500'
        END AS Class,
        o.Brand,
        COUNT(*) AS Starts,
        MIN(o.Result) AS BestOverall,
        MIN(
            CASE
                WHEN o.Moto1 IS NULL THEN o.Moto2
                WHEN o.Moto2 IS NULL THEN o.Moto1
                WHEN o.Moto1 < o.Moto2 THEN o.Moto1
                ELSE o.Moto2
            END
        ) AS BestMoto,
        CAST(ROUND(AVG(CAST(o.Result AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgOverallFinish,
        CAST(ROUND(
            ( SUM(CAST(o.Moto1 AS DECIMAL(10,2))) + SUM(CAST(o.Moto2 AS DECIMAL(10,2))) )
            / NULLIF(
                SUM(CASE WHEN o.Moto1 IS NOT NULL THEN 1 ELSE 0 END)
              + SUM(CASE WHEN o.Moto2 IS NOT NULL THEN 1 ELSE 0 END),
              0
            ), 2) AS DECIMAL(10,2)) AS AvgMotoFinish,
        CAST(ROUND(AVG(CAST(o.Moto1 AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMoto1Finish,
        CAST(ROUND(AVG(CAST(o.Moto2 AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMoto2Finish,
        SUM(CASE WHEN o.Result <= 10 THEN 1 ELSE 0 END) AS Top10s,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 10 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS Top10Pct,
        SUM(CASE WHEN o.Result <= 5 THEN 1 ELSE 0 END) AS Top5s,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS Top5Pct,
        SUM(CASE WHEN o.Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 3 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS PodiumPct,
        SUM(CASE WHEN o.Result = 1 THEN 1 ELSE 0 END) AS Wins,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS WinPct,
        SUM(CASE
            WHEN o.LapsLed IS NOT NULL THEN CAST(o.LapsLed AS INT)
            ELSE CAST(COALESCE(o.M1_Laps_Led,0) + COALESCE(o.M2_Laps_Led,0) AS INT)
        END) AS LapsLed,
        SUM(COALESCE(o.Holeshot, 0)) AS Holeshots,
        CAST(ROUND(
            ( SUM(CASE WHEN o.M1_Start IS NOT NULL THEN CAST(o.M1_Start AS DECIMAL(10,2)) ELSE 0 END)
            + SUM(CASE WHEN o.M2_Start IS NOT NULL THEN CAST(o.M2_Start AS DECIMAL(10,2)) ELSE 0 END) )
            / NULLIF(
                SUM(CASE WHEN o.M1_Start IS NOT NULL THEN 1 ELSE 0 END)
              + SUM(CASE WHEN o.M2_Start IS NOT NULL THEN 1 ELSE 0 END),
              0
            ), 2) AS DECIMAL(10,2)) AS AvgStart,
        SUM(COALESCE(o.Points,0)) AS TotalPoints
    FROM MX_OVERALLS o
    JOIN Race_Table r ON r.RaceID = o.RaceID
    WHERE o.Sport_ID = 2
    GROUP BY
        o.RiderID,
        r.[Year],
        o.ClassID,
        CASE WHEN o.ClassID = 1 THEN '450' WHEN o.ClassID = 2 THEN '250' WHEN o.ClassID = 3 THEN '500' END,
        o.Brand
),
overall_career_class AS (
    SELECT
        o.RiderID,
        o.ClassID,
        COUNT(*) AS Starts,
        MIN(o.Result) AS BestOverall,
        MIN(CASE WHEN o.Moto1 IS NULL THEN o.Moto2 WHEN o.Moto2 IS NULL THEN o.Moto1 WHEN o.Moto1 < o.Moto2 THEN o.Moto1 ELSE o.Moto2 END) AS BestMoto,
        CAST(ROUND(AVG(CAST(o.Result AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgOverallFinish,
        CAST(ROUND(
            ( SUM(CAST(o.Moto1 AS DECIMAL(10,2))) + SUM(CAST(o.Moto2 AS DECIMAL(10,2))) )
            / NULLIF(
                SUM(CASE WHEN o.Moto1 IS NOT NULL THEN 1 ELSE 0 END)
              + SUM(CASE WHEN o.Moto2 IS NOT NULL THEN 1 ELSE 0 END),
              0
            ), 2) AS DECIMAL(10,2)) AS AvgMotoFinish,
        CAST(ROUND(AVG(CAST(o.Moto1 AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMoto1Finish,
        CAST(ROUND(AVG(CAST(o.Moto2 AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMoto2Finish,
        SUM(CASE WHEN o.Result <= 10 THEN 1 ELSE 0 END) AS Top10s,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 10 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS Top10Pct,
        SUM(CASE WHEN o.Result <= 5 THEN 1 ELSE 0 END) AS Top5s,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS Top5Pct,
        SUM(CASE WHEN o.Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 3 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS PodiumPct,
        SUM(CASE WHEN o.Result = 1 THEN 1 ELSE 0 END) AS Wins,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS WinPct,
        SUM(CASE WHEN o.LapsLed IS NOT NULL THEN CAST(o.LapsLed AS INT) ELSE CAST(COALESCE(o.M1_Laps_Led,0) + COALESCE(o.M2_Laps_Led,0) AS INT) END) AS LapsLed,
        SUM(COALESCE(o.Holeshot, 0)) AS Holeshots,
        CAST(ROUND(
            ( SUM(CASE WHEN o.M1_Start IS NOT NULL THEN CAST(o.M1_Start AS DECIMAL(10,2)) ELSE 0 END)
            + SUM(CASE WHEN o.M2_Start IS NOT NULL THEN CAST(o.M2_Start AS DECIMAL(10,2)) ELSE 0 END) )
            / NULLIF(
                SUM(CASE WHEN o.M1_Start IS NOT NULL THEN 1 ELSE 0 END)
              + SUM(CASE WHEN o.M2_Start IS NOT NULL THEN 1 ELSE 0 END),
              0
            ), 2) AS DECIMAL(10,2)) AS AvgStart,
        SUM(COALESCE(o.Points,0)) AS TotalPoints
    FROM MX_OVERALLS o
    WHERE o.Sport_ID = 2
    GROUP BY o.RiderID, o.ClassID
),
overall_career_combined AS (
    SELECT
        o.RiderID,
        COUNT(*) AS Starts,
        MIN(o.Result) AS BestOverall,
        MIN(CASE WHEN o.Moto1 IS NULL THEN o.Moto2 WHEN o.Moto2 IS NULL THEN o.Moto1 WHEN o.Moto1 < o.Moto2 THEN o.Moto1 ELSE o.Moto2 END) AS BestMoto,
        CAST(ROUND(AVG(CAST(o.Result AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgOverallFinish,
        CAST(ROUND(
            ( SUM(CAST(o.Moto1 AS DECIMAL(10,2))) + SUM(CAST(o.Moto2 AS DECIMAL(10,2))) )
            / NULLIF(
                SUM(CASE WHEN o.Moto1 IS NOT NULL THEN 1 ELSE 0 END)
              + SUM(CASE WHEN o.Moto2 IS NOT NULL THEN 1 ELSE 0 END),
              0
            ), 2) AS DECIMAL(10,2)) AS AvgMotoFinish,
        CAST(ROUND(AVG(CAST(o.Moto1 AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMoto1Finish,
        CAST(ROUND(AVG(CAST(o.Moto2 AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMoto2Finish,
        SUM(CASE WHEN o.Result <= 10 THEN 1 ELSE 0 END) AS Top10s,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 10 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS Top10Pct,
        SUM(CASE WHEN o.Result <= 5 THEN 1 ELSE 0 END) AS Top5s,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS Top5Pct,
        SUM(CASE WHEN o.Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 3 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS PodiumPct,
        SUM(CASE WHEN o.Result = 1 THEN 1 ELSE 0 END) AS Wins,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS WinPct,
        SUM(CASE WHEN o.LapsLed IS NOT NULL THEN CAST(o.LapsLed AS INT) ELSE CAST(COALESCE(o.M1_Laps_Led,0) + COALESCE(o.M2_Laps_Led,0) AS INT) END) AS LapsLed,
        SUM(COALESCE(o.Holeshot, 0)) AS Holeshots,
        CAST(ROUND(
            ( SUM(CASE WHEN o.M1_Start IS NOT NULL THEN CAST(o.M1_Start AS DECIMAL(10,2)) ELSE 0 END)
            + SUM(CASE WHEN o.M2_Start IS NOT NULL THEN CAST(o.M2_Start AS DECIMAL(10,2)) ELSE 0 END) )
            / NULLIF(
                SUM(CASE WHEN o.M1_Start IS NOT NULL THEN 1 ELSE 0 END)
              + SUM(CASE WHEN o.M2_Start IS NOT NULL THEN 1 ELSE 0 END),
              0
            ), 2) AS DECIMAL(10,2)) AS AvgStart,
        SUM(COALESCE(o.Points,0)) AS TotalPoints
    FROM MX_OVERALLS o
    WHERE o.Sport_ID = 2
    GROUP BY o.RiderID
)
INSERT INTO dbo.RiderProfileMXStatsSummary (
    RiderID, [Year], ClassID, Class, Brand, Starts, BestOverall, BestMoto, AvgOverallFinish,
    AvgMotoFinish, AvgMoto1Finish, AvgMoto2Finish, Top10s, Top10Pct, Top5s, Top5Pct,
    Podiums, PodiumPct, Wins, WinPct, LapsLed, Holeshots, AvgStart, TotalPoints
)
SELECT
    RiderID, [Year], ClassID, Class, Brand, Starts, BestOverall, BestMoto, AvgOverallFinish,
    AvgMotoFinish, AvgMoto1Finish, AvgMoto2Finish, Top10s, Top10Pct, Top5s, Top5Pct,
    Podiums, PodiumPct, Wins, WinPct, LapsLed, Holeshots, AvgStart, TotalPoints
FROM overall_year_brand
UNION ALL
SELECT
    RiderID, NULL AS [Year], ClassID, CASE WHEN ClassID = 1 THEN '450' WHEN ClassID = 2 THEN '250' END AS Class, NULL AS Brand,
    Starts, BestOverall, BestMoto, AvgOverallFinish, AvgMotoFinish, AvgMoto1Finish, AvgMoto2Finish,
    Top10s, Top10Pct, Top5s, Top5Pct, Podiums, PodiumPct, Wins, WinPct, LapsLed, Holeshots, AvgStart, TotalPoints
FROM overall_career_class
UNION ALL
SELECT
    RiderID, NULL AS [Year], 0 AS ClassID, NULL AS Class, NULL AS Brand,
    Starts, BestOverall, BestMoto, AvgOverallFinish, AvgMotoFinish, AvgMoto1Finish, AvgMoto2Finish,
    Top10s, Top10Pct, Top5s, Top5Pct, Podiums, PodiumPct, Wins, WinPct, LapsLed, Holeshots, AvgStart, TotalPoints
FROM overall_career_combined;
GO

WITH QualYearly AS (
    SELECT
        q.RiderID,
        r.Year,
        q.ClassID,
        q.Brand,
        COUNT(DISTINCT q.RaceID) AS QualAppearances,
        CAST(ROUND(AVG(CAST(q.Result AS FLOAT)), 2) AS DECIMAL(10,2)) AS AvgQual,
        MIN(q.Result) AS BestQual,
        SUM(CASE WHEN q.Result = 1 THEN 1 ELSE 0 END) AS Poles
    FROM MX_QUAL q
    JOIN Race_Table r ON r.RaceID = q.RaceID
    GROUP BY q.RiderID, r.Year, q.ClassID, q.Brand
),
ConsiYearly AS (
    SELECT
        c.RiderID,
        r.Year,
        c.ClassID,
        c.Brand,
        COUNT(DISTINCT c.RaceID) AS ConsiAppearances,
        CAST(ROUND(AVG(CAST(c.Result AS FLOAT)), 2) AS DECIMAL(10,2)) AS AvgConsi,
        MIN(c.Result) AS BestConsi,
        SUM(CASE WHEN c.Result = 1 THEN 1 ELSE 0 END) AS ConsiWins
    FROM MX_CONSIS c
    JOIN Race_Table r ON r.RaceID = c.RaceID
    GROUP BY c.RiderID, r.Year, c.ClassID, c.Brand
),
BrandUnion AS (
    SELECT RiderID, Year, ClassID, Brand FROM QualYearly
    UNION
    SELECT RiderID, Year, ClassID, Brand FROM ConsiYearly
),
Yearly AS (
    SELECT
        bu.RiderID,
        bu.Year,
        bu.ClassID,
        bu.Brand,
        ISNULL(q.QualAppearances, 0) AS QualAppearances,
        q.AvgQual,
        q.BestQual,
        ISNULL(q.Poles, 0) AS Poles,
        ISNULL(c.ConsiAppearances, 0) AS ConsiAppearances,
        c.AvgConsi,
        c.BestConsi,
        ISNULL(c.ConsiWins, 0) AS ConsiWins
    FROM BrandUnion bu
    LEFT JOIN QualYearly q
        ON bu.RiderID = q.RiderID
       AND bu.Year = q.Year
       AND bu.ClassID = q.ClassID
       AND ((bu.Brand = q.Brand) OR (bu.Brand IS NULL AND q.Brand IS NULL))
    LEFT JOIN ConsiYearly c
        ON bu.RiderID = c.RiderID
       AND bu.Year = c.Year
       AND bu.ClassID = c.ClassID
       AND ((bu.Brand = c.Brand) OR (bu.Brand IS NULL AND c.Brand IS NULL))
),
CareerByClass AS (
    SELECT
        RiderID,
        ClassID,
        COUNT(DISTINCT CASE WHEN Source = 'Qual' THEN RaceID END) AS QualAppearances,
        CAST(ROUND(AVG(CASE WHEN Source = 'Qual' THEN CAST(Result AS FLOAT) END), 2) AS DECIMAL(10,2)) AS AvgQual,
        MIN(CASE WHEN Source = 'Qual' THEN Result END) AS BestQual,
        SUM(CASE WHEN Source = 'Qual' AND Result = 1 THEN 1 ELSE 0 END) AS Poles,
        COUNT(DISTINCT CASE WHEN Source = 'Consi' THEN RaceID END) AS ConsiAppearances,
        CAST(ROUND(AVG(CASE WHEN Source = 'Consi' THEN CAST(Result AS FLOAT) END), 2) AS DECIMAL(10,2)) AS AvgConsi,
        MIN(CASE WHEN Source = 'Consi' THEN Result END) AS BestConsi,
        SUM(CASE WHEN Source = 'Consi' AND Result = 1 THEN 1 ELSE 0 END) AS ConsiWins
    FROM (
        SELECT RiderID, ClassID, RaceID, Result, 'Qual' AS Source FROM MX_QUAL
        UNION ALL
        SELECT RiderID, ClassID, RaceID, Result, 'Consi' AS Source FROM MX_CONSIS
    ) x
    GROUP BY RiderID, ClassID
),
CareerOverall AS (
    SELECT
        RiderID,
        COUNT(DISTINCT CASE WHEN Source = 'Qual' THEN RaceID END) AS QualAppearances,
        CAST(ROUND(AVG(CASE WHEN Source = 'Qual' THEN CAST(Result AS FLOAT) END), 2) AS DECIMAL(10,2)) AS AvgQual,
        MIN(CASE WHEN Source = 'Qual' THEN Result END) AS BestQual,
        SUM(CASE WHEN Source = 'Qual' AND Result = 1 THEN 1 ELSE 0 END) AS Poles,
        COUNT(DISTINCT CASE WHEN Source = 'Consi' THEN RaceID END) AS ConsiAppearances,
        CAST(ROUND(AVG(CASE WHEN Source = 'Consi' THEN CAST(Result AS FLOAT) END), 2) AS DECIMAL(10,2)) AS AvgConsi,
        MIN(CASE WHEN Source = 'Consi' THEN Result END) AS BestConsi,
        SUM(CASE WHEN Source = 'Consi' AND Result = 1 THEN 1 ELSE 0 END) AS ConsiWins
    FROM (
        SELECT RiderID, RaceID, Result, 'Qual' AS Source FROM MX_QUAL
        UNION ALL
        SELECT RiderID, RaceID, Result, 'Consi' AS Source FROM MX_CONSIS
    ) x
    GROUP BY RiderID
)
INSERT INTO dbo.RiderProfileMXQualSummary (
    RiderID, [Year], ClassID, Class, Brand, QualAppearances, AvgQual, BestQual,
    Poles, ConsiAppearances, AvgConsi, BestConsi, ConsiWins
)
SELECT
    RiderID,
    [Year],
    ClassID,
    CASE
        WHEN ClassID = 1 THEN '450'
        WHEN ClassID = 2 THEN '250'
        WHEN ClassID = 3 THEN '500'
        WHEN ClassID = 0 THEN NULL
    END AS Class,
    Brand,
    QualAppearances,
    AvgQual,
    BestQual,
    Poles,
    ConsiAppearances,
    AvgConsi,
    BestConsi,
    ConsiWins
FROM Yearly
UNION ALL
SELECT
    RiderID,
    NULL AS [Year],
    ClassID,
    CASE
        WHEN ClassID = 1 THEN '450'
        WHEN ClassID = 2 THEN '250'
        WHEN ClassID = 3 THEN '500'
        WHEN ClassID = 0 THEN NULL
    END AS Class,
    NULL AS Brand,
    QualAppearances,
    AvgQual,
    BestQual,
    Poles,
    ConsiAppearances,
    AvgConsi,
    BestConsi,
    ConsiWins
FROM CareerByClass
UNION ALL
SELECT
    RiderID,
    NULL AS [Year],
    0 AS ClassID,
    NULL AS Class,
    NULL AS Brand,
    QualAppearances,
    AvgQual,
    BestQual,
    Poles,
    ConsiAppearances,
    AvgConsi,
    BestConsi,
    ConsiWins
FROM CareerOverall;
GO
