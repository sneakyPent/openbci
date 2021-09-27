# -*- coding: utf-8 -*-
"""
Created on Wed Jul 10 13:56:22 2019

@author: xfarmakh
"""

import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as plt
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
import h5py
from multiprocessing import Event
# import rcca
# from parameters import refresh_rate
from sklearn.neighbors import KNeighborsClassifier
from sklearn import svm

# from parameters import refresh_rate
# 

# refresh rate
refresh_rate = 60


def butter_bandpass(lowcut, highcut, fs, order=5):
	# *************************************************** Resolve the order issue!!! *********************************
	nyq = 0.5 * fs
	low = lowcut / nyq
	high = highcut / nyq
	sos = signal.butter(order, [low, high], analog=False, btype='band', output='sos')
	return sos


def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
	sos = butter_bandpass(lowcut, highcut, fs, order=order)
	# *********** sosfiltfilt, instead of sosfilt, for forward-backward filtering
	# ************** check the axis!!!
	y = signal.sosfiltfilt(sos, data, axis=0)
	return y


def create_reference_signals(stimulus_freq, harmonics_num, samples_num, fs):
	time_vector = (np.arange(samples_num)) / fs
	y_ref = np.zeros((samples_num, 2 * harmonics_num))
	for i in range(harmonics_num):
		y_ref[:, 2 * i] = np.sin(2 * np.pi * stimulus_freq * (i + 1) * time_vector)
		y_ref[:, 2 * i + 1] = np.cos(2 * np.pi * stimulus_freq * (i + 1) * time_vector)
	return y_ref


def cca(X, Y):
	"""

	Canonical Correlation Analysis (from depmeas)
	Currently only returns the canonical correlations.
	"""
	n, p1 = X.shape
	n, p2 = Y.shape

	# center X and Y
	meanX = X.mean(axis=0)
	meanY = Y.mean(axis=0)
	X = X - meanX[np.newaxis, :]
	Y = Y - meanY[np.newaxis, :]

	Qx, Rx = np.linalg.qr(X)
	Qy, Ry = np.linalg.qr(Y)

	rankX = np.linalg.matrix_rank(Rx)
	if rankX == 0:
		raise Exception('Rank(X) = 0! Bad Data!')
	elif rankX < p1:
		# warnings.warn("X not full rank!")
		Qx = Qx[:, 0:rankX]
		Rx = Rx[0:rankX, 0:rankX]

	rankY = np.linalg.matrix_rank(Ry)
	if rankY == 0:
		raise Exception('Rank(Y) = 0! Bad Data!')
	elif rankY < p2:
		# warnings.warn("Y not full rank!")
		Qy = Qy[:, 0:rankY]
		Ry = Ry[0:rankY, 0:rankY]

	d = min(rankX, rankY)
	svdInput = np.dot(Qx.T, Qy)

	U, r, V = np.linalg.svd(svdInput)
	r = np.clip(r, 0, 1)
	# A = np.linalg.lstsq(Rx, U[:,0:d]) * np.sqrt(n-1)
	# B = np.linalg.lstsq(Ry, V[:,0:d]) * np.sqrt(n-1)

	# TODO: resize A to match inputs

	# return (A,B,r)
	return r


# ... This function calculates the cca correlations of a segment of data, for all the stimulus freqs
# ... segment: number_of_samples x number_of_channels
def calculate_cca_correlations(segment, fs, frames_ch, harmonics_num):
	frames_np = np.sum(np.array(frames_ch),
	                   1)  # I sum the frames along axis 1 (i.e. I sum all the elements of each row)
	stimulus_freqs = np.divide(np.full(frames_np.shape[0], refresh_rate),
	                           frames_np)  # I divide the screen refresh rate by the frames_np for each stimulus frequency
	# .....checkerboard invokes double of the stimuli freqs!!!!!!!!!!!!
	# if not refresh_rate == 30:
	stimulus_freqs = 2 * stimulus_freqs

	r_segment = np.zeros((1, stimulus_freqs.shape[0]))

	for stimulus_ind in range(stimulus_freqs.shape[0]):
		stimulus_freq = stimulus_freqs[stimulus_ind]
		y_ref = create_reference_signals(stimulus_freq, harmonics_num, segment.shape[0],
		                                 fs)  # create_cca_reference_signals

		r_pyr = cca(segment.astype(float), y_ref.astype(float))
		r_segment[0, stimulus_ind] = r_pyr[0]  # r_segment contains one cca correlation for each stimulus frequency

	return r_segment


# ....This function band-pass filters a number of segments, whether they are training or testing data
# ....It calculates the cca correlations of all filtered segments and the ground-truth labels
def calculate_cca_corrs_all_segments(segment_buffer, chan_ind, fs, frames_ch, lowcut, highcut, harmonics_num,
                                     _dataInFile):
	if _dataInFile.is_set():  # If data are read from file, they are already in a numpy array form
		segments_num = len(segment_buffer)
	else:  # else, if we proccess the data right after the presentation, the data lie in a buffer
		segments_num = segment_buffer.qsize()

	frames_np = np.sum(np.array(frames_ch),
	                   1)  # I sum the frames along axis 1 (i.e. I sum all the elements of each row)
	stimulus_freqs = np.divide(np.full(frames_np.shape[0], refresh_rate),
	                           frames_np)  # I divide the screen refresh rate by the frames_np for each stimulus frequency

	# .....checkerboard invokes double of the stimuli freqs!!!!!!!!!!!!
	print("stimulus_freqs:", stimulus_freqs)
	# if refresh_rate == 60:
	stimulus_freqs = 2 * stimulus_freqs

	ground_truth_full = np.zeros((segments_num, 1))  # Initialize ground truth array
	r_full = np.zeros((segments_num, stimulus_freqs.shape[0]))  # Initialize array of cca coefficients r
	mask = np.zeros((segments_num, 1),
	                dtype=bool)  # The mask will contain false for all the segments where the label is not the same for all samples
	# ms = mask.shape[0]
	# mv = 0
	# cc_tr = 0
	# while ms > 0:
	#     if mask[mv] == True:
	#         cc_tr = cc_tr +1
	#     ms = ms - 1

	# print("True labels",cc_tr)

	for segment_ind in range(segments_num):  # Main loop that runs over segments

		if _dataInFile.is_set():
			segment_full = segment_buffer[segment_ind]
		else:
			segment_full = segment_buffer.get()

		segment = segment_full[:, np.asarray(chan_ind)]  # choose channels (last column = label, we will use it later)

		mask[segment_ind] = len(set(segment_full[:, -1])) <= 1
		ground_truth_full[segment_ind, 0] = segment_full[
			0, -1]  # I store the label of the segment, which is in the last (-1) column of the 1st (0) row

		segment_filt = butter_bandpass_filter(segment, lowcut, highcut, fs, order=10)

		r_full[segment_ind, :] = calculate_cca_correlations(segment_filt, fs, frames_ch, harmonics_num)

	# print("Before", ground_truth_full.shape)
	ground_truth_new = ground_truth_full[np.ravel(mask)]
	# print("After", ground_truth_new.shape)
	r_new = r_full[np.ravel(mask)]

	ground_truth = ground_truth_new[np.nonzero(ground_truth_new < 200)[0]]
	r = r_new[np.nonzero(ground_truth_new < 200)[0]]

	return r, ground_truth
