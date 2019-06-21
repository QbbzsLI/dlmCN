import os
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import Grid


# plots a bunch of predictions from a saved network (from the validation set).
model_name = '20190508_155720'
pred_file = os.path.join(os.path.dirname(__file__), 'data', 'test_pred_{}.csv'.format(model_name))
truth_file = os.path.join(os.path.dirname(__file__), 'data', 'test_truth_{}.csv'.format(model_name))

pred = np.loadtxt(pred_file, delimiter=' ')
truth = np.loadtxt(truth_file, delimiter=' ')

# generated a grid of plots of the network prediction vs the true value
for fig_cnt in range(13):
    fig = plt.figure(figsize=(12, 8))
    grid = Grid(fig, rect=111, nrows_ncols=(4, 4), axes_pad=0.25, label_mode='L')
    for i, ax in enumerate(grid):
        try:
            ax.plot(truth[fig_cnt*16+i, :], label='truth')
            ax.plot(pred[fig_cnt*16+i, :], label='pred')
            ax.legend()
            mse = np.mean([dif**2 for dif in (truth[fig_cnt*16+i, :] - pred[fig_cnt*16+i, :])])
            plt.text(0.6, 0.4, 'MSE={:.2E}'.format(mse), ha='center', va='center', transform=ax.transAxes)
        except IndexError:
            pass
    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'figs', 'prediction_plot_{}_{}.png'.format(model_name,
                                                                                                   fig_cnt)))
    plt.close(fig)
