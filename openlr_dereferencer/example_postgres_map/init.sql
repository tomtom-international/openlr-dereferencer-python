CREATE TABLE openlr_nodes (
    node_id BIGINT PRIMARY KEY,
    coord geometry(Point,4326) DEFAULT NULL::geometry
);

CREATE TABLE openlr_lines (
    line_id BIGINT PRIMARY KEY,
    startnode BIGINT NOT NULL,
    endnode BIGINT NOT NULL,
    frc integer NOT NULL,
    fow integer NOT NULL,
    path geometry(LineString,4326) DEFAULT NULL::geometry
);