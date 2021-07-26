import sys

import h5py
import numpy as np

sys.path.append('..')
from utils import filters
# from .filters import *
import matplotlib.pyplot as plt

refresh_rate = 60


# def fft_analysis(file1, target3_, lowcut, highcut, fs, frames_ch):

def printfft():
	# with h5py.File("../streamData/15minutesStream.hdf5", 'r') as f:
	# fileNameList = ['panwAristera2', 'katwAristera2', 'panwDexia2', 'katwDexia']
	# for filename in fileNameList:
	fileName = 'katwAristera2'
	with h5py.File("../streamData/" + fileName + ".hdf5", 'r') as f:
		d1 = f['signal']
		lowcut = 4
		highcut = 40
		fs = 250
		freq_6 = d1[:, 0:4]
		mm = np.array(freq_6)
		tt = mm[1:]
		print(tt.shape)
		freq_6 = tt
		data_processed_freq_6 = []
		i = 0

		while i < freq_6.shape[1]:
			# bandpass filtering            !! ATTENTION: how many channels you want<
			data_filt = filters.butter_bandpass_filter(freq_6[:, i], lowcut, highcut, fs, order=10)
			# hamming window
			data_fft = np.abs(np.fft.fft(data_filt)) ** 2
			# # fft
			data_processed_freq_6.append(data_fft)  # = np.array(data_processed)
			i = i + 1

		time_step = 1 / fs

		colors = ['r', 'b', 'g', 'orange']
		lb = ['ch1', 'ch2', 'ch3', 'ch4']

		# calculate the frequencies
		freqs3 = np.fft.fftfreq(freq_6[:, 0].size, time_step)
		idx3 = np.argsort(freqs3)

		for w in range(len(data_processed_freq_6)):
			ps = data_processed_freq_6[w]
			plt.plot(freqs3[idx3], ps[idx3], colors[w], label=lb[w])
		plt.xlim(left=0, right=40)
		plt.ylim(bottom=0)
		plt.legend()
		plt.show()


if __name__ == '__main__':
	name = ''
	printfft()
