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

IF OBJECT_ID('dbo.RiderRaceResultsSummary', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RiderRaceResultsSummary (
        RiderID INT NOT NULL,
        RaceID INT NOT NULL,
        TrackID INT NULL,
        TrackName NVARCHAR(255) NULL,
        RaceDate DATE NOT NULL,
        Discipline NVARCHAR(10) NOT NULL,
        Class NVARCHAR(20) NULL,
        Brand NVARCHAR(100) NULL,
        Result NVARCHAR(20) NOT NULL,
        QualResult NVARCHAR(20) NOT NULL,
        HeatResult NVARCHAR(20) NOT NULL,
        LCQResult NVARCHAR(20) NOT NULL,
        RefreshedAt DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.RiderPointsSummary', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RiderPointsSummary (
        RiderID INT NOT NULL,
        [Year] INT NOT NULL,
        Result NVARCHAR(20) NOT NULL,
        Points INT NOT NULL,
        Class NVARCHAR(20) NOT NULL,
        Brand NVARCHAR(200) NULL,
        SortOrder INT NOT NULL,
        RefreshedAt DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.SeasonSXMainStatsSummary', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.SeasonSXMainStatsSummary (
        [Year] INT NOT NULL,
        SportID INT NOT NULL,
        ClassID INT NOT NULL,
        RiderID INT NOT NULL,
        FullName NVARCHAR(255) NULL,
        DisplayFullName NVARCHAR(255) NULL,
        RiderCoastID INT NULL,
        Points INT NOT NULL,
        Wins INT NOT NULL,
        Podiums INT NOT NULL,
        Top5s INT NOT NULL,
        Top10s INT NOT NULL,
        BestFinish INT NULL,
        AvgFinish DECIMAL(10,2) NULL,
        MainsMade INT NOT NULL,
        Holeshots INT NOT NULL,
        AvgStartPosition DECIMAL(10,2) NULL,
        Brand NVARCHAR(100) NULL,
        RefreshedAt DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.SeasonSXStartStatsSummary', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.SeasonSXStartStatsSummary (
        [Year] INT NOT NULL,
        SportID INT NOT NULL,
        ClassID INT NOT NULL,
        RiderID INT NOT NULL,
        FullName NVARCHAR(255) NULL,
        DisplayFullName NVARCHAR(255) NULL,
        RiderCoastID INT NULL,
        QualStarts INT NOT NULL,
        Poles INT NOT NULL,
        BestQual INT NULL,
        AvgQualFinish DECIMAL(10,2) NULL,
        HeatStarts INT NOT NULL,
        HeatWins INT NOT NULL,
        BestHeat INT NULL,
        LCQStarts INT NOT NULL,
        LCQWins INT NOT NULL,
        BestLCQ INT NULL,
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

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_RiderRaceResultsSummary_Rider'
      AND object_id = OBJECT_ID('dbo.RiderRaceResultsSummary')
)
BEGIN
    CREATE INDEX IX_RiderRaceResultsSummary_Rider
        ON dbo.RiderRaceResultsSummary (RiderID, RaceDate DESC, RaceID);
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_RiderPointsSummary_Rider'
      AND object_id = OBJECT_ID('dbo.RiderPointsSummary')
)
BEGIN
    CREATE INDEX IX_RiderPointsSummary_Rider
        ON dbo.RiderPointsSummary (RiderID, [Year] DESC, SortOrder, Class);
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_SeasonSXMainStatsSummary_Season'
      AND object_id = OBJECT_ID('dbo.SeasonSXMainStatsSummary')
)
BEGIN
    CREATE INDEX IX_SeasonSXMainStatsSummary_Season
        ON dbo.SeasonSXMainStatsSummary ([Year], ClassID, RiderCoastID, RiderID);
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_SeasonSXStartStatsSummary_Season'
      AND object_id = OBJECT_ID('dbo.SeasonSXStartStatsSummary')
)
BEGIN
    CREATE INDEX IX_SeasonSXStartStatsSummary_Season
        ON dbo.SeasonSXStartStatsSummary ([Year], ClassID, RiderCoastID, RiderID);
END;
GO

