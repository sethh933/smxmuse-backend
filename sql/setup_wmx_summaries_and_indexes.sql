SET NOCOUNT ON;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.WMX_OVERALLS') AND name = 'IX_WMX_OVERALLS_RiderRace')
    CREATE NONCLUSTERED INDEX IX_WMX_OVERALLS_RiderRace
    ON dbo.WMX_OVERALLS (riderid, raceid)
    INCLUDE (Result, FullName, Moto1, Moto2, Moto3, Brand, Points, LapsLed, M1_Laps_Led, M2_Laps_Led, Holeshot, M1_Start, M2_Start);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.WMX_OVERALLS') AND name = 'IX_WMX_OVERALLS_RaceRider')
    CREATE NONCLUSTERED INDEX IX_WMX_OVERALLS_RaceRider
    ON dbo.WMX_OVERALLS (raceid, riderid)
    INCLUDE (Result, FullName, Moto1, Moto2, Moto3, Brand, Points, LapsLed, M1_Laps_Led, M2_Laps_Led, Holeshot, M1_Start, M2_Start);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.WMX_QUAL') AND name = 'IX_WMX_QUAL_RiderRace')
    CREATE NONCLUSTERED INDEX IX_WMX_QUAL_RiderRace
    ON dbo.WMX_QUAL (riderid, raceid)
    INCLUDE (Result, FullName, Brand, BestLap);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.WMX_QUAL') AND name = 'IX_WMX_QUAL_RaceRider')
    CREATE NONCLUSTERED INDEX IX_WMX_QUAL_RaceRider
    ON dbo.WMX_QUAL (raceid, riderid)
    INCLUDE (Result, FullName, Brand, BestLap);

IF EXISTS (
    SELECT 1
    FROM sys.indexes i
    WHERE i.object_id = OBJECT_ID('dbo.WMX_MOTOS')
      AND i.name = 'IX_WMX_MOTOS_RaceMotoRider'
      AND (
          NOT EXISTS (
              SELECT 1 FROM sys.index_columns ic
              JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
              WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id
                AND ic.is_included_column = 1 AND c.name = 'Interval'
          )
          OR NOT EXISTS (
              SELECT 1 FROM sys.index_columns ic
              JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
              WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id
                AND ic.is_included_column = 1 AND c.name = 'BestLap'
          )
          OR NOT EXISTS (
              SELECT 1 FROM sys.index_columns ic
              JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
              WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id
                AND ic.is_included_column = 1 AND c.name = 'HoleshotPos'
          )
      )
)
    DROP INDEX IX_WMX_MOTOS_RaceMotoRider ON dbo.WMX_MOTOS;

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.WMX_MOTOS') AND name = 'IX_WMX_MOTOS_RaceMotoRider')
    CREATE NONCLUSTERED INDEX IX_WMX_MOTOS_RaceMotoRider
    ON dbo.WMX_MOTOS (raceid, Moto, riderid)
    INCLUDE (Result, FullName, Brand, Interval, BestLap, Start, LapsLed, Holeshot, HoleshotPos, RaceStatus);

