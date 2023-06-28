from itertools import pairwise
import logging
import argparse
import concurrent.futures

import osmnx as ox
import openlr
from openlr.locations import Coordinates, FRC, FOW
import pandas as pd
import geopandas as gpd
import numpy as np
import psycopg2
from sqlalchemy import text
from shapely.geometry import LineString
from tqdm import tqdm
from stl_general import database as db

import openlr_dereferencer
from openlr_dereferencer.maps.wgs84 import distance
from openlr_dereferencer.stl_osm_map import PostgresMapReader
from openlr_dereferencer.decoding.error import LRDecodeError

MAX_FRC = 5
OPENLR_LINES_TBL_NAME = "hollowell_cumberland_osm_openlr_lines"
OPENLR_NODES_TBL_NAME = "hollowell_cumberland_osm_openlr_nodes"
OUTPUT_TBL_NAME = "hollowell_cumberland_tt_osm_simp_crosswalk"
SCHEMA_NAME = "mag"
DB_NICKNAME = "dell4db"

# OLR dereferencers configs
SEARCH_RADIUS = 25
BEAR_DIST = 1  # tomtom has v short segs
MAX_BEAR_DEV = 100  # very generous but we don't expect to have many candidates
FOW_WEIGHT = 0  # we don't get FOW from TomTom at the moment
TOLERATED_DNP_DEV = 100  # tomtom has v short segs
CANDIDATE_THRESHOLD = 20  # tomtom has v short segs
REL_CANDIDATE_THRESHOLD = 0.1  # threshold should be relative to candidate segment length


def tt_seg_to_openlr_ref(linestr, frc=7, fow=0, lfrcnp=None):
    """Encode TomTom segment as OpenLR reference line location

    Args:
        linestr (_type_): _description_
        frc (int, optional): _description_. Defaults to 7.
        fow (int, optional): _description_. Defaults to 0.
        lfrcnp (_type_, optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """
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


def load_tomtom_segs(resume=False, max_frc=7, simplify=False, geom_col="geom"):
    conn = db.connect_db(
        host="dev-cem-01.streetlightdata.net", dbname="repo", user="postgres", port=6543, driver="sqlalchemy"
    )
    if simplify:
        geom_col = f"""st_makeline(st_startpoint({geom_col}), st_endpoint({geom_col})) as {geom_col}
        """

    query_str = f"""
    select
        segment_id,
        {geom_col},
        road_class
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
        line_ids integer[] NULL,
        osm_geometry public.geometry(linestring, 4326) NULL
    );
    CREATE INDEX {table_name}_geometry ON {schema_name}.{table_name} USING gist (osm_geometry);
    """
    conn = db.connect_db(nickname=db_nickname, driver="sqlalchemy")
    for query_str in query_text.split(";\n"):
        if query_str.strip() != "":
            db.execute_remote_query(conn, text(query_str), driver="sqlalchemy")
    conn.close()
    return


def match_segs(segments, config, observer):
    write_errs = []
    conn = db.connect_db(nickname="dell4db", driver="psycopg2")
    for seg in segments:
        observer = openlr_dereferencer.SimpleObserver() if observer else None
        olr_ref = tt_seg_to_openlr_ref(seg["geom"], frc=seg["road_class"])
        try:
            with PostgresMapReader(
                DB_NICKNAME, SCHEMA_NAME, OPENLR_LINES_TBL_NAME, OPENLR_NODES_TBL_NAME
            ) as mapreader:
                match = openlr_dereferencer.decode(
                    olr_ref,
                    mapreader,
                    observer,
                    config,
                )
                all_line_ids = []
                for line in match.lines:
                    all_line_ids.append(line.line_id)
                line_ids = list(set(all_line_ids))
                geom = match.internal_route.shape

        except LRDecodeError:
            line_ids = []
            geom = LineString()
        cur = conn.cursor()
        insert_str = f"insert into {SCHEMA_NAME}.{OUTPUT_TBL_NAME} values (%s, %s, %s)"
        try:
            cur.execute(insert_str, (seg["segment_id"], line_ids, geom.wkb))
            conn.commit()
        except psycopg2.DatabaseError:
            conn.rollback()
            write_errs.append(seg["segment_id"])
    conn.close()
    return write_errs


def run_matcher(simplify=False, max_frc=MAX_FRC, resume=False, observer=False, debug=False, batchsize=50):
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    if not resume:
        create_output_table(SCHEMA_NAME, OUTPUT_TBL_NAME, DB_NICKNAME)
    tt_segs = load_tomtom_segs(resume, max_frc=max_frc, simplify=simplify)
    config = openlr_dereferencer.Config(
        search_radius=SEARCH_RADIUS,
        bear_dist=BEAR_DIST,
        fow_weight=FOW_WEIGHT,
        tolerated_dnp_dev=TOLERATED_DNP_DEV,
        candidate_threshold=CANDIDATE_THRESHOLD,
        rel_candidate_threshold=REL_CANDIDATE_THRESHOLD,
        max_bear_deviation=MAX_BEAR_DEV,
    )

    # split routes into batches
    num_segs = tt_segs.shape[0]
    nbatches = int(np.ceil(num_segs / batchsize))
    seg_batches = np.array_split(tt_segs.to_records(), nbatches)
    num_batches = len(seg_batches)

    # run batches
    pbar = tqdm(total=num_batches)
    all_write_errs = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = []
        for batch in seg_batches:
            new_future = executor.submit(match_segs, batch, config, observer)
            futures.append(new_future)
        for result in concurrent.futures.as_completed(futures):
            write_errs = result.result()
            all_write_errs += write_errs
            pbar.update(n=1)
    return all_write_errs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--resume", action="store_true", help="Append results to existing output table.")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode.")
    parser.add_argument("-o", "--observer", action="store_true", help="Enable internal dereferencing observer.")
    parser.add_argument("-s", "--simplify", action="store_true", help="Simplify TomTom geometries.")
    parser.add_argument("-f", "--max_frc", action="store", help="Max TomTom FRC to process.", default=MAX_FRC)
    args = parser.parse_args()
    resume = args.resume
    debug = args.debug
    observer = args.observer if not debug else True
    simplify = args.simplify
    max_frc = args.max_frc
    write_errs = run_matcher(simplify, max_frc, resume, observer, debug)
