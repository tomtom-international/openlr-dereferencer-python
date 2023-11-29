CREATE TABLE openlr_nodes (
    node_id BIGINT PRIMARY KEY,
    geometry geometry(Point, 4326) DEFAULT NULL::geometry
);

CREATE TABLE openlr_lines (
    line_id BIGINT PRIMARY KEY,
    way_id BIGINT,
    startnode BIGINT NOT NULL,
    endnode BIGINT NOT NULL,
    frc integer NOT NULL,
    fow integer NOT NULL,
    geometry geometry(LineString, 4326) DEFAULT NULL::geometry,
    bearing float8
);

CREATE INDEX idx_openlr_nodes_geometry ON openlr_nodes USING GIST (geometry gist_geometry_ops_2d);
CREATE INDEX idx_openlr_lines_geometry ON openlr_lines USING GIST (geometry gist_geometry_ops_2d);
CREATE INDEX idx_openlr_lines_startnode ON openlr_lines(startnode int8_ops);
CREATE INDEX idx_openlr_lines_endnode ON openlr_lines(endnode int8_ops);