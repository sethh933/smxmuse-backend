SET NOCOUNT ON;
GO

IF OBJECT_ID('dbo.SMX_POINTS_STANDINGS', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.SMX_POINTS_STANDINGS (
        SMXStandingsID INT IDENTITY(1,1) NOT NULL,
        [Year] INT NOT NULL,
        ClassID INT NOT NULL,
        RiderID INT NOT NULL,
        FullName NVARCHAR(100) NOT NULL,
        Result INT NULL,
        Points INT NULL,
        Brand NVARCHAR(100) NULL,
        CONSTRAINT PK_SMX_POINTS_STANDINGS PRIMARY KEY CLUSTERED (SMXStandingsID),
        CONSTRAINT UQ_SMX_FinalStandings UNIQUE ([Year], ClassID, RiderID)
    );
END;
GO

CREATE OR ALTER VIEW dbo.vw_SMX_RunningStandings AS
WITH ClassRaces AS (
    SELECT
        rt.RaceID,
        rt.[Year],
        so.ClassID,
        rt.Round AS OverallRound,
        rt.RaceDate,
        DENSE_RANK() OVER (
            PARTITION BY rt.[Year], so.ClassID
            ORDER BY rt.RaceDate
        ) AS ClassRound
    FROM dbo.Race_Table rt
    JOIN dbo.SMX_OVERALLS so
        ON so.RaceID = rt.RaceID
    WHERE rt.SportID = 3
),
DistinctClassRaces AS (
    SELECT DISTINCT
        RaceID,
        [Year],
        ClassID,
        OverallRound,
        RaceDate,
        ClassRound
    FROM ClassRaces
),
Riders AS (
    SELECT DISTINCT
        so.RiderID,
        so.FullName,
        rt.[Year],
        so.ClassID
    FROM dbo.SMX_OVERALLS so
    JOIN dbo.Race_Table rt
        ON rt.RaceID = so.RaceID
    WHERE rt.SportID = 3
),
RiderRounds AS (
    SELECT
        r.RiderID,
        r.FullName,
        r.[Year],
        r.ClassID,
        cr.ClassRound,
        cr.OverallRound,
        cr.RaceID,
        cr.RaceDate
    FROM Riders r
    JOIN DistinctClassRaces cr
        ON r.[Year] = cr.[Year]
       AND r.ClassID = cr.ClassID
),
RacePoints AS (
    SELECT
        so.RiderID,
        rt.[Year],
        so.ClassID,
        rt.RaceID,
        ISNULL(so.Points, 0) AS Points
    FROM dbo.SMX_OVERALLS so
    JOIN dbo.Race_Table rt
        ON rt.RaceID = so.RaceID
    WHERE rt.SportID = 3
),
Joined AS (
    SELECT
        rr.RiderID,
        rr.FullName,
        rr.[Year],
        rr.ClassID,
        rr.ClassRound,
        rr.OverallRound,
        rr.RaceID,
        rr.RaceDate,
        ISNULL(rp.Points, 0) AS Points
    FROM RiderRounds rr
    LEFT JOIN RacePoints rp
        ON rr.RiderID = rp.RiderID
       AND rr.[Year] = rp.[Year]
       AND rr.ClassID = rp.ClassID
       AND rr.RaceID = rp.RaceID
),
Cumulative AS (
    SELECT
        RiderID,
        FullName,
        [Year],
        ClassID,
        ClassRound,
        OverallRound,
        RaceID,
        RaceDate,
        SUM(Points) OVER (
            PARTITION BY RiderID, [Year], ClassID
            ORDER BY ClassRound
        ) AS RunningPoints
    FROM Joined
),
AdjustmentTotals AS (
    SELECT
        RiderID,
        SeasonYear AS [Year],
        ClassID,
        Round AS ClassRound,
        SUM(AdjustmentPoints) AS AdjustmentPoints
    FROM dbo.PointsAdjustments
    WHERE SportID = 3
    GROUP BY RiderID, SeasonYear, ClassID, Round
)
SELECT
    c.RiderID,
    c.FullName,
    c.[Year],
    c.ClassID,
    c.ClassRound,
    c.OverallRound,
    c.RaceID,
    c.RaceDate,
    c.RunningPoints,
    ISNULL(ar.AdjustmentPoints, 0) AS AdjustmentPoints,
    c.RunningPoints + ISNULL(ar.AdjustmentPoints, 0) AS TotalPoints,
    RANK() OVER (
        PARTITION BY c.[Year], c.ClassID, c.ClassRound
        ORDER BY c.RunningPoints + ISNULL(ar.AdjustmentPoints, 0) DESC
    ) AS ChampionshipPosition
FROM Cumulative c
OUTER APPLY (
    SELECT SUM(a.AdjustmentPoints) AS AdjustmentPoints
    FROM AdjustmentTotals a
    WHERE a.RiderID = c.RiderID
      AND a.[Year] = c.[Year]
      AND a.ClassID = c.ClassID
      AND a.ClassRound <= c.ClassRound
) ar;
GO

WITH SMX_MaxRound AS (
    SELECT
        [Year],
        ClassID,
        MAX(ClassRound) AS MaxRound
    FROM dbo.vw_SMX_RunningStandings
    GROUP BY [Year], ClassID
),
SMX_Final AS (
    SELECT
        s.[Year],
        s.ClassID,
        s.RiderID,
        s.FullName,
        s.ChampionshipPosition,
        s.TotalPoints,
        ROW_NUMBER() OVER (
            PARTITION BY s.[Year], s.ClassID, s.RiderID
            ORDER BY s.ChampionshipPosition
        ) AS rn
    FROM dbo.vw_SMX_RunningStandings s
    JOIN SMX_MaxRound mr
        ON s.[Year] = mr.[Year]
       AND s.ClassID = mr.ClassID
       AND s.ClassRound = mr.MaxRound
),
BrandDedup AS (
    SELECT DISTINCT
        rt.[Year],
        so.ClassID,
        so.RiderID,
        so.Brand
    FROM dbo.SMX_OVERALLS so
    JOIN dbo.Race_Table rt
        ON rt.RaceID = so.RaceID
    WHERE rt.SportID = 3
)
MERGE dbo.SMX_POINTS_STANDINGS AS target
USING (
    SELECT
        s.[Year],
        s.ClassID,
        s.RiderID,
        s.FullName,
        s.ChampionshipPosition AS Result,
        s.TotalPoints AS Points,
        CASE
            WHEN COUNT(DISTINCT CASE WHEN b.Brand IS NOT NULL THEN b.Brand END) = 1
                THEN MAX(b.Brand)
            ELSE STRING_AGG(CASE WHEN b.Brand IS NOT NULL THEN b.Brand END, ', ')
        END AS Brand
    FROM SMX_Final s
    LEFT JOIN BrandDedup b
        ON b.RiderID = s.RiderID
       AND b.[Year] = s.[Year]
       AND b.ClassID = s.ClassID
    WHERE s.rn = 1
    GROUP BY
        s.[Year],
        s.ClassID,
        s.RiderID,
        s.FullName,
        s.ChampionshipPosition,
        s.TotalPoints
) AS source
ON target.[Year] = source.[Year]
   AND target.ClassID = source.ClassID
   AND target.RiderID = source.RiderID
WHEN MATCHED THEN
    UPDATE SET
        FullName = source.FullName,
        Result = source.Result,
        Points = source.Points,
        Brand = source.Brand
WHEN NOT MATCHED THEN
    INSERT ([Year], ClassID, RiderID, FullName, Result, Points, Brand)
    VALUES (source.[Year], source.ClassID, source.RiderID, source.FullName, source.Result, source.Points, source.Brand);
GO
