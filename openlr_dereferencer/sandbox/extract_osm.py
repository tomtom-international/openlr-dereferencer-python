########################################################################
# Creates tables of nodes and edges from OSM
#
########################################################################

from repoman.utils import stl_database as db
import pandas as pd
import geopandas as gpd
from sqlalchemy import text, types
from sqlalchemy.dialects import postgresql as psql
from geoalchemy2 import Geometry
import osmnx as ox

PROJECT_ID = "at_7"
PROJECT_TBL_DB_NICKNAME = "dell4db"
PROJECTS_TBL_SCHEMA = "at_tomtom"
OLR_DB_NICKNAME = "dell4db"
SIMPLIFY = True
SCHEMA_NAME = "at_tomtom"
TT_TBL_SCHEMA = "at_tomtom"

# adapted from https://github.com/FraunhoferIVI/openlr/blob/master/src/main/resources/SQL/SQL_Script.sql
HWY_TO_FRC = {
    "motorway": 0,
    "motorway_link": 0,
    "trunk": 1,
    "trunk_link": 1,
    "primary": 2,
    "primary_link": 2,
    "secondary": 3,
    "secondary_link": 3,
    "tertiary": 4,
    "tertiary_link": 4,
    "road": 5,
    "road_link": 5,
    "unclassified": 6,  # changed from 5
    "residential": 6,  # changed from 5
    "living_street": 6,
}
HWY_TO_FOW = {
    "motorway": 1,
    "motorway_link": 6,
    "trunk": 2,
    "trunk_link": 6,
    "primary": 3,
    "primary_link": 6,
    "secondary": 3,
    "secondary_link": 6,
    "tertiary": 3,
    "tertiary_link": 6,
    "road": 3,
    "road_link": 6,
    "residential": 3,
    "living_street": 3,
    "unclassified": 0,
}
JUNCTION_TO_FOW = {"roundabout": 4}
YEAR = 2023
MONTH = 2


def extract_osm(year=YEAR, month=MONTH, simplify=False, project_id=PROJECT_ID):
    openlr_lines_tbl_name = f"{project_id}_osm_openlr_lines"
    openlr_nodes_tbl_name = f"{project_id}_osm_openlr_nodes"
    conn = db.connect_db(PROJECT_TBL_DB_NICKNAME, driver="sqlalchemy")
    query_str = f"""
    select *
    from {PROJECTS_TBL_SCHEMA}.projects
    where project_id = '{project_id}'
    """
    proj_info = gpd.read_postgis(text(query_str), con=conn, crs="epsg:4326", geom_col="bounding_box")
    conn.close()

    proj_bb_coords = proj_info["bounding_box"].values[0].bounds
    ox.settings.all_oneway = False
    ox.settings.bidirectional_network_types = []
    osmnx_datetimestamp = "{YYYY}-{MM}-01T00:00:00Z".format(YYYY=year, MM=str(month).zfill(2))
    overpass_date_str = f'[date:"{osmnx_datetimestamp}"]'
    ox.settings.overpass_settings += overpass_date_str
    west, south, east, north = proj_bb_coords
    g = ox.graph_from_bbox(
        north,
        south,
        east,
        west,
        network_type="drive",
        simplify=simplify,
        clean_periphery=False,
    )
    nodes, edges = ox.graph_to_gdfs(g)
    edges = edges.reset_index()
    nodes = nodes.reset_index()
    edges["osmid"] = edges["osmid"].apply(lambda x: set([x]) if isinstance(x, int) else set(x))
    merged = pd.merge(edges, edges, left_on=["u", "v"], right_on=["v", "u"], how="left")
    assert all(merged[merged["v_y"].isna()]["oneway_x"])
    edges.loc[edges["highway"].apply(type) == list, "highway"] = edges.loc[
        edges["highway"].apply(type) == list, "highway"
    ].str[0]
    edges.loc[edges["junction"].apply(type) == list, "junction"] = edges.loc[
        edges["junction"].apply(type) == list, "junction"
    ].str[0]
    edges["frc"] = edges["highway"].map(HWY_TO_FRC).fillna(7)
    edges["fow"] = edges["highway"].map(HWY_TO_FOW).fillna(0)
    edges.loc[edges["junction"] == "roundabout", "FOW"] = 4
    openlr_lines = edges[["osmid", "highway", "u", "v", "frc", "fow", "geometry"]].rename(
        columns={"u": "startnode", "v": "endnode", "osmid": "way_ids"}
    )
    openlr_lines.index.name = "line_id"
    openlr_lines.reset_index(inplace=True)
    openlr_nodes = nodes[["osmid", "geometry"]].rename(columns={"osmid": "node_id"})
    conn = db.connect_db(OLR_DB_NICKNAME, driver="sqlalchemy")
    openlr_lines.to_postgis(
        openlr_lines_tbl_name,
        con=conn,
        schema=SCHEMA_NAME,
        index=False,
        dtype={"geometry": Geometry("LINESTRING", srid=4326), "way_ids": psql.ARRAY(types.INTEGER)},
        if_exists="replace",
    )
    lines_index_query = (
        f"create index {openlr_lines_tbl_name}_lineid on {SCHEMA_NAME}.{openlr_lines_tbl_name} (line_id);"
    )
    db.execute_remote_query(conn, text(lines_index_query), driver="sqlalchemy")
    openlr_nodes.to_postgis(
        openlr_nodes_tbl_name,
        con=conn,
        schema=SCHEMA_NAME,
        index=False,
        dtype={
            "geometry": Geometry("POINT", srid=4326),
        },
        if_exists="replace",
    )
    nodes_index_query = (
        f"create index {openlr_nodes_tbl_name}_nodeid on {SCHEMA_NAME}.{openlr_nodes_tbl_name} (node_id);"
    )
    db.execute_remote_query(conn, text(nodes_index_query), driver="sqlalchemy")
    conn.close()

    print(f"New tables available: {SCHEMA_NAME}.{openlr_nodes_tbl_name}, {SCHEMA_NAME}.{openlr_lines_tbl_name}")


if __name__ == "__main__":
    extract_osm(simplify=SIMPLIFY, project_id=PROJECT_ID)
