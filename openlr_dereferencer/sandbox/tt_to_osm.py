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
from repoman.utils import stl_database as db

import openlr_dereferencer
from openlr_dereferencer.maps.wgs84 import distance
from openlr_dereferencer.stl_osm_map import PostgresMapReader
from openlr_dereferencer.decoding.error import LRDecodeError


PROJECT_ID = "at_7"
PROJECT_TBL_DB_NICKNAME = "dell4db"
PROJECTS_TBL_SCHEMA = "at_tomtom"
OLR_DB_NICKNAME = "dell4db"
OLR_SCHEMA_NAME = "at_tomtom"
TT_SEGS_SCHEMA_NAME = "at_tomtom"
TT_SEGS_TBL_NAME = f"tt_segments"
MAX_FRC = 7
BATCHSIZE = 5
FILTER_PROJ_BBOX = True
XWALK_TABLE_NAME_TEMPLATE = "{project_id}_tt_osm_crosswalk"
FULL_JOIN_TABLE_NAME_TEMPLATE = "{project_id}_tt_osm_full_outer_join"
OLR_LINES_TABLE_NAME_TEMPLATE = "{project_id}_osm_openlr_lines"

# OLR dereferencers configs
SEARCH_RADIUS = 25
BEAR_DIST = 1  # tomtom has v short segs
MAX_BEAR_DEV = 100  # very generous but we don't expect to have many candidates
FOW_WEIGHT = 0  # we don't get FOW from TomTom at the moment
TOLERATED_DNP_DEV = 100  # tomtom has v short segs
CANDIDATE_THRESHOLD = 20  # tomtom has v short segs
REL_CANDIDATE_THRESHOLD = 0.1  # threshold should be relative to candidate segment length


def create_full_outer_join_tbl(
    project_id=PROJECT_ID,
    db_nickname=OLR_DB_NICKNAME,
    output_schema=OLR_SCHEMA_NAME,
    olr_schema=OLR_SCHEMA_NAME,
    tt_schema=TT_SEGS_SCHEMA_NAME,
    tt_segs_tbl_name=TT_SEGS_TBL_NAME,
):
    olr_lines_table_name = OLR_LINES_TABLE_NAME_TEMPLATE.format(project_id=project_id)
    xwalk_table_name = XWALK_TABLE_NAME_TEMPLATE.format(project_id=project_id)
    match_output_tbl_name = FULL_JOIN_TABLE_NAME_TEMPLATE.format(project_id=project_id)
    outer_join_query_str = f"""
    drop table if exists {output_schema}.{xwalk_table_name};
    create table {output_schema}.{xwalk_table_name} as
    select
        segment_id as tt_seg_id,
        tt_frc,
        tt_geom,
        hcool.line_id as osm_line_id,
        hcool.frc as osm_frc,
        hcool.geometry as osm_geom,
        xtt.osm_geometry as matched_geom
    from (
        select
            segment_id,
            road_class as tt_frc,
            geom as tt_geom,
            unnest(case when line_ids <> '{{}}' then line_ids else '{{null}}' end) as line_id,
            osm_geometry
        FROM {output_schema}.{match_output_tbl_name} x
        right join {tt_schema}.{tt_segs_tbl_name} hcts
        on x.tt_seg_id = hcts.segment_id
    ) xtt
    full outer join {olr_schema}.{olr_lines_table_name} hcool
    on hcool.line_id = xtt.line_id;
    """
    conn = db.connect_db(nickname=db_nickname, driver="sqlalchemy")
    for query_str in outer_join_query_str.split(";\n"):
        if query_str.strip() != "":
            db.execute_remote_query(conn, text(query_str), driver="sqlalchemy")
    conn.close()

    tt_score_query = f"""
    with match_counts as (
        SELECT tt_seg_id, count(osm_line_id) > 0 as matched
        FROM {output_schema}.{xwalk_table_name}
        where tt_seg_id notnull
        and tt_frc <= 5
        group by 1
    )
    select matched, count(*)::float / (select count(*) from match_counts)
    from match_counts
    group by 1;
    """
    conn = db.connect_db(nickname=db_nickname, driver="sqlalchemy")
    res = pd.read_sql(text(tt_score_query), con=conn).to_dict(orient="records")
    print(res)
    conn.close()

    osm_score_query = f"""
    with match_counts as (
        SELECT osm_line_id, count(tt_seg_id) > 0 as matched
        FROM {output_schema}.{xwalk_table_name}
        where osm_line_id notnull
        and osm_frc <= 5
        group by 1
    )
    select matched, count(*)::float / (select count(*) from match_counts)
    from match_counts
    group by 1;
    """
    conn = db.connect_db(nickname=db_nickname, driver="sqlalchemy")
    res = pd.read_sql(text(osm_score_query), con=conn).to_dict(orient="records")
    print(res)
    conn.close()
    return