IF EXISTS (
    SELECT 1
    FROM sys.indexes i
    WHERE i.object_id = OBJECT_ID('dbo.WMX_MOTOS')
      AND i.name = 'IX_WMX_MOTOS_RiderRaceMoto'
      AND (
          NOT EXISTS (
              SELECT 1 FROM sys.index_columns ic
              JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
              WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id
                AND ic.is_included_column = 1 AND c.name = 'Interval'
          )
          OR NOT EXISTS (
              SELECT 1 FROM sys.index_columns ic
              JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
              WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id
                AND ic.is_included_column = 1 AND c.name = 'BestLap'
          )
          OR NOT EXISTS (
              SELECT 1 FROM sys.index_columns ic
              JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
              WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id
                AND ic.is_included_column = 1 AND c.name = 'HoleshotPos'
          )
      )
)
    DROP INDEX IX_WMX_MOTOS_RiderRaceMoto ON dbo.WMX_MOTOS;

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.WMX_MOTOS') AND name = 'IX_WMX_MOTOS_RiderRaceMoto')
    CREATE NONCLUSTERED INDEX IX_WMX_MOTOS_RiderRaceMoto
    ON dbo.WMX_MOTOS (riderid, raceid, Moto)
    INCLUDE (Result, FullName, Brand, Interval, BestLap, Start, LapsLed, Holeshot, HoleshotPos, RaceStatus);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.WMX_MOTO_SEGMENTS') AND name = 'IX_WMX_MOTO_SEGMENTS_RaceMotoRider')
    CREATE NONCLUSTERED INDEX IX_WMX_MOTO_SEGMENTS_RaceMotoRider
    ON dbo.WMX_MOTO_SEGMENTS (raceid, Moto, riderid, Lap)
    INCLUDE (sportid, Laptime, position, SEG_1, SEG_2, SEG_3, SEG_4, SEG_5, SEG_6, SEG_7, SEG_8, SEG_9, SEG_10);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.WMX_QUAL_SESSIONS') AND name = 'IX_WMX_QUAL_SESSIONS_RaceRiderSession')
    CREATE NONCLUSTERED INDEX IX_WMX_QUAL_SESSIONS_RaceRiderSession
    ON dbo.WMX_QUAL_SESSIONS (raceid, riderid, Session, Lap)
    INCLUDE (sportid, Laptime, SEG_1, SEG_2, SEG_3, SEG_4, SEG_5, SEG_6, SEG_7, SEG_8, SEG_9, SEG_10);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.WMX_POINTS_STANDINGS') AND name = 'IX_WMX_POINTS_STANDINGS_RiderYear')
    CREATE NONCLUSTERED INDEX IX_WMX_POINTS_STANDINGS_RiderYear
    ON dbo.WMX_POINTS_STANDINGS (RiderID, [Year] DESC)
    INCLUDE (SportID, Result, Points, Brand, FullName);
GO

