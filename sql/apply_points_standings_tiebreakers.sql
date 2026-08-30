/* Keep persisted championship positions aligned with the website tiebreak rules. */

WITH MotoFinishes AS (
    SELECT rt.[Year], mo.ClassID, mo.RiderID, finish.MotoNumber,
           CAST(finish.Result AS INT) AS FinishResult, rt.RaceDate, mo.RaceID
    FROM dbo.MX_OVERALLS mo
    JOIN dbo.Race_Table rt ON rt.RaceID = mo.RaceID
    CROSS APPLY (VALUES (1, mo.Moto1), (2, mo.Moto2)) finish(MotoNumber, Result)
    WHERE finish.Result IS NOT NULL AND finish.Result > 0
),
FinishPositions AS (
    SELECT DISTINCT [Year], ClassID, FinishResult FROM MotoFinishes
),
FinishCounts AS (
    SELECT [Year], ClassID, RiderID, FinishResult, COUNT(*) AS FinishCount
    FROM MotoFinishes
    GROUP BY [Year], ClassID, RiderID, FinishResult
),
TiebreakKeys AS (
    SELECT s.[Year], s.ClassID, s.RiderID,
           STRING_AGG(
               CAST(RIGHT('00000' + CAST(COALESCE(fc.FinishCount, 0) AS VARCHAR(5)), 5) AS VARCHAR(MAX)),
               ''
           ) WITHIN GROUP (ORDER BY fp.FinishResult) AS FinishCountKey
    FROM dbo.MX_POINTS_STANDINGS s
    JOIN FinishPositions fp ON fp.[Year] = s.[Year] AND fp.ClassID = s.ClassID
    LEFT JOIN FinishCounts fc
      ON fc.[Year] = s.[Year] AND fc.ClassID = s.ClassID
     AND fc.RiderID = s.RiderID AND fc.FinishResult = fp.FinishResult
    WHERE s.[Year] = YEAR(GETDATE())
    GROUP BY s.[Year], s.ClassID, s.RiderID
),
LastMoto AS (
    SELECT [Year], ClassID, RiderID, FinishResult,
           ROW_NUMBER() OVER (
               PARTITION BY [Year], ClassID, RiderID
               ORDER BY RaceDate DESC, RaceID DESC, MotoNumber DESC
           ) AS rn
    FROM MotoFinishes
),
Ranked AS (
    SELECT s.MXStandingsID,
           ROW_NUMBER() OVER (
               PARTITION BY s.[Year], s.ClassID
               ORDER BY s.Points DESC, tk.FinishCountKey DESC,
                        lm.FinishResult ASC, s.RiderID ASC
           ) AS CorrectResult
    FROM dbo.MX_POINTS_STANDINGS s
    LEFT JOIN TiebreakKeys tk
      ON tk.[Year] = s.[Year] AND tk.ClassID = s.ClassID AND tk.RiderID = s.RiderID
    LEFT JOIN LastMoto lm
      ON lm.[Year] = s.[Year] AND lm.ClassID = s.ClassID
     AND lm.RiderID = s.RiderID AND lm.rn = 1
    WHERE s.[Year] = YEAR(GETDATE())
)
UPDATE standings
SET Result = ranked.CorrectResult
FROM dbo.MX_POINTS_STANDINGS standings
JOIN Ranked ranked ON ranked.MXStandingsID = standings.MXStandingsID;
GO

WITH MotoFinishes AS (
    SELECT rt.[Year], CAST(4 AS INT) AS SportID, wo.RiderID, finish.MotoNumber,
           CAST(finish.Result AS INT) AS FinishResult, rt.RaceDate, wo.RaceID
    FROM dbo.WMX_OVERALLS wo
    JOIN dbo.Race_Table rt ON rt.RaceID = wo.RaceID
    CROSS APPLY (VALUES
        (1, wo.Moto1), (2, wo.Moto2), (3, wo.Moto3)
    ) finish(MotoNumber, Result)
    WHERE rt.SportID = 4 AND finish.Result IS NOT NULL AND finish.Result > 0
),
FinishPositions AS (
    SELECT DISTINCT [Year], SportID, FinishResult FROM MotoFinishes
),
FinishCounts AS (
    SELECT [Year], SportID, RiderID, FinishResult, COUNT(*) AS FinishCount
    FROM MotoFinishes
    GROUP BY [Year], SportID, RiderID, FinishResult
),
TiebreakKeys AS (
    SELECT s.[Year], s.SportID, s.RiderID,
           STRING_AGG(
               CAST(RIGHT('00000' + CAST(COALESCE(fc.FinishCount, 0) AS VARCHAR(5)), 5) AS VARCHAR(MAX)),
               ''
           ) WITHIN GROUP (ORDER BY fp.FinishResult) AS FinishCountKey
    FROM dbo.WMX_POINTS_STANDINGS s
    JOIN FinishPositions fp ON fp.[Year] = s.[Year] AND fp.SportID = s.SportID
    LEFT JOIN FinishCounts fc
      ON fc.[Year] = s.[Year] AND fc.SportID = s.SportID
     AND fc.RiderID = s.RiderID AND fc.FinishResult = fp.FinishResult
    WHERE s.[Year] = YEAR(GETDATE())
    GROUP BY s.[Year], s.SportID, s.RiderID
),
LastMoto AS (
    SELECT [Year], SportID, RiderID, FinishResult,
           ROW_NUMBER() OVER (
               PARTITION BY [Year], SportID, RiderID
               ORDER BY RaceDate DESC, RaceID DESC, MotoNumber DESC
           ) AS rn
    FROM MotoFinishes
),
Ranked AS (
    SELECT s.WMXStandingsID,
           ROW_NUMBER() OVER (
               PARTITION BY s.[Year], s.SportID
               ORDER BY s.Points DESC, tk.FinishCountKey DESC,
                        lm.FinishResult ASC, s.RiderID ASC
           ) AS CorrectResult
    FROM dbo.WMX_POINTS_STANDINGS s
    LEFT JOIN TiebreakKeys tk
      ON tk.[Year] = s.[Year] AND tk.SportID = s.SportID AND tk.RiderID = s.RiderID
    LEFT JOIN LastMoto lm
      ON lm.[Year] = s.[Year] AND lm.SportID = s.SportID
     AND lm.RiderID = s.RiderID AND lm.rn = 1
    WHERE s.[Year] = YEAR(GETDATE())
)
UPDATE standings
SET Result = ranked.CorrectResult
FROM dbo.WMX_POINTS_STANDINGS standings
JOIN Ranked ranked ON ranked.WMXStandingsID = standings.WMXStandingsID;
GO
