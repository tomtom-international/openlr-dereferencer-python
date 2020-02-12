SELECT InitSpatialMetaData(1);

CREATE TABLE nodes (id INTEGER PRIMARY KEY AUTOINCREMENT);
SELECT AddGeometryColumn('nodes', 'coord', 4326, 'POINT', 2, 1);

CREATE TABLE lines (startnode INT, endnode INT, frc INT, fow INT);
SELECT AddGeometryColumn('lines', 'path', 4326, 'LINESTRING', 2, 1);

INSERT INTO nodes (coord) VALUES
    (MakePoint(13.41, 52.523, 4326)),
    (MakePoint(13.414, 52.521, 4326)),
    (MakePoint(13.416, 52.525, 4326)),
    (MakePoint(13.42, 52.521, 4326)),
    (MakePoint(13.424, 52.53, 4326)),
    (MakePoint(13.42, 52.528, 4326)),
    (MakePoint(13.427, 52.523, 4326)),
    (MakePoint(13.43, 52.521, 4326)),
    (MakePoint(13.4265, 52.52, 4326)),
    (MakePoint(13.4275, 52.526, 4326));