# Example map format
This is a simple example map format.

It uses Spatialite as data storage.

## Layout

### Create statements
`4326` refers to the WGS84 coordinate system. https://epsg.io/4326
```sql
SELECT InitSpatialMetaData(1);

CREATE TABLE nodes (id INTEGER PRIMARY KEY AUTOINCREMENT);
SELECT AddGeometryColumn('nodes', 'coord', 4326, 'POINT', 2, 1);

CREATE TABLE lines (startnode INT, endnode INT, frc INT, fow INT);
SELECT AddGeometryColumn('lines', 'path', 4326, 'LINESTRING', 2, 1);
```
### Nodes
Nodes are objects with only a geo location attribute.

They can be displayed like this:
```sql
SELECT id, X(coord), Y(coord) FROM nodes;
```
### Lines
A line connects two distinct nodes.
It has OpenLR line attributes like FRC and FOW.

It has also a column containing the exact path geometry.