IF OBJECT_ID('dbo.RiderProfileWMXStatsSummary', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RiderProfileWMXStatsSummary (
        RiderID INT NOT NULL,
        [Year] INT NULL,
        SportID INT NOT NULL,
        Class NVARCHAR(10) NOT NULL,
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

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.RiderProfileWMXStatsSummary') AND name = 'IX_RiderProfileWMXStatsSummary_Rider')
    CREATE NONCLUSTERED INDEX IX_RiderProfileWMXStatsSummary_Rider
    ON dbo.RiderProfileWMXStatsSummary (RiderID, [Year], Brand);
GO

IF OBJECT_ID('dbo.SeasonWMXOverallSummary', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.SeasonWMXOverallSummary (
        [Year] INT NOT NULL,
        SportID INT NOT NULL,
        RiderID INT NOT NULL,
        FullName NVARCHAR(255) NULL,
        Brand NVARCHAR(100) NULL,
        Starts INT NOT NULL,
        Wins INT NOT NULL,
        Podiums INT NOT NULL,
        Top5 INT NOT NULL,
        Top10 INT NOT NULL,
        BestOverall INT NULL,
        AvgOverall DECIMAL(10,2) NULL,
        Holeshots INT NOT NULL,
        AvgStart DECIMAL(10,2) NULL,
        Points INT NOT NULL,
        RefreshedAt DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.SeasonWMXOverallSummary') AND name = 'IX_SeasonWMXOverallSummary_Season')
    CREATE NONCLUSTERED INDEX IX_SeasonWMXOverallSummary_Season
    ON dbo.SeasonWMXOverallSummary ([Year], RiderID);
GO

IF OBJECT_ID('dbo.SeasonWMXMotoQualSummary', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.SeasonWMXMotoQualSummary (
        [Year] INT NOT NULL,
        SportID INT NOT NULL,
        RiderID INT NOT NULL,
        FullName NVARCHAR(255) NULL,
        MotoWins INT NOT NULL,
        MotoPodiums INT NOT NULL,
        BestMoto INT NULL,
        AvgMoto DECIMAL(10,2) NULL,
        Poles INT NOT NULL,
        QualStarts INT NOT NULL,
        AvgQual DECIMAL(10,2) NULL,
        ConsiWins INT NOT NULL,
        RefreshedAt DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.SeasonWMXMotoQualSummary') AND name = 'IX_SeasonWMXMotoQualSummary_Season')
    CREATE NONCLUSTERED INDEX IX_SeasonWMXMotoQualSummary_Season
    ON dbo.SeasonWMXMotoQualSummary ([Year], RiderID);
GO

CREATE OR ALTER PROCEDURE dbo.RefreshWMXSummaries
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRANSACTION;

    DELETE FROM dbo.RiderProfileWMXStatsSummary;

    WITH Base AS (
        SELECT
            wo.riderid AS RiderID,
            rt.[Year],
            wo.Brand,
            wo.Result,
            wo.Moto1,
            wo.Moto2,
            wo.Moto3,
            wo.Points,
            wo.LapsLed,
            wo.M1_Laps_Led,
            wo.M2_Laps_Led,
            wo.Holeshot,
            CASE
                WHEN wo.M1_Start IS NOT NULL AND wo.M2_Start IS NOT NULL THEN (wo.M1_Start + wo.M2_Start) / 2.0
                WHEN wo.M1_Start IS NOT NULL THEN wo.M1_Start
                WHEN wo.M2_Start IS NOT NULL THEN wo.M2_Start
            END AS AvgStartRace
        FROM dbo.WMX_OVERALLS wo
        JOIN dbo.Race_Table rt ON rt.RaceID = wo.raceid
        WHERE rt.SportID = 4
    ),
    Expanded AS (
        SELECT Base.*, moto.BestMoto
        FROM Base
        CROSS APPLY (
            SELECT MIN(value.Result) AS BestMoto
            FROM (VALUES (Moto1), (Moto2), (Moto3)) value(Result)
        ) moto
    ),
    Rollups AS (
        SELECT RiderID, [Year], Brand FROM Expanded
        UNION
        SELECT RiderID, NULL, NULL FROM Expanded
    )
    INSERT dbo.RiderProfileWMXStatsSummary (
        RiderID, [Year], SportID, Class, Brand, Starts, BestOverall, BestMoto,
        AvgOverallFinish, AvgMotoFinish, AvgMoto1Finish, AvgMoto2Finish,
        Top10s, Top10Pct, Top5s, Top5Pct, Podiums, PodiumPct, Wins, WinPct,
        LapsLed, Holeshots, AvgStart, TotalPoints
    )
    SELECT
        grouping_row.RiderID,
        grouping_row.[Year],
        4,
        'WMX',
        grouping_row.Brand,
        COUNT(*),
        MIN(base.Result),
        MIN(base.BestMoto),
        CAST(ROUND(AVG(CAST(base.Result AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)),
        CAST(ROUND(
            SUM(COALESCE(CAST(base.Moto1 AS DECIMAL(10,2)), 0)) +
            SUM(COALESCE(CAST(base.Moto2 AS DECIMAL(10,2)), 0)) +
            SUM(COALESCE(CAST(base.Moto3 AS DECIMAL(10,2)), 0)), 2
        ) / NULLIF(
            SUM(CASE WHEN base.Moto1 IS NOT NULL THEN 1 ELSE 0 END) +
            SUM(CASE WHEN base.Moto2 IS NOT NULL THEN 1 ELSE 0 END) +
            SUM(CASE WHEN base.Moto3 IS NOT NULL THEN 1 ELSE 0 END), 0
        ) AS DECIMAL(10,2)),
        CAST(ROUND(AVG(CAST(base.Moto1 AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)),
        CAST(ROUND(AVG(CAST(base.Moto2 AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)),
        SUM(CASE WHEN base.Result <= 10 THEN 1 ELSE 0 END),
        CAST(ROUND(100.0 * SUM(CASE WHEN base.Result <= 10 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)),
        SUM(CASE WHEN base.Result <= 5 THEN 1 ELSE 0 END),
        CAST(ROUND(100.0 * SUM(CASE WHEN base.Result <= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)),
        SUM(CASE WHEN base.Result <= 3 THEN 1 ELSE 0 END),
        CAST(ROUND(100.0 * SUM(CASE WHEN base.Result <= 3 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)),
        SUM(CASE WHEN base.Result = 1 THEN 1 ELSE 0 END),
        CAST(ROUND(100.0 * SUM(CASE WHEN base.Result = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)),
        SUM(COALESCE(CAST(base.LapsLed AS INT), COALESCE(CAST(base.M1_Laps_Led AS INT), 0) + COALESCE(CAST(base.M2_Laps_Led AS INT), 0))),
        SUM(COALESCE(CAST(base.Holeshot AS INT), 0)),
        CAST(ROUND(AVG(base.AvgStartRace), 2) AS DECIMAL(10,2)),
        SUM(COALESCE(CAST(base.Points AS INT), 0))
    FROM Rollups grouping_row
    JOIN Expanded base
      ON base.RiderID = grouping_row.RiderID
     AND (grouping_row.[Year] IS NULL OR base.[Year] = grouping_row.[Year])
     AND (grouping_row.[Year] IS NULL OR ISNULL(base.Brand, '') = ISNULL(grouping_row.Brand, ''))
    GROUP BY grouping_row.RiderID, grouping_row.[Year], grouping_row.Brand;

    DELETE FROM dbo.SeasonWMXOverallSummary;

    WITH Base AS (
        SELECT rt.[Year], wo.raceid AS RaceID, wo.riderid AS RiderID,
               wo.FullName, wo.Brand, wo.Result, wo.Points
        FROM dbo.WMX_OVERALLS wo
        JOIN dbo.Race_Table rt ON rt.RaceID = wo.raceid
        WHERE rt.SportID = 4
    ),
    StartHoleshotRows AS (
        SELECT rt.[Year], wm.riderid AS RiderID, wm.[Start], wm.Holeshot
        FROM dbo.WMX_MOTOS wm
        JOIN dbo.Race_Table rt ON rt.RaceID = wm.raceid
        WHERE rt.SportID = 4

        UNION ALL

        SELECT rt.[Year], wo.riderid, fallback.[Start], fallback.Holeshot
        FROM dbo.WMX_OVERALLS wo
        JOIN dbo.Race_Table rt ON rt.RaceID = wo.raceid
        CROSS APPLY (VALUES
            (wo.M1_Start, COALESCE(wo.M1_Holeshot, wo.Holeshot)),
            (wo.M2_Start, wo.M2_Holeshot)
        ) fallback([Start], Holeshot)
        WHERE rt.SportID = 4
          AND NOT EXISTS (
              SELECT 1 FROM dbo.WMX_MOTOS wm
              WHERE wm.raceid = wo.raceid AND wm.riderid = wo.riderid
          )
          AND (fallback.[Start] IS NOT NULL OR fallback.Holeshot IS NOT NULL)
    ),
    StartHoleshotStats AS (
        SELECT [Year], RiderID,
               SUM(COALESCE(CAST(Holeshot AS INT), 0)) AS Holeshots,
               CAST(AVG(CAST([Start] AS DECIMAL(10,2))) AS DECIMAL(10,2)) AS AvgStart
        FROM StartHoleshotRows
        GROUP BY [Year], RiderID
    ),
    OverallStats AS (
        SELECT [Year], RiderID, MAX(FullName) AS FullName, MAX(Brand) AS Brand, COUNT(*) AS Starts,
               SUM(CASE WHEN Result = 1 THEN 1 ELSE 0 END) AS Wins,
               SUM(CASE WHEN Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
               SUM(CASE WHEN Result <= 5 THEN 1 ELSE 0 END) AS Top5,
               SUM(CASE WHEN Result <= 10 THEN 1 ELSE 0 END) AS Top10,
               MIN(Result) AS BestOverall,
               CAST(AVG(CAST(Result AS FLOAT)) AS DECIMAL(10,2)) AS AvgOverall,
               SUM(COALESCE(Points, 0)) AS Points
        FROM Base
        GROUP BY [Year], RiderID
    )
    INSERT dbo.SeasonWMXOverallSummary (
        [Year], SportID, RiderID, FullName, Brand, Starts, Wins, Podiums, Top5, Top10,
        BestOverall, AvgOverall, Holeshots, AvgStart, Points
    )
    SELECT overall.[Year], 4, overall.RiderID, overall.FullName, overall.Brand,
           overall.Starts, overall.Wins, overall.Podiums, overall.Top5, overall.Top10,
           overall.BestOverall, overall.AvgOverall,
           COALESCE(session_stats.Holeshots, 0), session_stats.AvgStart, overall.Points
    FROM OverallStats overall
    LEFT JOIN StartHoleshotStats session_stats
      ON session_stats.[Year] = overall.[Year]
     AND session_stats.RiderID = overall.RiderID;

    DELETE FROM dbo.SeasonWMXMotoQualSummary;

    WITH RiderBase AS (
        SELECT DISTINCT rt.[Year], wo.riderid AS RiderID, wo.FullName
        FROM dbo.WMX_OVERALLS wo JOIN dbo.Race_Table rt ON rt.RaceID = wo.raceid WHERE rt.SportID = 4
        UNION
        SELECT DISTINCT rt.[Year], wq.riderid, wq.FullName
        FROM dbo.WMX_QUAL wq JOIN dbo.Race_Table rt ON rt.RaceID = wq.raceid WHERE rt.SportID = 4
    ),
    Motos AS (
        SELECT rt.[Year], wm.riderid AS RiderID, wm.Result
        FROM dbo.WMX_MOTOS wm
        JOIN dbo.Race_Table rt ON rt.RaceID = wm.raceid
        WHERE rt.SportID = 4 AND wm.Result IS NOT NULL

        UNION ALL

        SELECT rt.[Year], wo.riderid AS RiderID, valueset.Result
        FROM dbo.WMX_OVERALLS wo
        JOIN dbo.Race_Table rt ON rt.RaceID = wo.raceid
        CROSS APPLY (VALUES (wo.Moto1), (wo.Moto2), (wo.Moto3)) valueset(Result)
        WHERE rt.SportID = 4
          AND valueset.Result IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM dbo.WMX_MOTOS wm
              WHERE wm.raceid = wo.raceid AND wm.riderid = wo.riderid
          )
    ),
    MotoStats AS (
        SELECT [Year], RiderID,
               SUM(CASE WHEN Result = 1 THEN 1 ELSE 0 END) AS MotoWins,
               SUM(CASE WHEN Result <= 3 THEN 1 ELSE 0 END) AS MotoPodiums,
               MIN(Result) AS BestMoto,
               CAST(AVG(CAST(Result AS FLOAT)) AS DECIMAL(10,2)) AS AvgMoto
        FROM Motos GROUP BY [Year], RiderID
    ),
    QualStats AS (
        SELECT rt.[Year], wq.riderid AS RiderID, COUNT(*) AS QualStarts,
               SUM(CASE WHEN wq.Result = 1 THEN 1 ELSE 0 END) AS Poles,
               CAST(AVG(CAST(wq.Result AS FLOAT)) AS DECIMAL(10,2)) AS AvgQual
        FROM dbo.WMX_QUAL wq JOIN dbo.Race_Table rt ON rt.RaceID = wq.raceid
        WHERE rt.SportID = 4 GROUP BY rt.[Year], wq.riderid
    )
    INSERT dbo.SeasonWMXMotoQualSummary (
        [Year], SportID, RiderID, FullName, MotoWins, MotoPodiums, BestMoto,
        AvgMoto, Poles, QualStarts, AvgQual, ConsiWins
    )
    SELECT rb.[Year], 4, rb.RiderID, MAX(rb.FullName),
           COALESCE(m.MotoWins, 0), COALESCE(m.MotoPodiums, 0), m.BestMoto, m.AvgMoto,
           COALESCE(q.Poles, 0), COALESCE(q.QualStarts, 0), q.AvgQual, 0
    FROM RiderBase rb
    LEFT JOIN MotoStats m ON m.[Year] = rb.[Year] AND m.RiderID = rb.RiderID
    LEFT JOIN QualStats q ON q.[Year] = rb.[Year] AND q.RiderID = rb.RiderID
    GROUP BY rb.[Year], rb.RiderID, m.MotoWins, m.MotoPodiums, m.BestMoto, m.AvgMoto,
             q.Poles, q.QualStarts, q.AvgQual;

    COMMIT TRANSACTION;
END;
GO

EXEC dbo.RefreshWMXSummaries;
GO
