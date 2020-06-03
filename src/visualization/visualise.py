import numpy as np
from numpy import genfromtxt

import matplotlib.pyplot as plt


def gate_output(games, config, n_frames=None):
    plt.style.use('clean')
    fig, ax = plt.subplots(figsize=(12, 3), ncols=2, nrows=1, sharey=True)

    for i, game in enumerate(games):
        read_path = config['game_data'] + game + '.csv'
        data = genfromtxt(read_path,
                          delimiter=',',
                          skip_header=True,
                          usecols=[1, 2])
        gate_out = data[:, 1]
        gate_out[gate_out < 0] = 0
        gate_out[gate_out > 0] = 1
        t = np.arange(0, len(gate_out))

        ax[i].step(t, gate_out, where='mid')

        ax[i].set_ylim([-0.1, 1.01])
        ax[i].set_yticks([0, 1])
        ax[i].set_ylabel('Gate Output')
        name = game.replace('_', ' ').capitalize()
        ax[i].set_title(name)
        ax[i].grid()
        ax[i].set_xlabel('Game Frames')

    plt.tight_layout(pad=0.04)
    plt.savefig('gate_output.pdf')
    plt.show()


def gate_output_with_action(game, config, n_frames=None):
    plt.style.use('clean')
    fig, ax = plt.subplots(figsize=(12, 3), ncols=2, nrows=1, sharey=True)

    read_path = config['game_data'] + game + '.csv'
    data = genfromtxt(read_path,
                      delimiter=',',
                      skip_header=True,
                      usecols=[1, 2])
    gate_out = data[0:20, 1]
    gate_out[gate_out < 0] = 0
    gate_out[gate_out > 0] = 1
    t = np.arange(0, len(gate_out))

    ax.step(t, gate_out, where='mid')

    ax.set_ylim([-0.1, 1.01])
    ax.set_yticks([0, 1])
    ax.set_ylabel('Gate Output')
    name = game.replace('_', ' ').capitalize()
    ax.set_title(name)
    ax.grid()
    ax.set_xlabel('Game Frames')

    plt.tight_layout(pad=0.04)
    plt.savefig('gate_output.pdf')
    plt.show()