TRUNCATE TABLE dbo.RiderProfileAvailabilitySummary;
TRUNCATE TABLE dbo.RiderProfileSXStatsSummary;
TRUNCATE TABLE dbo.RiderProfileSXQualSummary;
TRUNCATE TABLE dbo.RiderProfileMXStatsSummary;
TRUNCATE TABLE dbo.RiderProfileMXQualSummary;
TRUNCATE TABLE dbo.RiderRaceResultsSummary;
TRUNCATE TABLE dbo.RiderPointsSummary;
TRUNCATE TABLE dbo.SeasonSXMainStatsSummary;
TRUNCATE TABLE dbo.SeasonSXStartStatsSummary;
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

WITH SX_WithTies AS (
    SELECT
        Year,
        RiderID,
        Points,
        ClassID,
        RiderCoastID,
        CASE
            WHEN COUNT(*) OVER (
                PARTITION BY Year, ClassID, RiderCoastID, Result
            ) > 1
                THEN 'T-' + CAST(Result AS VARCHAR)
            ELSE CAST(Result AS VARCHAR)
        END AS ResultDisplay
    FROM SX_POINTS_STANDINGS
),
MX_WithTies AS (
    SELECT
        Year,
        RiderID,
        Points,
        ClassID,
        CASE
            WHEN COUNT(*) OVER (
                PARTITION BY Year, ClassID, Result
            ) > 1
                THEN 'T-' + CAST(Result AS VARCHAR)
            ELSE CAST(Result AS VARCHAR)
        END AS ResultDisplay
    FROM MX_POINTS_STANDINGS
),
Brands AS (
    SELECT
        RiderID,
        Year,
        ClassID,
        SportID,
        STRING_AGG(Brand, ', ') AS Brand
    FROM (
        SELECT DISTINCT
            RiderID,
            Year,
            ClassID,
            SportID,
            Brand
        FROM RiderBrandListYear
    ) x
    GROUP BY
        RiderID,
        Year,
        ClassID,
        SportID
)
INSERT INTO dbo.RiderPointsSummary (
    RiderID, [Year], Result, Points, Class, Brand, SortOrder
)
SELECT
    s.RiderID,
    s.Year,
    s.ResultDisplay AS Result,
    s.Points,
    CASE
        WHEN s.ClassID = 1 THEN '450SX'
        WHEN s.ClassID = 2 AND s.RiderCoastID = 1 THEN '250SX W'
        WHEN s.ClassID = 2 AND s.RiderCoastID = 2 THEN '250SX E'
    END AS Class,
    b.Brand,
    1 AS SortOrder
FROM SX_WithTies s
LEFT JOIN Brands b
    ON b.RiderID = s.RiderID
   AND b.Year = s.Year
   AND b.ClassID = s.ClassID
   AND b.SportID = 1
UNION ALL
SELECT
    m.RiderID,
    m.Year,
    m.ResultDisplay,
    m.Points,
    CASE
        WHEN m.ClassID = 1 THEN '450MX'
        WHEN m.ClassID = 2 THEN '250MX'
        WHEN m.ClassID = 3 THEN '500MX'
    END,
    b.Brand,
    0 AS SortOrder
FROM MX_WithTies m
LEFT JOIN Brands b
    ON b.RiderID = m.RiderID
   AND b.Year = m.Year
   AND b.ClassID = m.ClassID
   AND b.SportID = 2;
GO

