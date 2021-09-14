import sys
import h5py
import numpy as np
import matplotlib.pyplot as plt

sys.path.append('..')
from utils.constants import Constants as cnst
from utils import filters


def printfft(fileName):
	with h5py.File(fileName, 'r') as f:
		signalData = f['signal']
		lowcut = 4
		highcut = 40
		fs = 250

		signalDataInClassPackages = []
		for trClass in cnst.trainingClasses:
			if trClass == 0:
				continue
			signalDataInClassPackages.append([sample for sample in signalData if sample[8] == trClass])

		fig, axs = plt.subplots(2, 2)
		axsCols, axsRows = axs.shape
		subCols = subRows = 0
		for tClass in range(len(cnst.trainingClasses) - 1):
			if subRows == axsRows:
				subCols += 1
				subRows = 0
			d1 = np.array(signalDataInClassPackages[tClass])
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
				axs[subCols, subRows].plot(freqs3[idx3], ps[idx3], colors[w], label=lb[w])
				axs[subCols, subRows].set_title(
					'Class ' + cnst.trainingClasses[tClass + 1].__str__() + ', Frequency: ' +
					cnst.trainingClassesFrequencies[
						tClass + 1].__str__())
			axs[subCols, subRows].set_xlim(left=0, right=40)
			axs[subCols, subRows].set_ylim(bottom=0)
			axs[subCols, subRows].legend()
			subRows += 1
		for ax in axs.flat:
			ax.set(xlabel='Amplitude', ylabel='Frequency (Hertz)')
		plt.show()


if __name__ == '__main__':
	sName = 'Streaming10_09_2021__16_21_49'
	fName = "../streamData/" + sName + ".hdf5"
	printfft(fName)
