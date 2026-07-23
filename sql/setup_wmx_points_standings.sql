SET NOCOUNT ON;
GO

IF OBJECT_ID('dbo.WMX_POINTS_STANDINGS', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.WMX_POINTS_STANDINGS (
        WMXStandingsID INT IDENTITY(1,1) NOT NULL,
        [Year] INT NOT NULL,
        SportID INT NOT NULL CONSTRAINT DF_WMX_POINTS_STANDINGS_SportID DEFAULT (4),
        RiderID INT NOT NULL,
        FullName NVARCHAR(100) NOT NULL,
        Result INT NULL,
        Points INT NULL,
        Brand NVARCHAR(100) NULL,
        CONSTRAINT PK_WMX_POINTS_STANDINGS PRIMARY KEY CLUSTERED (WMXStandingsID),
        CONSTRAINT UQ_WMX_FinalStandings UNIQUE ([Year], SportID, RiderID),
        CONSTRAINT CK_WMX_POINTS_STANDINGS_SportID CHECK (SportID = 4)
    );
END;
GO

CREATE OR ALTER VIEW dbo.vw_WMX_RunningStandings AS
WITH SeasonRaces AS (
    SELECT DISTINCT
        rt.RaceID,
        rt.[Year],
        CAST(4 AS INT) AS SportID,
        rt.Round AS OverallRound,
        rt.RaceDate
    FROM dbo.Race_Table rt
    JOIN dbo.WMX_OVERALLS wo
        ON wo.RaceID = rt.RaceID
    WHERE rt.SportID = 4
),
Riders AS (
    SELECT DISTINCT
        wo.RiderID,
        wo.FullName,
        rt.[Year],
        CAST(4 AS INT) AS SportID
    FROM dbo.WMX_OVERALLS wo
    JOIN dbo.Race_Table rt
        ON rt.RaceID = wo.RaceID
    WHERE rt.SportID = 4
),
RiderRounds AS (
    SELECT
        r.RiderID,
        r.FullName,
        r.[Year],
        r.SportID,
        sr.OverallRound,
        sr.RaceID,
        sr.RaceDate
    FROM Riders r
    JOIN SeasonRaces sr
        ON sr.[Year] = r.[Year]
       AND sr.SportID = r.SportID
),
RacePoints AS (
    SELECT
        wo.RiderID,
        rt.[Year],
        CAST(4 AS INT) AS SportID,
        rt.RaceID,
        ISNULL(wo.Points, 0) AS Points
    FROM dbo.WMX_OVERALLS wo
    JOIN dbo.Race_Table rt
        ON rt.RaceID = wo.RaceID
    WHERE rt.SportID = 4
),
Joined AS (
    SELECT
        rr.RiderID,
        rr.FullName,
        rr.[Year],
        rr.SportID,
        rr.OverallRound,
        rr.RaceID,
        rr.RaceDate,
        ISNULL(rp.Points, 0) AS Points
    FROM RiderRounds rr
    LEFT JOIN RacePoints rp
        ON rp.RiderID = rr.RiderID
       AND rp.[Year] = rr.[Year]
       AND rp.SportID = rr.SportID
       AND rp.RaceID = rr.RaceID
),
Cumulative AS (
    SELECT
        RiderID,
        FullName,
        [Year],
        SportID,
        OverallRound,
        RaceID,
        RaceDate,
        SUM(Points) OVER (
            PARTITION BY RiderID, [Year], SportID
            ORDER BY RaceDate, RaceID
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS RunningPoints
    FROM Joined
),
AdjustmentTotals AS (
    SELECT
        RiderID,
        SeasonYear AS [Year],
        SportID,
        Round AS OverallRound,
        SUM(AdjustmentPoints) AS AdjustmentPoints
    FROM dbo.PointsAdjustments
    WHERE SportID = 4
    GROUP BY RiderID, SeasonYear, SportID, Round
)
SELECT
    c.RiderID,
    c.FullName,
    c.[Year],
    c.SportID,
    c.OverallRound,
    c.RaceID,
    c.RaceDate,
    c.RunningPoints,
    ISNULL(adjustments.AdjustmentPoints, 0) AS AdjustmentPoints,
    c.RunningPoints + ISNULL(adjustments.AdjustmentPoints, 0) AS TotalPoints,
    RANK() OVER (
        PARTITION BY c.[Year], c.SportID, c.RaceID
        ORDER BY c.RunningPoints + ISNULL(adjustments.AdjustmentPoints, 0) DESC
    ) AS ChampionshipPosition
FROM Cumulative c
OUTER APPLY (
    SELECT SUM(a.AdjustmentPoints) AS AdjustmentPoints
    FROM AdjustmentTotals a
    WHERE a.RiderID = c.RiderID
      AND a.[Year] = c.[Year]
      AND a.SportID = c.SportID
      AND a.OverallRound <= c.OverallRound
) adjustments;
GO

WITH WMX_Final AS (
    SELECT
        standings.[Year],
        standings.SportID,
        standings.RiderID,
        standings.FullName,
        standings.ChampionshipPosition,
        standings.TotalPoints,
        ROW_NUMBER() OVER (
            PARTITION BY standings.[Year], standings.SportID, standings.RiderID
            ORDER BY standings.RaceDate DESC, standings.RaceID DESC
        ) AS rn
    FROM dbo.vw_WMX_RunningStandings standings
),
FinalRows AS (
    SELECT
        final.[Year],
        final.SportID,
        final.RiderID,
        final.FullName,
        final.TotalPoints
    FROM WMX_Final final
    WHERE final.rn = 1
),
OfficialFinal AS (
    SELECT
        final.[Year],
        final.SportID,
        final.RiderID,
        final.FullName,
        final.TotalPoints,
        DENSE_RANK() OVER (
            PARTITION BY final.[Year], final.SportID
            ORDER BY
                CASE WHEN champion.RiderID = final.RiderID THEN 1 ELSE 0 END DESC,
                final.TotalPoints DESC
        ) AS ChampionshipPosition
    FROM FinalRows final
    LEFT JOIN dbo.Champions champion
        ON champion.[Year] = final.[Year]
       AND champion.SportID = 4
       AND champion.RiderID = final.RiderID
),
BrandDedup AS (
    SELECT DISTINCT
        rt.[Year],
        CAST(4 AS INT) AS SportID,
        wo.RiderID,
        wo.Brand
    FROM dbo.WMX_OVERALLS wo
    JOIN dbo.Race_Table rt
        ON rt.RaceID = wo.RaceID
    WHERE rt.SportID = 4
)
MERGE dbo.WMX_POINTS_STANDINGS AS target
USING (
    SELECT
        final.[Year],
        final.SportID,
        final.RiderID,
        final.FullName,
        final.ChampionshipPosition AS Result,
        final.TotalPoints AS Points,
        CASE
            WHEN COUNT(DISTINCT CASE WHEN brands.Brand IS NOT NULL THEN brands.Brand END) = 1
                THEN MAX(brands.Brand)
            ELSE STRING_AGG(CASE WHEN brands.Brand IS NOT NULL THEN brands.Brand END, ', ')
        END AS Brand
    FROM OfficialFinal final
    LEFT JOIN BrandDedup brands
        ON brands.RiderID = final.RiderID
       AND brands.[Year] = final.[Year]
       AND brands.SportID = final.SportID
    GROUP BY
        final.[Year],
        final.SportID,
        final.RiderID,
        final.FullName,
        final.ChampionshipPosition,
        final.TotalPoints
) AS source
ON target.[Year] = source.[Year]
   AND target.SportID = source.SportID
   AND target.RiderID = source.RiderID
WHEN MATCHED THEN
    UPDATE SET
        FullName = source.FullName,
        Result = source.Result,
        Points = source.Points,
        Brand = source.Brand
WHEN NOT MATCHED THEN
    INSERT ([Year], SportID, RiderID, FullName, Result, Points, Brand)
    VALUES (source.[Year], source.SportID, source.RiderID, source.FullName, source.Result, source.Points, source.Brand);
GO