def get_proj_bbox(
    project_id=PROJECT_ID, db_nickname=PROJECT_TBL_DB_NICKNAME, db_schema=PROJECTS_TBL_SCHEMA, proj_tbl_name="projects"
):
    conn = db.connect_db(db_nickname, driver="sqlalchemy")
    query_str = f"""
    select *
    from {db_schema}.{proj_tbl_name}
    where project_id = '{project_id}'
    """
    proj_info = gpd.read_postgis(text(query_str), con=conn, crs="epsg:4326", geom_col="bounding_box")
    conn.close()
    return proj_info["bounding_box"].values[0]


def clip_segs_to_bbox(segs_gdf, bbox):
    """_summary_

    Args:
        segs_gdf (geopandas.GeoDataFrame):
        bbox (shapely.geometry.polygon.Polygon):
    """
    return segs_gdf[segs_gdf.intersects(bbox)]


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


def load_tomtom_segs(
    db_nickname,
    db_schema,
    table_name,
    output_db_nickname,
    output_schema,
    output_table_name,
    layer_id,
    resume,
    max_frc,
    simplify,
    geom_col="geom",
):
    conn = db.connect_db(db_nickname, driver="sqlalchemy")
    if simplify:
        geom_col = f"""st_makeline(st_startpoint({geom_col}), st_endpoint({geom_col})) as {geom_col}"""

    query_str = f"""
    select
        segment_id,
        {geom_col},
        road_class
    from {db_schema}.{table_name}
    where road_class <= {max_frc}
    """
    if layer_id:
        query_str += f" and layer_id = '{layer_id}'"
    tt_segs = gpd.read_postgis(text(query_str), con=conn, crs="epsg:4326", coerce_float=False)
    conn.close()
    if resume:
        print("Picking back up where we left off...")
        conn = db.connect_db(output_db_nickname, driver="sqlalchemy")
        query_str = f"""
        select tt_seg_id
        from {output_schema}.{output_table_name}
        """
        completed = pd.read_sql(text(query_str), con=conn)
        conn.close()
        tt_segs = tt_segs[~tt_segs["segment_id"].isin(completed["tt_seg_id"])]

    return tt_segs


def create_output_table(db_nickname, schema_name, table_name):
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
    return f"{schema_name}.{table_name}"


