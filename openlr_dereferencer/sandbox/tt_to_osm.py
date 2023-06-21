from itertools import pairwise
import logging
import ast
import argparse

import osmnx as ox
import openlr
from openlr.locations import Coordinates, FRC, FOW
import pandas as pd
import geopandas as gpd
import psycopg2
from sqlalchemy import text
from geoalchemy2 import Geometry
from shapely.geometry import LineString
from tqdm import tqdm
from stl_general import database as db

import openlr_dereferencer
from openlr_dereferencer.maps.wgs84 import distance
from openlr_dereferencer.stl_osm_map import PostgresMapReader
from openlr_dereferencer.decoding.error import LRDecodeError

OPENLR_LINES_TBL_NAME = "hollowell_cumberland_osm_openlr_lines"
OPENLR_NODES_TBL_NAME = "hollowell_cumberland_osm_openlr_nodes"
OUTPUT_TBL_NAME = "hollowell_cumberland_tt_osm_crosswalk"
SCHEMA_NAME = "mag"
DB_NICKNAME = "dell4db"


def tt_seg_to_openlr_ref(linestr, frc=7, fow=0, lfrcnp=None):
    lfrcnp = frc if lfrcnp is None else lfrcnp
    coordinates = []
    for this_point, next_point in pairwise(linestr.coords):
        bearing = ox.bearing.calculate_bearing(this_point[1], this_point[0], next_point[1], next_point[0])
        dnp = distance(Coordinates(this_point[0], this_point[1]), Coordinates(next_point[0], next_point[1]))
        lrp = openlr.LocationReferencePoint(
            this_point[0], this_point[1], FRC(frc), FOW(fow), bearing, FRC(lfrcnp), dnp
        )
        coordinates.append(lrp)
    final_bearing = ox.bearing.calculate_bearing(next_point[1], next_point[0], this_point[1], this_point[0])
    final_lrp = openlr.LocationReferencePoint(
        next_point[0], next_point[1], FRC(frc), FOW(fow), final_bearing, FRC(lfrcnp), None
    )
    coordinates.append(final_lrp)
    line = openlr.LineLocationReference(coordinates, poffs=0, noffs=0)
    return line


def load_tomtom_segs(resume=False, max_frc=7):
    conn = db.connect_db(
        host="dev-cem-01.streetlightdata.net", dbname="repo", user="postgres", port=6543, driver="sqlalchemy"
    )

    query_str = f"""
    select *
    from cem_tt_pipeline.tt_segments
    where layer_id = 'hollowell_cumberland_2022_12'
    and road_class <= {max_frc}
    """
    tt_segs = gpd.read_postgis(text(query_str), con=conn, crs="epsg:4326", coerce_float=False)
    conn.close()
    if resume:
        conn = db.connect_db("dell4db", driver="sqlalchemy")
        query_str = f"""
        select tt_seg_id
        from {SCHEMA_NAME}.{OUTPUT_TBL_NAME}
        """
        completed = pd.read_sql(text(query_str), con=conn)
        conn.close()
        tt_segs = tt_segs[~tt_segs["segment_id"].isin(completed["tt_seg_id"])]

    return tt_segs


def create_output_table(schema_name, table_name, db_nickname):
    query_text = f"""
    DROP TABLE if exists {schema_name}.{table_name};
    CREATE TABLE {schema_name}.{table_name} (
        tt_seg_id text NULL,
        way_ids text NULL,
        osm_geometry public.geometry(linestring, 4326) NULL,
    );
    CREATE INDEX {table_name}_geometry ON {schema_name}.{table_name} USING gist (osm_geometry);
    """
    conn = db.connect_db(nickname=db_nickname, driver="sqlalchemy")
    for query_str in query_text.split(";\n"):
        if query_str.strip() != "":
            db.execute_remote_query(conn, text(query_str), driver="sqlalchemy")
    return


def match_segs(resume=False, observer=False, debug=False):
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    if not resume:
        create_output_table(SCHEMA_NAME, OUTPUT_TBL_NAME, DB_NICKNAME)
    tt_segs = load_tomtom_segs(resume, max_frc=5)
    errs = []
    conn = db.connect_db(nickname="dell4db", driver="psycopg2")
    for seg in tqdm(tt_segs.to_records()):
        observer = openlr_dereferencer.SimpleObserver() if observer else None
        olr_ref = tt_seg_to_openlr_ref(seg["geom"], frc=seg["road_class"])
        my_config = openlr_dereferencer.Config(
            bear_dist=1,  # tomtom has v short segs
            fow_weight=0,  # we don't get FOW from TomTom at the moment
            tolerated_dnp_dev=1000,  # tomtom has v short segs
            candidate_threshold=20,  # tomtom has v short segs
            rel_candidate_threshold=0.1,  # threshold should be relative to candidate segment length
        )
        try:
            with PostgresMapReader(
                DB_NICKNAME, SCHEMA_NAME, OPENLR_LINES_TBL_NAME, OPENLR_NODES_TBL_NAME
            ) as mapreader:
                match = openlr_dereferencer.decode(
                    olr_ref,
                    mapreader,
                    observer,
                    my_config,
                )
                all_way_ids = []
                for lines in match.lines:
                    way_ids = ast.literal_eval(lines.way_id)
                    if isinstance(way_ids, int):
                        way_ids = [way_ids]
                    for way_id in way_ids:
                        all_way_ids.append(way_id)
                way_ids = list(set(all_way_ids))
                geom = match.internal_route.shape

        except LRDecodeError:
            way_ids = []
            geom = LineString()

        cur = conn.cursor()
        insert_str = f"insert into {SCHEMA_NAME}.{OUTPUT_TBL_NAME} values (%s, %s, %s)"
        try:
            cur.execute(insert_str, (seg["segment_id"], way_ids, geom.wkb))
            conn.commit()
        except psycopg2.DatabaseError:
            conn.rollback()
            errs.append(seg["segment_id"])

    return errs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--resume", action="store_true", help="Append results to existing output table.")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode.")
    parser.add_argument("-o", "--observer", action="store_true", help="Enable internal dereferencing observer.")
    args = parser.parse_args()
    resume = args.resume
    debug = args.debug
    observer = args.observer if not debug else True
    errs = match_segs(resume, observer, debug)
