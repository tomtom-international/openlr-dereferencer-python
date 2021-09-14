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


    # track position of current lrp poped from queue to identify adjacent lrp
    forwd_idx_pos = 0
    backwd_idx_pos = len(lrps) - 1
    
    K = 0 # top K best paths
    routes = {}
    for forwd_lrp, backwd_lrp in zip(lrps, lrps[::-1]):
        
        if forwd_idx_pos >= backwd_idx_pos:
            break

        # pdb.set_trace()
        forwd_nxt_lrp = lrps[forwd_idx_pos + 1]

        backwd_prev_lrp = lrps[backwd_idx_pos - 1]

        # find candidates
        forwd_lrp_cand = list(
            nominate_candidates(forwd_lrp, reader, config, forwd_idx_pos == len(lrps)-1)
        )
        forwd_nxt_lrp_cand = list(
            nominate_candidates(forwd_nxt_lrp, reader, config, forwd_idx_pos == len(lrps)-1)
        )

        backwd_lrp_cand = list(
            nominate_candidates(
                backwd_lrp, reader, config, backwd_idx_pos == len(lrps)-1
            )
        )
        backwd_prev_lrp_cand = list(
            nominate_candidates(
                backwd_prev_lrp, reader, config, backwd_idx_pos == len(lrps)-1
            )
        )

        """
        " choose top K candidates to build K maximum paths
        " K = Min(len(first_lrp_cand) // 2, len(last_lrp_cand) // 2)
        
        """
        if forwd_idx_pos==0 and backwd_idx_pos==len(lrps)-1:
            
            # K = min(len(forwd_lrp_cand) // 2, len(backwd_lrp_cand) // 2)
            K = min(len(forwd_lrp_cand), len(backwd_lrp_cand))
        # pdb.set_trace()
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
        
        # pdb.set_trace()
        # mín and max path length to the next lrp
        backwd_minlen = (
            1 - config.max_dnp_deviation
        ) * backwd_prev_lrp.dnp - config.tolerated_dnp_dev
        backwd_maxlen = (
            1 + config.max_dnp_deviation
        ) * backwd_prev_lrp.dnp + config.tolerated_dnp_dev
        backwd_lfrc = config.tolerated_lfrc[backwd_prev_lrp.lfrcnp]
        
        # pdb.set_trace()
        # find 2K shorest paths between consequtive lrps: K through forward, K through backward search
        forwd_routes, backwd_routes = [], []
        for idx in range(K):

            forwd_route = handleCandidatePair(
                (forwd_lrp, forwd_nxt_lrp),
                forwd_pairs[idx],
                observer,
                forwd_lfrc,
                forwd_minlen,
                forwd_maxlen
            )
            backwd_route = handleCandidatePair(
                (backwd_prev_lrp, backwd_lrp),
                backwd_pairs[idx],
                observer,
                backwd_lfrc,
                backwd_minlen,
                backwd_maxlen
            )
            print(forwd_route)

            pdb.set_trace()
            if forwd_routes is not None:
                # forwd_routes.append(forwd_route)
                forwd_routes.append(
                    (
                        forwd_nxt_lrp,
                        forwd_pairs[idx][0].line.end_node.node_id,
                        forwd_pairs[idx][1].line.start_node.node_id,
                        forwd_route
                    )
                )

            else:
                forwd_routes.append(
                    (
                        forwd_nxt_lrp,
                        forwd_pairs[idx][0].line.end_node.node_id,
                        forwd_pairs[idx][1].line.start_node.node_id,
                        None
                    )
                )
            if backwd_routes is not None:
                # backwd_routes.append(backwd_route)
                backwd_routes.append(
                    (
                        backwd_lrp,
                        backwd_pairs[idx][0].line.end_node.node_id,
                        backwd_pairs[idx][1].line.start_node.node_id,
                        backwd_route
                    )
                )
            else:
                backwd_routes.append(
                    (
                        backwd_lrp,
                        backwd_pairs[idx][0].line.end_node.node_id,
                        backwd_pairs[idx][1].line.start_node.node_id,
                        None
                    )
                )
            
            # pdb.set_trace()
            # add routes for each lrp into adjacency list
            if forwd_idx_pos == 0:
                routes[forwd_lrp] = [forwd_routes]
                routes[backwd_lrp] = [backwd_routes]
            else:
                routes[forwd_lrp].append(forwd_routes)
                routes[backwd_prev_lrp].append(backwd_routes)
            # pdb.set_trace()
            """
            # check if backward and forward search processed the same node

            if forwd_pairs[idx][1].line.start_node == forwd_pairs[idx][0].line.end_node:
                
                # join to sub-routes to build a complete path
                # [current_route] + [nxt_route]
            """
        forwd_idx_pos += 1
        backwd_idx_pos -= 1
    print(routes)
    return routes
