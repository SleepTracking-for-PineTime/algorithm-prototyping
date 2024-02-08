#!/usr/bin/env python3
"""
Initial work on accelerometer-only sleep tracking based on "A Novel, Open Access Method to
Assess Sleep Duration Using a Wrist-Worn Accelerometer" by Vincent T. van Hees et al., 2015:

https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0142533

"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


def stimuli(subject, data_dir):
    """Preprocess data from https://physionet.org/content/sleep-accel/1.0.0/ to
    get uniformly spaced samples at 10 Hz, which is the InfiniTime accelerometer
    update rate.

    """

    accel = np.genfromtxt(os.path.join(data_dir, "motion", f"{subject}_acceleration.txt"))
    truth = np.genfromtxt(os.path.join(data_dir, "labels", f"{subject}_labeled_sleep.txt"))

    # drop samples before test started (truth data starts at t=0)
    accel = accel[accel[:, 0] >= 0]
    t = accel[:, 0]

    # generate new time axis assuming uniformly spaced samples at <fs> Hz
    fs = 10  # Hz
    delta_t = t[-1] - t[0]
    N = int(np.floor(delta_t / (1/fs)))
    ti = np.linspace(t[0], t[0]+N/fs, N)

    # interpolate available data to generate sample for each interpolated timestamp
    axi = np.interp(ti, t, accel[:, 1])
    ayi = np.interp(ti, t, accel[:, 2])
    azi = np.interp(ti, t, accel[:, 3])

    # from now on, use the interpolated time axis
    t = ti

    # zero-order hold on truth data (assume truth data has a new sample each time subject state has
    # changed, holding the previous value until then)
    truth_interp = np.zeros(N)
    truth_interp[0] = truth[0, 1]

    for i in range(1, N):
        truth_interp[i] = truth[truth[:, 0] < t[i]][-1][1]  # there's probably a nicer way to do this...

    # we now have accelerometer data (axi, ayi, azi) and truth data (truth_interp) with the same time
    # axis (t)
    ret = np.zeros((N, 5))
    ret[:, 0] = t
    ret[:, 1] = axi
    ret[:, 2] = ayi
    ret[:, 3] = azi
    ret[:, 4] = truth_interp

    return ret


# exponential moving average
def ema(x, y, eta):
    return y + eta*(x - y)


# exponential moving "median"
def emm(x, y, eta):
    return y + eta*np.sign(x - y)

# arm angle estimate
def ang(accel):
    return np.arctan(accel[2] / np.sqrt(accel[0]**2 + accel[1]**2)) * 180/np.pi


def vanhees2015_modified(stim):
    """This version is modified to be less computationally expensive, using an
    exponential moving average instead of median. This will increase sensitivity
    to outliers. Exponential moving median seems to perform worse than average.

    Better performance can probably be gained by tweaking the exponential moving
    average decay factor, arm angle threshold or history length.

    """

    accel_avgs = np.zeros(3)
    fs = 10
    eta = 0.005  # exponential moving average decay factor

    # every 5 seconds, check if average arm angles has changed significantly
    seconds_per_update = 5
    arm_angle_hist = np.zeros(fs*seconds_per_update)
    arm_angle_mean_d = None

    # use the last 60 updates to classify sleep
    classification_hist_size = 60
    arm_angle_change_hist = np.zeros(classification_hist_size)

    # consider changes in arm angle larger than <arm_angle_threshold> between one window and the next
    # a wakeup event
    arm_angle_threshold = 5

    ret = [[0, 0]]

    # log some intermediate data for debugging
    dbg = np.zeros((len(stim), 7))
    dbg[:, :] = np.nan  # some values are not updated every time step

    for i in range(len(stim)):

        # update averages of accelerometer samples
        accel_avgs = ema(stim[i, 1:4], accel_avgs, eta)

        # estimate arm angle and update history
        arm_angle_hist[1:] = arm_angle_hist[:-1]
        arm_angle_hist[0] = ang(accel_avgs)

        dbg[i, 0] = stim[i, 0]  # time
        dbg[i, 1:4] = accel_avgs  # averaged accelerometer data
        dbg[i, 4] = arm_angle_hist[0]  # newest angle estimate

        # check change in arm angle with some interval
        if i % (fs*seconds_per_update) == 0:

            # average arm angle in this new window
            arm_angle_mean = np.mean(arm_angle_hist)

            dbg[i, 5] = arm_angle_mean  # log average arm angle

            if arm_angle_mean_d is not None:

                 # change in arm angle since last window
                arm_angle_change = np.abs(arm_angle_mean - arm_angle_mean_d)
                dbg[i, 6] = arm_angle_change

                # keep history of changes in arm angle for some longer duration
                arm_angle_change_hist[1:] = arm_angle_change_hist[:-1]
                arm_angle_change_hist[0] = arm_angle_change

                # if arm angle has not changed significantly between two windows for the last
                # <classification_hist_size> windows, classify as sleep. otherwise classify as awake
                if np.any(arm_angle_change_hist > arm_angle_threshold):
                    new_state = 0
                else:
                    new_state = 1

                # strictly speaking, this means sleep started a while ago:
                # ret.append([stim[i, 0]-(seconds_per_update*updates_per_classification)/fs, new_state])
                # but this might be simpler on hardware? (just shifts the entire time axis slightly)
                ret.append([stim[i, 0], new_state])

            arm_angle_mean_d = arm_angle_mean  # keep last computed arm angle mean

    return np.array(ret), dbg


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", required=True)
    parser.add_argument("-o", "--outfile")
    parser.add_argument("--data-dir", default="data")
    args = parser.parse_args()

    # seems to work well with subject 5498603
    # 4426783 has good example with some easy to see classification errors
    stim = stimuli(args.subject, args.data_dir)
    ret, dbg = vanhees2015_modified(stim)

    truth_binary = stim[:, 4].copy()
    truth_binary[truth_binary > 1] = 1

    fig = plt.figure(figsize=(24, 18), tight_layout=True)
    gs = gridspec.GridSpec(3, 2)

    ax_x = fig.add_subplot(gs[0, 0])
    ax_y = fig.add_subplot(gs[1, 0], sharex=ax_x)
    ax_z = fig.add_subplot(gs[2, 0], sharex=ax_x)
    ax_ang = fig.add_subplot(gs[0, 1], sharex=ax_x)
    ax_ang_change = fig.add_subplot(gs[1, 1], sharex=ax_x)
    ax_state = fig.add_subplot(gs[2, 1], sharex=ax_x)

    ax_x.plot(stim[:, 0], stim[:, 1], label="stim x")
    ax_y.plot(stim[:, 0], stim[:, 2], label="stim y")
    ax_z.plot(stim[:, 0], stim[:, 3], label="stim z")

    ax_x.plot(dbg[:, 0], dbg[:, 1], label="accel avg x")
    ax_y.plot(dbg[:, 0], dbg[:, 2], label="accel avg y")
    ax_z.plot(dbg[:, 0], dbg[:, 3], label="accel avg z")

    ax_ang.plot(dbg[:, 0], dbg[:, 5], label="arm angle mean", marker='x')
    ax_ang.plot(dbg[:, 0], dbg[:, 4], label="arm angle")

    ax_ang_change.plot(dbg[:, 0], dbg[:, 6], label="arm angle change", marker='.')
    xlims = ax_ang_change.get_xlim()
    ax_ang_change.plot(xlims, (5,)*2, linestyle='--', alpha=0.5, c='k', label="threshold")

    ax_state.plot(ret[:, 0], ret[:, 1], label="estimate", marker='x')
    ax_state.plot(stim[:, 0], stim[:, 4], label="truth")
    # ax_state.plot(stim[:, 0], truth_binary, label="truth (binary)")

    for ax in [ax_x, ax_y, ax_z, ax_ang, ax_ang_change, ax_state]:
        ax.legend(loc="upper right")
        ax.grid()
        ax.set_xlim((stim[0, 0]-100, stim[-1, 0]+100))
        ax.set_xlabel("time [s]")

    for ax in [ax_x, ax_y, ax_z]:
        ax.set_ylabel("Acceleration [g]")

    for ax in [ax_ang, ax_ang_change]:
        ax.set_ylabel("Angle [deg]")

    if args.outfile:
        plt.savefig(args.outfile)
    else:
        plt.show()
