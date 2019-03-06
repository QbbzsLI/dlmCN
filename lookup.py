import os
import tensorflow as tf
import numpy as np
import time

import utils
import network_maker
import network_helper
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('TkAgg')
from itertools import islice

# generate geometric parameters for the grid and save them in a file
def gen_data(out_path, param_bounds, spacings):
    scan = []
    for h1 in np.arange(param_bounds[0, 0], param_bounds[0, 1], spacings[0]):
        scan.append(h1)
    print('possible h1 values are in {}'.format(scan))
    print('if all bounds and spacings are the same, number of combos is {}'.format(len(scan)**8))
    start = time.time()
    with open(os.path.join(out_path, 'grid.csv'), 'w+') as gfile:
        for h1 in np.arange(param_bounds[0, 0], param_bounds[0, 1], spacings[0]):
            for h2 in np.arange(param_bounds[1, 0], param_bounds[1, 1], spacings[1]):
                check_time = time.time()
                print('time elapsed: {}'.format(np.round(check_time-start), 1))
                print('h1 = {}, h2 = {}'.format(h1, h2))
                for h3 in np.arange(param_bounds[2, 0], param_bounds[2, 1], spacings[2]):
                    for h4 in np.arange(param_bounds[3, 0], param_bounds[3, 1], spacings[3]):
                        for r1 in np.arange(param_bounds[4, 0], param_bounds[4, 1], spacings[4]):
                            for r2 in np.arange(param_bounds[5, 0], param_bounds[5, 1], spacings[5]):
                                for r3 in np.arange(param_bounds[6, 0], param_bounds[6, 1], spacings[6]):
                                    for r4 in np.arange(param_bounds[7, 0], param_bounds[7, 1], spacings[7]):
                                        geom_params = np.round([h1, h2, h3, h4, r1, r2, r3, r4], 1)
                                        geom_strs = [str(el) for el in geom_params]
                                        gfile.write(",".join(geom_strs) + '\n')
    finish = time.time()
    print('total time taken = {}'.format(finish-start))

# yield the geometry from the saved grid data file in the form of a dataset
def import_data(data_dir, batch_size=100):
    """
    :param data_dir:
    :param grid_dir:
    :return: returns a dataset which can yield all the input data
    """

    # define input and output files
    data_paths = [os.path.join(data_dir, file) for file in os.listdir(data_dir) if file.endswith(".csv")]

    # pull data into python, should be either for training set or eval set
    print(data_paths)

    def get_geom(data_paths):
        for file_name in data_paths:
            with open(file_name, 'r') as file:
                for line in file:
                    geom = line.split(",")[2:10]   #[2:10] if using validation set for testing
                    # print(geom, np.shape(geom))
                    assert len(geom) == 8, "expected geometry vector of length 8, got length {}".format(len(geom))
                    yield geom

    ds = tf.data.Dataset.from_generator(lambda: get_geom(data_paths), (tf.float32),
                                        (tf.TensorShape([8]))
                                        )
    # shuffle then split into training and validation sets
    ds = ds.batch(batch_size, drop_remainder=True)

    iterator = ds.make_one_shot_iterator()
    features = iterator.get_next()
    pred_init_op = iterator.make_initializer(ds)

    return features, pred_init_op


# generate predictions with the given model and save them to a spectrum library file
def main(data_dir, grid_dir, model_name, batch_size=100):
    ckpt_dir = os.path.join(os.path.dirname(__file__), 'models', model_name)
    fc_filters, tconv_Fnums, tconv_dims, tconv_filters, n_filter, n_branch, \
    reg_scale = network_helper.get_parameters(ckpt_dir)

    print('defining input data')
    features, pred_init_op = import_data(data_dir=data_dir,
                                         batch_size=batch_size)

    print('making network')
    # make network
    ntwk = network_maker.CnnNetwork(features, [], utils.my_model_fn_tens, batch_size,
                                    fc_filters=fc_filters, tconv_Fnums=tconv_Fnums, tconv_dims=tconv_dims,
                                    n_filter=n_filter, n_branch=n_branch, reg_scale=reg_scale,
                                    tconv_filters=tconv_filters, make_folder=False)

    print('defining save file')
    save_file = os.path.join('.', grid_dir)

    # evaluate the model for each geometry in the grid file
    print('executing the model ...')
    pred_file, feat_file = ntwk.predict(pred_init_op, ckpt_dir=ckpt_dir, model_name=model_name, save_file=save_file)
    return pred_file, feat_file

def lookup(sstar, library_path, candidate_num):
    candidates = []
    start = time.time()
    with open(library_path) as lib:
        line_batch = islice(lib, 100)
        for line in line_batch:
            # line_start = time.time()
            # if cnt != 0 and (cnt % 1000) == 0:
            #     print('line is {}, time taken is {}'.format(cnt, np.round(time.time()-start, 3)))
            # get spectrum from library file
            spectrum = line.split(',')
            spectrum = [float(string) for string in spectrum]
            assert len(spectrum) == 300

            # calculate mse with desired spectrum
            errors = []
            for sstar_point, spectrum_point in zip(sstar, spectrum):
                if sstar_point is not None:  # use only the defined points of sstar
                    errors.append((spectrum_point-sstar_point)**2)
            mse = np.mean(errors)

            if len(candidates) < candidate_num:  # then we need more candidates, so append
                candidates.append([spectrum, mse])
            else:  # see if this spectrum is better than any of the current candidates
                for candidate in candidates:
                    if candidate[1] > mse:
                        candidates.append([spectrum, mse])
                        candidates.sort(key=lambda x: x[1])
                        candidates = candidates[:candidate_num]  # take only the candidates with the lowest error
                        break
    # extract the defined points of sstar
    sstar_keyPoints = []
    for cnt, value in enumerate(sstar):
        if value is not None:
            sstar_keyPoints.append([cnt, value])

    print('total search time taken is {}'.format(np.round(time.time() - start, 4)))
    #convert to arrays so we can slice
    sstar_keyPoints = np.array(sstar_keyPoints)
    candidates = np.array(candidates)
    # plot the defined sstar points along with the candidate
    plt.scatter(sstar_keyPoints[:, 0],
                sstar_keyPoints[:, 1])
    for candidate in candidates[:, 0]:
        plt.plot(candidate)
    plt.show()
    return candidates

if __name__=="__main__":
    # gen_data(
    #     os.path.join('.', 'dataGrid', 'gridFiles'), param_bounds=np.array([
    #                                                          [42, 52.2], [42, 52.2], [42, 52.2], [42, 52.2],
    #                                                          [42, 52.2], [42, 52.2], [42, 52.2], [42, 52.2]]),
    #     spacings=[.8,.8,.8,.8,.8,.8,.8,.8])
    modelNum = '20190218_182224'
    #import_data(os.path.join('.', 'dataIn', 'eval'), os.path.join('.', 'dataGrid'), batch_size=100, shuffle_size=100)
    # main(data_dir=os.path.join('.', 'dataIn', 'eval'), grid_dir=os.path.join('.', 'dataGrid'),
    #      model_name=modelNum, batch_size=1000)

    # define test sstar, see ML\lookupTest\findTestSpectra.nb
    spec = [None for i in range(300)]
    spec[50] = .7
    spec[100] = .2
    spec[250] = .1
    cand = lookup(sstar=spec,
                  library_path=os.path.join('.', 'dataGrid', 'test_pred_' + modelNum + '.csv'),
                  candidate_num=3)
