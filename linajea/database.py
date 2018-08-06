from pymongo import MongoClient, IndexModel, ASCENDING
import logging

logger = logging.getLogger(__name__)

class CandidateDatabase(object):

    def __init__(self, db_name, mode='r'):

        self.db_name = db_name
        self.mode = mode
        self.client = MongoClient()

        if mode == 'w':
            self.client.drop_database(db_name)

        self.database = self.client[db_name]
        self.nodes = self.database['nodes']
        self.edges = self.database['edges']

        if mode == 'w':

            self.nodes.create_index(
                [
                    ('t', ASCENDING),
                    ('z', ASCENDING),
                    ('y', ASCENDING),
                    ('x', ASCENDING)
                ],
                name='position')

            self.nodes.create_index(
                [
                    ('id', ASCENDING)
                ],
                name='id')

            self.edges.create_index(
                [
                    ('u', ASCENDING),
                    ('v', ASCENDING)
                ],
                name='incident')

    def write_nodes(self, nodes, roi=None):

        if roi is not None:

            nodes = [
                n
                for n in nodes
                if roi.contains(n['position'])
            ]

        if len(nodes) == 0:

            logger.debug("No nodes to write.")
            return

        # convert 'position' into '{t,z,y,x}'
        nodes = [
            {
                'id': n['id'],
                't': n['position'][0],
                'z': n['position'][1],
                'y': n['position'][2],
                'x': n['position'][3]
            }
            for n in nodes
        ]

        logger.info("Insert %d nodes"%len(nodes))

        self.nodes.insert_many(nodes)

    def read_nodes(self, roi):

        logger.debug("Querying nodes in %s", roi)

        bt, bz, by, bx = roi.get_begin()
        et, ez, ey, ex = roi.get_end()

        nodes = self.nodes.find(
            {
                't': { '$gte': bt, '$lt': et },
                'z': { '$gte': bz, '$lt': ez },
                'y': { '$gte': by, '$lt': ey },
                'x': { '$gte': bx, '$lt': ex }
            })

        # convert '{t,z,y,x}' into 'position'
        nodes = [
            {
                'id': n['id'],
                'center': (n['t'], n['z'], n['y'], n['x'])
            }
            for n in nodes
        ]

        return nodes