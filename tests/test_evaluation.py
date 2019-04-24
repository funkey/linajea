import linajea.tracking
import linajea.evaluation as e
import logging
import unittest
import linajea
import daisy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger('linajea.evaluation').setLevel(logging.DEBUG)


class EvaluationTestCase(unittest.TestCase):

    def get_tracks(self, cells, edges, roi):
        g = self.create_graph(cells, edges, roi)
        tracks = g.get_tracks()

        str_x = "\nTracks:\n"
        for track_id, track in enumerate(tracks):
            str_x += "Track %d has nodes %s and edges %s\n"\
                % (track_id, track.nodes, track.edges)
        logger.debug(str_x)
        return tracks

    def create_graph(self, cells, edges, roi):
        db = linajea.CandidateDatabase('test_eval', 'localhost')
        graph = db[roi]
        graph.add_nodes_from(cells)
        graph.add_edges_from(edges)
        tg = linajea.tracking.TrackGraph(graph_data=graph, frame_key='t')
        return tg

    def getTrack1(self):
        cells = [
                (1, {'t': 0, 'z': 0, 'y': 0, 'x': 0}),
                (2, {'t': 1, 'z': 0, 'y': 0, 'x': 0}),
                (3, {'t': 2, 'z': 0, 'y': 0, 'x': 0}),
                (4, {'t': 3, 'z': 0, 'y': 0, 'x': 0}),
            ]
        edges = [
            (2, 1),
            (3, 2),
            (4, 3)
            ]
        roi = daisy.Roi((0, 0, 0, 0), (4, 4, 4, 4))
        return cells, edges, roi

    def getDivisionTrack(self):
        cells = [
                (1, {'t': 0, 'z': 0, 'y': 0, 'x': 0}),
                (2, {'t': 1, 'z': 0, 'y': 0, 'x': 0}),
                (3, {'t': 2, 'z': 0, 'y': 0, 'x': 0}),
                (4, {'t': 3, 'z': 0, 'y': 0, 'x': 0}),
                (5, {'t': 2, 'z': 3, 'y': 0, 'x': 0}),
                (6, {'t': 3, 'z': 3, 'y': 0, 'x': 0}),
                (7, {'t': 4, 'z': 3, 'y': 0, 'x': 0}),
            ]
        edges = [
            (2, 1),
            (3, 2),
            (4, 3),
            (5, 2),
            (6, 5),
            (7, 6),
            ]
        roi = daisy.Roi((0, 0, 0, 0), (5, 5, 5, 5))
        return cells, edges, roi

    def test_perfect_evaluation(self):
        cells, edges, roi = self.getTrack1()
        gt_track_graph = self.create_graph(cells, edges, roi)
        for cell in cells:
            cell[1]['y'] += 1
        rec_track_graph = self.create_graph(cells, edges, roi)
        scores = e.evaluate(
                gt_track_graph, rec_track_graph, matching_threshold=2)

        self.assertEqual(scores.num_matched_edges, 3)
        self.assertEqual(scores.num_fp_edges, 0)
        self.assertEqual(scores.num_fn_edges, 0)
        self.assertEqual(scores.num_gt_tracks, 1)
        self.assertEqual(scores.num_gt_matched_tracks, 1)
        self.assertEqual(scores.num_rec_matched_tracks, 1)
        self.assertEqual(scores.num_rec_tracks, 1)
        self.assertEqual(scores.num_edge_fps_in_matched_tracks, 0)
        self.assertEqual(scores.avg_segment_length, 3)

    def test_imperfect_evaluation(self):
        cells, edges, roi = self.getTrack1()
        gt_track_graph = self.create_graph(cells, edges, roi)
        for cell in cells:
            cell[1]['y'] += 1
        # introduce a split error
        del edges[1]
        rec_track_graph = self.create_graph(cells, edges, roi)
        scores = e.evaluate(
                gt_track_graph, rec_track_graph, matching_threshold=2)

        self.assertEqual(scores.num_matched_edges, 2)
        self.assertEqual(scores.num_fp_edges, 0)
        self.assertEqual(scores.num_fn_edges, 1)
        self.assertEqual(scores.num_gt_tracks, 1)
        self.assertEqual(scores.num_gt_matched_tracks, 1)
        self.assertEqual(scores.num_rec_matched_tracks, 2)
        self.assertEqual(scores.num_rec_tracks, 2)
        self.assertEqual(scores.num_edge_fps_in_matched_tracks, 0)
        self.assertEqual(scores.avg_segment_length, 1)

    def test_fn_division_evaluation(self):
        cells, edges, roi = self.getDivisionTrack()
        gt_cells = cells.copy()
        gt_edges = edges.copy()
        gt_track_graph = self.create_graph(gt_cells, gt_edges, roi)
        for cell in cells:
            cell[1]['y'] += 1
        # introduce a split error
        edges.remove((5, 2))
        rec_track_graph = self.create_graph(cells, edges, roi)
        scores = e.evaluate(
                gt_track_graph, rec_track_graph, matching_threshold=2)

        self.assertEqual(scores.num_matched_edges, 5)
        self.assertEqual(scores.num_fp_edges, 0)
        self.assertEqual(scores.num_fn_edges, 1)
        self.assertEqual(scores.num_gt_tracks, 1)
        self.assertEqual(scores.num_gt_matched_tracks, 1)
        self.assertEqual(scores.num_rec_matched_tracks, 2)
        self.assertEqual(scores.num_rec_tracks, 2)
        self.assertEqual(scores.num_edge_fps_in_matched_tracks, 0)
        self.assertEqual(scores.avg_segment_length, 2.5)
        self.assertEqual(scores.num_gt_divisions, 1)
        self.assertEqual(scores.num_rec_divisions_in_matched_tracks, 0)
        self.assertEqual(scores.num_fp_divisions, 0)

    def test_fn_division_evaluation2(self):
        cells, edges, roi = self.getDivisionTrack()
        # introduce a false positive edge
        gt_cells = cells.copy()
        gt_edges = edges.copy()
        del gt_cells[0]
        del gt_edges[0]
        gt_track_graph = self.create_graph(gt_cells, gt_edges, roi)
        for cell in cells:
            cell[1]['y'] += 1
        # introduce a split error
        edges.remove((5, 2))
        rec_track_graph = self.create_graph(cells, edges, roi)
        scores = e.evaluate(
                gt_track_graph, rec_track_graph, matching_threshold=2)

        self.assertEqual(scores.num_matched_edges, 4)
        self.assertEqual(scores.num_fp_edges, 1)
        self.assertEqual(scores.num_fn_edges, 1)
        self.assertEqual(scores.num_gt_tracks, 1)
        self.assertEqual(scores.num_gt_matched_tracks, 1)
        self.assertEqual(scores.num_rec_matched_tracks, 2)
        self.assertEqual(scores.num_rec_tracks, 2)
        self.assertEqual(scores.num_edge_fps_in_matched_tracks, 1)
        self.assertEqual(scores.avg_segment_length, 2)
        self.assertEqual(scores.num_gt_divisions, 1)
        self.assertEqual(scores.num_rec_divisions_in_matched_tracks, 0)
        self.assertEqual(scores.num_fp_divisions, 0)

    def test_fp_division_evaluation(self):
        cells, edges, roi = self.getDivisionTrack()
        gt_cells = cells.copy()
        gt_edges = edges.copy()
        # remove division from gt
        gt_edges.remove((5, 2))
        gt_track_graph = self.create_graph(gt_cells, gt_edges, roi)
        for cell in cells:
            cell[1]['y'] += 1
        rec_track_graph = self.create_graph(cells, edges, roi)
        scores = e.evaluate(
                gt_track_graph, rec_track_graph, matching_threshold=2)

        self.assertEqual(scores.num_matched_edges, 5)
        self.assertEqual(scores.num_fp_edges, 1)
        self.assertEqual(scores.num_fn_edges, 0)
        self.assertEqual(scores.num_gt_tracks, 2)
        self.assertEqual(scores.num_gt_matched_tracks, 2)
        self.assertEqual(scores.num_rec_matched_tracks, 1)
        self.assertEqual(scores.num_rec_tracks, 1)
        self.assertEqual(scores.num_edge_fps_in_matched_tracks, 1)
        self.assertAlmostEqual(scores.avg_segment_length, 5.0/3.0)
        self.assertEqual(scores.num_gt_divisions, 0)
        self.assertEqual(scores.num_rec_divisions_in_matched_tracks, 1)
        self.assertEqual(scores.num_fp_divisions, 1)
