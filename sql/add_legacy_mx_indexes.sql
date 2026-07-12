IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.MX_QUAL_RACES')
      AND name = 'IX_MX_QUAL_RACES_RiderRaceClass'
)
CREATE NONCLUSTERED INDEX IX_MX_QUAL_RACES_RiderRaceClass
ON dbo.MX_QUAL_RACES (riderid, raceid, classid)
INCLUDE (Result, Brand, qualtype, qual, FullName, Interval);

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.MX_QUAL_RACES')
      AND name = 'IX_MX_QUAL_RACES_RaceClassType'
)
CREATE NONCLUSTERED INDEX IX_MX_QUAL_RACES_RaceClassType
ON dbo.MX_QUAL_RACES (raceid, classid, qualtype, qual)
INCLUDE (Result, riderid, FullName, Brand, Interval);

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.MX_QUAL_OLD_FORMAT')
      AND name = 'IX_MX_QUAL_OLD_FORMAT_RiderRaceClass'
)
CREATE NONCLUSTERED INDEX IX_MX_QUAL_OLD_FORMAT_RiderRaceClass
ON dbo.MX_QUAL_OLD_FORMAT (riderid, raceid, classid)
INCLUDE (Result, Brand, [Day], FullName, BestLap);

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.MX_QUAL_OLD_FORMAT')
      AND name = 'IX_MX_QUAL_OLD_FORMAT_RaceClassDay'
)
CREATE NONCLUSTERED INDEX IX_MX_QUAL_OLD_FORMAT_RaceClassDay
ON dbo.MX_QUAL_OLD_FORMAT (raceid, classid, [Day])
INCLUDE (Result, riderid, FullName, Brand, BestLap);

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.MX_CONSIS_OLD_FORMAT')
      AND name = 'IX_MX_CONSIS_OLD_FORMAT_RiderRaceClass'
)
CREATE NONCLUSTERED INDEX IX_MX_CONSIS_OLD_FORMAT_RiderRaceClass
ON dbo.MX_CONSIS_OLD_FORMAT (riderid, raceid, classid)
INCLUDE (Result, Brand, consitype, FullName, Interval);

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.MX_CONSIS_OLD_FORMAT')
      AND name = 'IX_MX_CONSIS_OLD_FORMAT_RaceClassType'
)
CREATE NONCLUSTERED INDEX IX_MX_CONSIS_OLD_FORMAT_RaceClassType
ON dbo.MX_CONSIS_OLD_FORMAT (raceid, classid, consitype)
INCLUDE (Result, riderid, FullName, Brand, Interval);
