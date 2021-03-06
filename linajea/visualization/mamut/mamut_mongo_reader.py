from __future__ import print_function, division, absolute_import
import logging
import networkx as nx
import linajea
import daisy
from .mamut_reader import MamutReader

logger = logging.getLogger(__name__)


class MamutMongoReader(MamutReader):
    def __init__(self, mongo_url):
        super(MamutMongoReader, self).__init__()
        self.mongo_url = mongo_url

    def read_nodes_and_edges(
            self,
            db_name,
            frames=None,
            nodes_key=None,
            edges_key=None,
            key=None,
            filter_unattached=True):
        db = linajea.CandidateDatabase(db_name, self.mongo_url)
        if frames is None:
            frames = [0, 1e10]
        roi = daisy.Roi((frames[0], 0, 0, 0),
                        (frames[1] - frames[0], 1e10, 1e10, 1e10))
        if nodes_key is None:
            nodes = db.read_nodes(roi)
        else:
            nodes = db.read_nodes(roi, attr_filter={nodes_key: True})
        node_ids = [node['id'] for node in nodes]
        logger.debug("Found %d nodes" % len(node_ids))
        if edges_key is None and key is not None:
            edges_key = key
        if edges_key is None:
            edges = db.read_edges(roi, nodes=nodes)
        else:
            edges = db.read_edges(
                    roi, nodes=nodes, attr_filter={edges_key: True})
            if filter_unattached:
                logger.debug("Filtering cells")
                filtered_cell_ids = set([edge['source'] for edge in edges] +
                                        [edge['target'] for edge in edges])
                filtered_cells = [cell for cell in nodes
                                  if cell['id'] in filtered_cell_ids]
                nodes = filtered_cells
                node_ids = filtered_cell_ids
                logger.debug("Done filtering cells")

        logger.debug("Adjusting ids")
        target_min_id = 0
        actual_min_id = min(node_ids)
        diff = actual_min_id - target_min_id
        logger.debug("Subtracting {} from all cell ids".format(diff))
        for node in nodes:
            node['name'] = node['id']
            node['id'] -= diff

        for edge in edges:
            edge['source'] -= diff
            edge['target'] -= diff

        return nodes, edges

    def read_data(self, data):

        db_name = data['db_name']
        logger.debug("DB name: ", db_name)
        group = data['group'] if 'group' in data else None
        if 'parameters_id' in data:
            try:
                int(data['parameters_id'])
                selected_key = 'selected_' + str(data['parameters_id'])
            except:
                selected_key = data['parameters_id']
        else:
            selected_key = None
        frames = data['frames'] if 'frames' in data else None
        logger.debug("Selected key: ", selected_key)
        nodes, edges = self.read_nodes_and_edges(
                db_name,
                frames=frames,
                key=selected_key)

        if not nodes:
            logger.error("No nodes found in database {}".format(db_name))
            return [], []

        logger.info("Found %d nodes, %d edges in database"
                    % (len(nodes), len(edges)))

        cells = []
        for node in nodes:
            position = [node['t'], node['z'], node['y'], node['x']]
            if group is None:
                score = node['score'] if 'score' in node else 0
            else:
                score = group
            cells.append(self.create_cell(position, score, node['id'],
                                          name=node['name']))
        tracks = []
        if not edges:
            logger.info("No edges in database. Skipping track formation.")
            return cells, tracks

        graph = nx.DiGraph()
        cell_ids = []
        for cell in cells:
            if cell['id'] == -1:
                continue
            graph.add_node(cell['id'], **cell)
            cell_ids.append(cell['id'])
        for edge in edges:
            if edge['target'] not in cell_ids\
                    or edge['source'] not in cell_ids:
                logger.info("Skipping edge %s with an end not in cell set"
                            % edge)
                continue
            graph.add_edge(edge['source'], edge['target'], **edge)

        logger.info("Graph has %d nodes and %d edges"
                    % (len(graph.nodes), len(graph.edges)))
        track_graphs = [graph.subgraph(g).copy()
                        for g in nx.weakly_connected_components(graph)]
        logger.info("Found {} tracks".format(len(track_graphs)))
        track_id = 0
        for track in track_graphs:
            if not track.nodes:
                logger.info("track has no nodes. skipping")
                continue
            if not track.edges:
                logger.info("track has no edges. skipping")
                continue
            track_edges = []
            for u, v, edge in track.edges(data=True):
                score = edge['score'] if 'score' in edge else 0
                track_edges.append(self.create_edge(edge['source'],
                                                    edge['target'],
                                                    score=score))
            cell_frames = [cell['position'][0]
                           for _, cell in track.nodes(data=True)]
            start_time = min(cell_frames)
            end_time = max(cell_frames)

            num_cells = len(track.nodes)
            tracks.append(self.create_track(start_time,
                                            end_time,
                                            num_cells,
                                            track_id,
                                            track_edges))
            track_id += 1
        return cells, tracks
