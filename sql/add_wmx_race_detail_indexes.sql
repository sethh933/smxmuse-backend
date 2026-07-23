SET NOCOUNT ON;

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
