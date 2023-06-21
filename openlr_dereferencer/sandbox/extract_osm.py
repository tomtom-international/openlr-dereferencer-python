from stl_general import database as db
import pandas as pd
import geopandas as gpd
from sqlalchemy import text
from geoalchemy2 import Geometry
import osmnx as ox

OPENLR_LINES_TBL_NAME = "hollowell_cumberland_osm_openlr_lines"
OPENLR_NODES_TBL_NAME = "hollowell_cumberland_osm_openlr_nodes"
SCHEMA_NAME = "mag"

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
    "unclassified": 5,
    "residential": 5,
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


def extract_osm():
    with db.connect_with("repoman", driver="sqlalchemy") as conn:
        query_str = """
        select *
        from cem_tt_repo.projects
        where project_id = 'hollowell_cumberland'
        """
        proj_info = gpd.read_postgis(text(query_str), con=conn, crs="epsg:4326", geom_col="bounding_box")
    proj_bb_coords = proj_info["bounding_box"].values[0].bounds
    ox.settings.all_oneway = False
    ox.settings.bidirectional_network_types = []
    osmnx_datetimestamp = "{YYYY}-{MM}-01T00:00:00Z".format(YYYY=2022, MM=12)
    overpass_date_str = f'[date:"{osmnx_datetimestamp}"]'
    ox.settings.overpass_settings += overpass_date_str
    west, south, east, north = proj_bb_coords
    g = ox.graph_from_bbox(north, south, east, west, network_type="drive", simplify=True, clean_periphery=False)
    nodes, edges = ox.graph_to_gdfs(
        g,
    )
    edges = edges.reset_index()
    nodes = nodes.reset_index()
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
    openlr_lines = edges[["osmid", "u", "v", "frc", "fow", "geometry"]].rename(
        columns={"u": "startnode", "v": "endnode", "osmid": "way_id"}
    )
    openlr_lines.index.name = "line_id"
    openlr_lines.reset_index(inplace=True)
    openlr_nodes = nodes[["osmid", "geometry"]].rename(columns={"osmid": "node_id"})
    with db.connect_with("dell4db", driver="sqlalchemy") as conn:
        openlr_lines.to_postgis(
            OPENLR_LINES_TBL_NAME,
            con=conn,
            schema=SCHEMA_NAME,
            index=False,
            dtype={
                "geometry": Geometry("LINESTRING", srid=4326),
            },
            if_exists="replace",
        )
        openlr_nodes.to_postgis(
            OPENLR_NODES_TBL_NAME,
            con=conn,
            schema=SCHEMA_NAME,
            index=False,
            dtype={
                "geometry": Geometry("POINT", srid=4326),
            },
            if_exists="replace",
        )
