"""example mapformat to test"""
import sqlite3
import os

from openlr_dereferencer.example_sqlite_map import SRID

INIT_SQL = f"""SELECT InitSpatialMetaData(1);

CREATE TABLE nodes (id INTEGER PRIMARY KEY);
SELECT AddGeometryColumn('nodes', 'coord', {SRID}, 'POINT', 2, 1);

CREATE TABLE lines (startnode INT, endnode INT, frc INT, fow INT);
SELECT AddGeometryColumn('lines', 'path', {SRID}, 'LINESTRING', 2, 1);

INSERT INTO nodes (id, coord) VALUES
    (0, MakePoint(13.41, 52.525, {SRID})),
    (1, MakePoint(13.413, 52.522, {SRID})),
    (2, MakePoint(13.414, 52.525, {SRID})),
    (3, MakePoint(13.4145, 52.529, {SRID})),
    (4, MakePoint(13.416, 52.525, {SRID})),
    (5, MakePoint(13.4175, 52.52, {SRID})),
    (6, MakePoint(13.418, 52.53, {SRID})),
    (7, MakePoint(13.4185, 52.525, {SRID})),
    (8, MakePoint(13.42, 52.527, {SRID})),
    (9, MakePoint(13.421, 52.53, {SRID})),
    (10, MakePoint(13.4215, 52.522, {SRID})),
    (11, MakePoint(13.425, 52.525, {SRID})),
    (12, MakePoint(13.427, 52.53, {SRID})),
    (13, MakePoint(13.429, 52.523, {SRID}));

INSERT INTO lines (startnode, endnode, frc, fow, path) VALUES
    (0, 2, 1, 3, ST_GeomFromText("LINESTRING(13.41 52.525, 13.413 52.522)", {SRID})),
    (1, 2, 2, 3, ST_GeomFromText("LINESTRING(13.413 52.522, 13.4145 52.529)", {SRID})),
    (2, 3, 2, 3, ST_GeomFromText("LINESTRING(13.414 52.525, 13.4145 52.529)", {SRID})),
    (3, 4, 2, 3, ST_GeomFromText("LINESTRING(13.4145 52.529, 13.416 52.525)", {SRID})),
    (2, 4, 1, 3, ST_GeomFromText("LINESTRING(13.414 52.525, 13.416 52.525)", {SRID})),
    (4, 5, 2, 3, ST_GeomFromText("LINESTRING(13.416 52.525, 13.4175 52.52)", {SRID})),
    (5, 7, 2, 3, ST_GeomFromText("LINESTRING(13.4175 52.52, 13.4185 52.525)", {SRID})),
    (4, 7, 1, 3, ST_GeomFromText("LINESTRING(13.416 52.525, 13.4185 52.525)", {SRID})),
    (7, 8, 2, 3, ST_GeomFromText("LINESTRING(13.4185 52.525, 13.42 52.527)", {SRID})),
    (8, 9, 2, 3, ST_GeomFromText("LINESTRING(13.42 52.527, 13.421 52.53)", {SRID})),
    (9, 6, 2, 3, ST_GeomFromText("LINESTRING(13.421 52.53, 13.418 52.53)", {SRID})),
    (6, 8, 2, 3, ST_GeomFromText("LINESTRING(13.418 52.53, 13.42 52.527)", {SRID})),
    (8, 11, 2, 3, ST_GeomFromText("LINESTRING(13.42 52.527, 13.425 52.525)", {SRID})),
    (7, 11, 1, 3, ST_GeomFromText("LINESTRING(13.4185 52.525, 13.425 52.525)", {SRID})),
    (10, 11, 2, 3, ST_GeomFromText("LINESTRING(13.4215 52.522, 13.425 52.525)", {SRID})),
    (11, 12, 2, 3, ST_GeomFromText("LINESTRING(13.425 52.525, 13.427 52.53)", {SRID})),
    (11, 13, 1, 3, ST_GeomFromText("LINESTRING(13.425 52.525, 13.429 52.523)", {SRID}));
"""

def setup_testdb(db_file: str):
    "Creates a sqlite DB with all the test data"
    conn = sqlite3.connect(db_file)
    conn.enable_load_extension(True)
    conn.load_extension('mod_spatialite.so')
    cur = conn.cursor()
    cur.executescript(INIT_SQL)
    conn.close()

def remove_db_file(db_file: str):
    "Removes the sqlite DB file, and does not raise when nonexistent"
    try:
        os.remove(db_file)
    except FileNotFoundError:
        pass
