"""
"
Implements a function to search top K 
paths using bi-directional candidate search
"
"""
from heapq import heapify, heappush, heappop
from itertools import product
from logging import debug
from typing import Optional, Iterable, List, Tuple
from openlr import FRC, LocationReferencePoint
from ..maps import shortest_path, MapReader, Line
from ..maps.a_star import LRPathNotFoundError
from ..observer import DecoderObserver
from .candidate import Candidate
from .candidate_functions import nominate_candidates, handleCandidatePair
from .scoring import score_lrp_candidate, angle_difference
from .error import LRDecodeError
from .path_math import coords, project, compute_bearing
from .routes import Route
from .configuration import Config
import pdb


def bi_directional_search(
    lrps: List[LocationReferencePoint],
    reader: MapReader,
    config: Config,
    observer: Optional[DecoderObserver],
) -> List[Route]:

    # priority queue for forward and backward search

    forwd_pq, backwd_pq = [lrp for lrp in lrps[::-1]], lrps.copy()

    heapify(forwd_pq), heapify(backwd_pq)

    # track position of current lrp poped from queue to identify adjacent lrp
    forwd_idx_pos = 0
    backwd_idx_pos = len(lrps) - 1

    while (
        len(backwd_pq) <= len(forwd_pq) and len(forwd_pq) != 0 and len(backwd_pq) != 0
    ):

        forwd_lrp = heappop(forwd_pq)
        forwd_nxt_lrp = lrps[forwd_idx_pos + 1]

        backwd_lrp = heappop(backwd_pq)
        backwd_prev_lrp = lrps[backwd_idx_pos - 1]

        # find candidates
        forwd_lrp_cand = list(
            nominate_candidates(forwd_lrp, reader, config, len(forwd_pq) == 1)
        )
        forwd_nxt_lrp_cand = list(
            nominate_candidates(forwd_nxt_lrp, reader, config, len(forwd_pq) == 1)
        )

        backwd_lrp_cand = list(
            nominate_candidates(
                backwd_lrp, reader, config, len(backwd_pq) == len(processed_lrps)
            )
        )
        backwd_prev_lrp_cand = list(
            nominate_candidates(
                backwd_prev_lrp, reader, config, len(backwd_pq) == len(processed_lrps)
            )
        )

        """
        " choose top K candidates to build K maximum paths
        " K = Min(len(first_lrp_cand) // 2, len(last_lrp_cand) // 2)
        
        """
        if len(forwd_pq) == len(lrps) - 2:

            K = min(len(forwd_lrp_cand) // 2, len(backwd_lrp_cand) // 2)

        forwd_pairs = list(product(forwd_lrp_cand, forwd_nxt_lrp_cand))
        backwd_pairs = list(product(backwd_prev_lrp_cand, backwd_lrp_cand))

        # Sort by line scores
        forwd_pairs.sort(key=lambda pair: (pair[0].score + pair[1].score), reverse=True)
        backwd_pairs.sort(
            key=lambda pair: (pair[0].score + pair[1].score), reverse=True
        )

        # mín and max path length to the next lrp
        forwd_minlen = (
            1 - config.max_dnp_deviation
        ) * forwd_lrp.dnp - config.tolerated_dnp_dev
        forwd_maxlen = (
            1 + config.max_dnp_deviation
        ) * forwd_lrp.dnp + config.tolerated_dnp_dev
        forwd_lfrc = config.tolerated_lfrc[forwd_lrp.lfrcnp]

        # mín and max path length to the next lrp
        backwd_minlen = (
            1 - config.max_dnp_deviation
        ) * backwd_prev_lrp.dnp - config.tolerated_dnp_dev
        backwd_maxlen = (
            1 + config.max_dnp_deviation
        ) * backwd_prev_lrp.dnp + config.tolerated_dnp_dev
        backwd_lfrc = config.tolerated_lfrc[backwd_prev_lrp.lfrcnp]

        # find 2K shorest paths between consequtive lrps: K through forward, K through backward search
        forwd_routes, backwd_routes = [], []
        for idx in range(K):

            forwd_route = handleCandidatePair(
                (forwd_lrp, forwd_nxt_lrp),
                forwd_pairs[idx],
                observer,
                forwd_lfrc,
                forwd_minlen,
                forwd_maxlen,
            )
            backwd_route = handleCandidatePair(
                (backwd_prev_lrp, backwd_lrp),
                backwd_pairs[idx],
                observer,
                backwd_lfrc,
                backwd_minlen,
                backwd_maxlen,
            )

            if forwd_route is not None:
                # forwd_routes.append(forwd_route)
                forwd_routes.append((forwd_nxt_lrp, forwd_pairs[idx][0].line.start_node, forwd_pairs[idx][1].line.start_node.node_id, forwd_route))

            else:
                forwd_routes.append((forwd_nxt_lrp, forwd_pairs[idx][0].line.start_node, forwd_pairs[idx][1].line.start_node.node_id, None))
            if backwd_route is not None:
                # backwd_routes.append(backwd_route)
                backwd_routes.append((backwd_lrp, backwd_pairs[idx][0].line.start_node, backwd_pairs[idx][1].line.start_node.node_id, backwd_route))
            else:
                backwd_routes.append((backwd_lrp, backwd_pairs[idx][0].line.start_node, backwd_pairs[idx][1].line.start_node.node_id, None))

        # add route to each adjacent lrp into adjacency list
        if len(forwd_pq) == len(lrps):
            routes[forwd_lrp] = [forwd_routes]
            routes[backwd_lrp] = [backwd_routes]
        else:
            routes[forwd_lrp].append(forwd_routes)
            routes[backwd_prev_lrp].append(backwd_routes)

            """
            # check if backward and forward search processed the same node

            if forwd_pairs[idx][1].line.start_node == forwd_pairs[idx][0].line.end_node:
                
                # join to sub-routes to build a complete path
                # [current_route] + [nxt_route]
            """
            # TODO: add recursive call for the next lrps so computation
        # forwd_idx_pos += 1
        # backwd_idx_pos += 1