WITH CoastPoolResolved AS (
    SELECT
        RiderID,
        [Year],
        MIN(RiderCoastID) AS RiderCoastID
    FROM CoastPool
    GROUP BY RiderID, [Year]
),
MainStatsRaw AS (
    SELECT DISTINCT *
    FROM dbo.vw_SeasonMainEventStats
    WHERE SportID = 1
),
MainStats AS (
    SELECT *
    FROM (
        SELECT
            msr.*,
            ROW_NUMBER() OVER (
                PARTITION BY msr.[Year], msr.SportID, msr.ClassID, msr.RiderID
                ORDER BY
                    CASE WHEN msr.RiderCoastID IS NULL THEN 0 ELSE 1 END,
                    msr.Wins DESC,
                    msr.AvgFinish ASC,
                    msr.Points DESC
            ) AS rn
        FROM MainStatsRaw msr
    ) ranked
    WHERE rn = 1
),
BrandAgg AS (
    SELECT
        rt.[Year],
        1 AS SportID,
        sm.ClassID,
        sm.RiderID,
        MAX(sm.Brand) AS Brand,
        COALESCE(sm.RiderCoastID, cp.RiderCoastID) AS RiderCoastID
    FROM SX_MAINS sm
    JOIN Race_Table rt
        ON rt.RaceID = sm.RaceID
    LEFT JOIN CoastPoolResolved cp
        ON cp.RiderID = sm.RiderID
       AND cp.[Year] = rt.[Year]
    WHERE rt.SportID = 1
    GROUP BY
        rt.[Year],
        sm.ClassID,
        sm.RiderID,
        COALESCE(sm.RiderCoastID, cp.RiderCoastID)
)
INSERT INTO dbo.SeasonSXMainStatsSummary (
    [Year], SportID, ClassID, RiderID, FullName, DisplayFullName, RiderCoastID,
    Points, Wins, Podiums, Top5s, Top10s, BestFinish, AvgFinish, MainsMade,
    Holeshots, AvgStartPosition, Brand
)
SELECT
    ms.[Year],
    ms.SportID,
    ms.ClassID,
    ms.RiderID,
    ms.FullName,
    COALESCE(rl.FullName, ms.FullName) AS DisplayFullName,
    ms.RiderCoastID,
    COALESCE(ms.Points, 0) AS Points,
    COALESCE(ms.Wins, 0) AS Wins,
    COALESCE(ms.Podiums, 0) AS Podiums,
    COALESCE(ms.Top5s, 0) AS Top5s,
    COALESCE(ms.Top10s, 0) AS Top10s,
    ms.BestFinish,
    ms.AvgFinish,
    COALESCE(ms.MainsMade, 0) AS MainsMade,
    COALESCE(ms.Holeshots, 0) AS Holeshots,
    ms.AvgStartPosition,
    ba.Brand
FROM MainStats ms
LEFT JOIN Rider_List rl
    ON rl.RiderID = ms.RiderID
LEFT JOIN BrandAgg ba
    ON ba.[Year] = ms.[Year]
   AND ba.SportID = ms.SportID
   AND ba.ClassID = ms.ClassID
   AND ba.RiderID = ms.RiderID
   AND (
        (ba.RiderCoastID = ms.RiderCoastID)
        OR (ba.RiderCoastID IS NULL AND ms.RiderCoastID IS NULL)
   );
GO

