import sys
import h5py
import numpy as np
import matplotlib.pyplot as plt

sys.path.append('..')
from utils.constants import Constants as cnst
from utils import filters

def printfft():
	# with h5py.File("../streamData/15minutesStream.hdf5", 'r') as f:
	# fileNameList = ['panwAristera2', 'katwAristera2', 'panwDexia2', 'katwDexia']
	# for filename in fileNameList:
	fileName = 'Streaming10_09_2021__15_39_05'
	with h5py.File("../streamData/" + fileName + ".hdf5", 'r') as f:
		signalData = f['signal']
		lowcut = 4
		highcut = 40
		fs = 250
		" training class breaking array"
		"---------"
		signalDataInClassPackages = [[sample for sample in signalData if sample[8] == cnst.unknownClass]]
		for trClass in cnst.trainingClasses:
			signalDataInClassPackages.append([sample for sample in signalData if sample[8] == trClass])
		"---------"
		
		for i in range(len(cnst.trainingClasses)+1):
			d1 = np.array(signalDataInClassPackages[i])
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

			# plot1 = plt.figure(1)
			# plt.plot(x1, y1)
			# plot2 = plt.figure(2)
			# plt.plot(x2, y2)
			plt.figure(i+1)
			for w in range(len(data_processed_freq_6)):
				ps = data_processed_freq_6[w]
				plt.plot(freqs3[idx3], ps[idx3], colors[w], label=lb[w])
			plt.xlim(left=0, right=40)
			plt.ylim(bottom=0)
			plt.legend()
			plt.show()


if __name__ == '__main__':
	printfft()
