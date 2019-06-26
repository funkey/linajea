from __future__ import absolute_import
from linajea import check_function
import daisy
import json
import logging
import os

logger = logging.getLogger(__name__)


def predict_blockwise(
        setup,
        iteration,
        sample,
        db_host,
        db_name,
        cell_score_threshold=0,
        frames=None,
        frame_context=1,
        num_workers=16,
        **kwargs):

    data_dir = '../01_data'
    setup_dir = '../02_setups'

    # get absolute paths
    sample_dir = os.path.abspath(os.path.join(data_dir, sample))
    setup_dir = os.path.abspath(os.path.join(setup_dir, setup))
    # get ROI of source
    with open(os.path.join(sample_dir, 'attributes.json'), 'r') as f:
        attributes = json.load(f)

    voxel_size = daisy.Coordinate(attributes['resolution'])
    shape = daisy.Coordinate(attributes['shape'])
    offset = daisy.Coordinate(attributes['offset'])
    source_roi = daisy.Roi(offset, shape*voxel_size)

    # limit to specific frames, if given
    if frames:
        begin, end = frames
        begin -= frame_context
        end += frame_context
        crop_roi = daisy.Roi(
            (begin, None, None, None),
            (end - begin, None, None, None))
        source_roi = source_roi.intersect(crop_roi)

    # get context and total input and output ROI
    with open(os.path.join(setup_dir, 'test_net_config.json'), 'r') as f:
        net_config = json.load(f)
    net_input_size = net_config['input_shape']
    net_output_size = net_config['output_shape_2']
    net_input_size = daisy.Coordinate(net_input_size)*voxel_size
    net_output_size = daisy.Coordinate(net_output_size)*voxel_size
    context = (net_input_size - net_output_size)/2
    input_roi = source_roi.grow(context, context)
    output_roi = source_roi

    # create read and write ROI
    block_write_roi = daisy.Roi((0, 0, 0, 0), net_output_size)
    block_read_roi = block_write_roi.grow(context, context)

    logger.info("Following ROIs in world units:")
    logger.info("Input ROI       = %s" % input_roi)
    logger.info("Block read  ROI = %s" % block_read_roi)
    logger.info("Block write ROI = %s" % block_write_roi)
    logger.info("Output ROI      = %s" % output_roi)

    logger.info("Starting block-wise processing...")

    # process block-wise
    daisy.run_blockwise(
        input_roi,
        block_read_roi,
        block_write_roi,
        process_function=lambda: predict_worker(
            setup,
            iteration,
            sample,
            db_host,
            db_name,
            cell_score_threshold),
        check_function=lambda b: check_function(
            b,
            'predict',
            db_name,
            db_host),
        num_workers=num_workers,
        read_write_conflict=False)


def predict_worker(
        setup,
        iteration,
        sample,
        db_host,
        db_name,
        cell_score_threshold):

    worker_id = daisy.Context.from_env().worker_id

    logger.info("Starting predict worker...")

    daisy.call([
        'run_lsf',
        '-c', '4',
        '-g', '1',
        '-q', 'gpu_tesla',
        '-s', 'linajea/linajea:v1.5.14',
        'python -u %s %d %s %s %s %f' % (
            os.path.join('../02_setups', setup, 'predict.py'),
            iteration,
            sample,
            db_host,
            db_name,
            cell_score_threshold
        )],
        log_out='predict_%d.out' % worker_id,
        log_err='predict_%d.err' % worker_id)

    logger.info("Predict worker finished")