WITH CoastPoolResolved AS (
    SELECT
        RiderID,
        [Year],
        MIN(RiderCoastID) AS RiderCoastID
    FROM CoastPool
    GROUP BY RiderID, [Year]
),
Base AS (
    SELECT
        rt.[Year],
        1 AS SportID,
        q.ClassID,
        q.RiderID,
        COALESCE(rl.FullName, q.FullName) AS FullName,
        COALESCE(q.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
        'QUAL' AS SessionType,
        q.Result
    FROM SX_QUAL q
    JOIN Race_Table rt
        ON rt.RaceID = q.RaceID
    LEFT JOIN Rider_List rl
        ON rl.RiderID = q.RiderID
    LEFT JOIN CoastPoolResolved cp
        ON cp.RiderID = q.RiderID
       AND cp.[Year] = rt.[Year]
    WHERE rt.SportID = 1

    UNION ALL

    SELECT
        rt.[Year],
        1 AS SportID,
        h.ClassID,
        h.RiderID,
        COALESCE(rl.FullName, h.FullName) AS FullName,
        COALESCE(h.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
        'HEAT' AS SessionType,
        h.Result
    FROM SX_HEATS h
    JOIN Race_Table rt
        ON rt.RaceID = h.RaceID
    LEFT JOIN Rider_List rl
        ON rl.RiderID = h.RiderID
    LEFT JOIN CoastPoolResolved cp
        ON cp.RiderID = h.RiderID
       AND cp.[Year] = rt.[Year]
    WHERE rt.SportID = 1

    UNION ALL

    SELECT
        rt.[Year],
        1 AS SportID,
        l.ClassID,
        l.RiderID,
        COALESCE(rl.FullName, l.FullName) AS FullName,
        COALESCE(l.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
        'LCQ' AS SessionType,
        l.Result
    FROM SX_LCQS l
    JOIN Race_Table rt
        ON rt.RaceID = l.RaceID
    LEFT JOIN Rider_List rl
        ON rl.RiderID = l.RiderID
    LEFT JOIN CoastPoolResolved cp
        ON cp.RiderID = l.RiderID
       AND cp.[Year] = rt.[Year]
    WHERE rt.SportID = 1
)
INSERT INTO dbo.SeasonSXStartStatsSummary (
    [Year], SportID, ClassID, RiderID, FullName, DisplayFullName, RiderCoastID,
    QualStarts, Poles, BestQual, AvgQualFinish,
    HeatStarts, HeatWins, BestHeat,
    LCQStarts, LCQWins, BestLCQ
)
SELECT
    [Year],
    SportID,
    ClassID,
    RiderID,
    MAX(FullName) AS FullName,
    MAX(FullName) AS DisplayFullName,
    MAX(RiderCoastID) AS RiderCoastID,
    SUM(CASE WHEN SessionType = 'QUAL' THEN 1 ELSE 0 END) AS QualStarts,
    SUM(CASE WHEN SessionType = 'QUAL' AND Result = 1 THEN 1 ELSE 0 END) AS Poles,
    MIN(CASE WHEN SessionType = 'QUAL' THEN Result END) AS BestQual,
    CAST(ROUND(AVG(CASE WHEN SessionType = 'QUAL' THEN CAST(Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)) AS AvgQualFinish,
    SUM(CASE WHEN SessionType = 'HEAT' THEN 1 ELSE 0 END) AS HeatStarts,
    SUM(CASE WHEN SessionType = 'HEAT' AND Result = 1 THEN 1 ELSE 0 END) AS HeatWins,
    MIN(CASE WHEN SessionType = 'HEAT' THEN Result END) AS BestHeat,
    SUM(CASE WHEN SessionType = 'LCQ' THEN 1 ELSE 0 END) AS LCQStarts,
    SUM(CASE WHEN SessionType = 'LCQ' AND Result = 1 THEN 1 ELSE 0 END) AS LCQWins,
    MIN(CASE WHEN SessionType = 'LCQ' THEN Result END) AS BestLCQ
FROM Base
GROUP BY
    [Year],
    SportID,
    ClassID,
    RiderID;
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
    RiderID, NULL AS [Year], ClassID, CASE WHEN ClassID = 1 THEN '450' WHEN ClassID = 2 THEN '250' WHEN ClassID = 3 THEN '500' END AS Class, NULL AS Brand,
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

WITH SX_RiderRaceClasses AS (
    SELECT DISTINCT RiderID, RaceID, ClassID
    FROM (
        SELECT RiderID, RaceID, ClassID FROM SX_MAINS
        UNION ALL
        SELECT RiderID, RaceID, ClassID FROM SX_HEATS
        UNION ALL
        SELECT RiderID, RaceID, ClassID FROM SX_LCQS
        UNION ALL
        SELECT RiderID, RaceID, ClassID FROM SX_QUAL
    ) x
),
SX_MainResults AS (
    SELECT RiderID, RaceID, ClassID, Result, Brand
    FROM SX_MAINS
),
SX_HeatResults AS (
    SELECT RiderID, RaceID, ClassID, MIN(Result) AS HeatResult, MAX(Brand) AS Brand
    FROM SX_HEATS
    GROUP BY RiderID, RaceID, ClassID
),
SX_LCQResults AS (
    SELECT RiderID, RaceID, ClassID, MIN(Result) AS LCQResult, MAX(Brand) AS Brand
    FROM SX_LCQS
    GROUP BY RiderID, RaceID, ClassID
),
SX_QualResults AS (
    SELECT RiderID, RaceID, ClassID, MIN(Result) AS QualResult, MAX(Brand) AS Brand
    FROM SX_QUAL
    GROUP BY RiderID, RaceID, ClassID
),
SXResults AS (
    SELECT
        rc.RiderID,
        rt.RaceID,
        rt.TrackID,
        rt.TrackName,
        CAST(rt.RaceDate AS DATE) AS RaceDate,
        'SX' AS Discipline,
        CASE
            WHEN rc.ClassID = 1 THEN '450SX'
            WHEN rc.ClassID = 2 THEN '250SX'
            ELSE '-'
        END AS Class,
        COALESCE(q.Brand, h.Brand, l.Brand, m.Brand, '-') AS Brand,
        COALESCE(CAST(m.Result AS VARCHAR(20)), '-') AS Result,
        COALESCE(CAST(q.QualResult AS VARCHAR(20)), '-') AS QualResult,
        COALESCE(CAST(h.HeatResult AS VARCHAR(20)), '-') AS HeatResult,
        COALESCE(CAST(l.LCQResult AS VARCHAR(20)), '-') AS LCQResult
    FROM SX_RiderRaceClasses rc
    JOIN Race_Table rt
        ON rt.RaceID = rc.RaceID
    LEFT JOIN SX_MainResults m
        ON m.RiderID = rc.RiderID
       AND m.RaceID = rc.RaceID
       AND m.ClassID = rc.ClassID
    LEFT JOIN SX_HeatResults h
        ON h.RiderID = rc.RiderID
       AND h.RaceID = rc.RaceID
       AND h.ClassID = rc.ClassID
    LEFT JOIN SX_LCQResults l
        ON l.RiderID = rc.RiderID
       AND l.RaceID = rc.RaceID
       AND l.ClassID = rc.ClassID
    LEFT JOIN SX_QualResults q
        ON q.RiderID = rc.RiderID
       AND q.RaceID = rc.RaceID
       AND q.ClassID = rc.ClassID
    WHERE rt.SportID = 1
),
MX_RiderRaces AS (
    SELECT DISTINCT RiderID, RaceID
    FROM (
        SELECT RiderID, RaceID FROM MX_OVERALLS
        UNION ALL
        SELECT RiderID, RaceID FROM MX_CONSIS
        UNION ALL
        SELECT RiderID, RaceID FROM MX_QUAL
    ) x
),
MXResults AS (
    SELECT
        rr.RiderID,
        rt.RaceID,
        rt.TrackID,
        rt.TrackName,
        CAST(rt.RaceDate AS DATE) AS RaceDate,
        'MX' AS Discipline,
        CASE
            WHEN COALESCE(mo.ClassID, mq.ClassID, mc.ClassID) = 1 THEN '450MX'
            WHEN COALESCE(mo.ClassID, mq.ClassID, mc.ClassID) = 2 THEN '250MX'
            WHEN COALESCE(mo.ClassID, mq.ClassID, mc.ClassID) = 3 THEN '500MX'
            ELSE '-'
        END AS Class,
        COALESCE(mo.Brand, mq.Brand, mc.Brand, '-') AS Brand,
        COALESCE(CAST(mo.Result AS VARCHAR(20)), '-') AS Result,
        COALESCE(CAST(mq.Result AS VARCHAR(20)), '-') AS QualResult,
        '-' AS HeatResult,
        COALESCE(CAST(mc.Result AS VARCHAR(20)), '-') AS LCQResult
    FROM MX_RiderRaces rr
    JOIN Race_Table rt
        ON rt.RaceID = rr.RaceID
    LEFT JOIN MX_OVERALLS mo
        ON mo.RaceID = rr.RaceID
       AND mo.RiderID = rr.RiderID
    LEFT JOIN MX_QUAL mq
        ON mq.RaceID = rr.RaceID
       AND mq.RiderID = rr.RiderID
    LEFT JOIN MX_CONSIS mc
        ON mc.RaceID = rr.RaceID
       AND mc.RiderID = rr.RiderID
    WHERE rt.SportID = 2
)
INSERT INTO dbo.RiderRaceResultsSummary (
    RiderID, RaceID, TrackID, TrackName, RaceDate, Discipline, Class, Brand,
    Result, QualResult, HeatResult, LCQResult
)
SELECT
    RiderID, RaceID, TrackID, TrackName, RaceDate, Discipline, Class, Brand,
    Result, QualResult, HeatResult, LCQResult
FROM SXResults
UNION ALL
SELECT
    RiderID, RaceID, TrackID, TrackName, RaceDate, Discipline, Class, Brand,
    Result, QualResult, HeatResult, LCQResult
FROM MXResults;
GO