def match_segs(
    segments,
    config,
    observer,
    project_id,
    olr_db_nickname=OLR_DB_NICKNAME,
    olr_schema=OLR_SCHEMA_NAME,
    output_schema=OLR_SCHEMA_NAME,
):
    olr_lines_table_name = f"{project_id}_osm_openlr_lines"
    olr_nodes_table_name = f"{project_id}_osm_openlr_nodes"
    output_table_name = f"{project_id}_tt_osm_crosswalk"
    write_errs = []
    conn = db.connect_db(nickname="dell4db", driver="psycopg2")
    for seg in segments:
        observer = openlr_dereferencer.SimpleObserver() if observer else None
        olr_ref = tt_seg_to_openlr_ref(seg["geom"], frc=seg["road_class"])
        try:
            with PostgresMapReader(
                olr_db_nickname, olr_schema, olr_lines_table_name, olr_nodes_table_name
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
        insert_str = f"insert into {output_schema}.{output_table_name} values (%s, %s, %s)"
        try:
            cur.execute(insert_str, (seg["segment_id"], line_ids, geom.wkb))
            conn.commit()
        except psycopg2.DatabaseError:
            conn.rollback()
            write_errs.append(seg["segment_id"])
    conn.close()
    return write_errs


def run_batches_parallel(observer, config, seg_batches, num_batches, project_id):
    pbar = tqdm(total=num_batches)
    all_write_errs = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = []
        for batch in seg_batches:
            new_future = executor.submit(match_segs, batch, config, observer, project_id)
            futures.append(new_future)
        for result in concurrent.futures.as_completed(futures):
            write_errs = result.result()
            all_write_errs += write_errs
            pbar.update(n=1)
    return all_write_errs


def run_matcher(
    simplify,
    max_frc,
    parallel,
    resume,
    layer_id=None,
    project_id=PROJECT_ID,
    filter_proj_bbox=FILTER_PROJ_BBOX,
    observer=False,
    debug=False,
    batchsize=BATCHSIZE,
    tt_db_nickname=OLR_DB_NICKNAME,
    tt_segs_schema_name=TT_SEGS_SCHEMA_NAME,
    tt_segs_table_name=TT_SEGS_TBL_NAME,
    output_db_nickname=OLR_DB_NICKNAME,
    output_db_schema=OLR_SCHEMA_NAME,
):
    output_table_name = f"{project_id}_tt_osm_crosswalk"
    output_table_details = f"{output_db_schema}.{output_table_name}"
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    if not resume:
        create_output_table(
            db_nickname=output_db_nickname,
            schema_name=output_db_schema,
            table_name=output_table_name,
        )

    tt_segs = load_tomtom_segs(
        db_nickname=tt_db_nickname,
        db_schema=tt_segs_schema_name,
        table_name=tt_segs_table_name,
        output_db_nickname=output_db_nickname,
        output_schema=output_db_schema,
        output_table_name=output_table_name,
        layer_id=layer_id,
        resume=resume,
        max_frc=max_frc,
        simplify=simplify,
    )
    if filter_proj_bbox:
        bbox = get_proj_bbox(project_id=project_id)
        tt_segs = clip_segs_to_bbox(tt_segs, bbox)

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
    if parallel:
        all_write_errs = run_batches_parallel(observer, config, seg_batches, num_batches, project_id=project_id)
    else:
        all_write_errs = []
        for batch in tqdm(seg_batches, total=num_batches):
            write_errs = match_segs(batch, config, observer)
            all_write_errs.append(write_errs)
    print(f"Output table available at {output_table_details}")

    # create full outer join table
    create_full_outer_join_tbl()
    return all_write_errs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--resume", action="store_true", help="Append results to existing output table.")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode.")
    parser.add_argument("-o", "--observer", action="store_true", help="Enable internal dereferencing observer.")
    parser.add_argument("-s", "--simplify", action="store_true", help="Simplify TomTom geometries.")
    parser.add_argument("-f", "--max_frc", action="store", help="Max TomTom FRC to process.", default=MAX_FRC)
    parser.add_argument("-p", "--parallel", action="store_true", help="Run segment batches in parallel.")
    parser.add_argument("-l", "--layer_id", action="store", help="TomTom layer ID (CEM only).")
    args = parser.parse_args()
    resume = args.resume
    debug = args.debug
    observer = args.observer if not debug else True
    simplify = args.simplify
    max_frc = args.max_frc
    parallel = args.parallel
    layer_id = args.layer_id
    write_errs = run_matcher(simplify, max_frc, parallel, resume, layer_id, observer=observer, debug=debug)
