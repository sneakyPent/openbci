import os
import h5py
import numpy as np
import matplotlib.pyplot as plt
from utils.constants import Constants as cnst
from utils import filters
import sys
sys.path.append('..')


def calculateSNR(data):
	"""
	Calculates the Signal to Noise Ratio for a given sample.
		* Find the maximum value in the sample.
		* sums every other value apart form the maximum.
		* Get the ratio of the above results.

	:param numpy.array data: The Sample
	:return: (float) The snr value for the given sample
	"""
	# Get the maximum value of the array
	signal = data.max()
	noise = data[data != signal].sum()
	snr = signal / noise
	return snr


def printUniqueFFT(fileNames, lowCut=5, highCut=50, fs=250, enabledChannel=None):
	"""
	Method used to plot a training fft without classification. Mainly used to test for unique target training.

	:param [str] fileNames: List of the full paths of the Hdf5 filenames contains the training dataset
	:return: None
	"""
	if enabledChannel is None:
		enabledChannel = [0, 1, 2, 3]

	for fileName in fileNames:
		fig = plt.figure(num=os.path.basename(fileName))
		with h5py.File(fileName, 'r') as f:
			d1 = None
			for channel in enabledChannel:
				if d1 is None:
					d1 = f['signal'][:, channel]
				else:
					d1 = np.column_stack((d1, f['signal'][:, channel]))
		fig.suptitle(os.path.basename(fileName))
		freq_6 = d1
		mm = np.array(freq_6)
		tt = mm[1:]
		print(tt.shape)
		freq_6 = tt
		data_processed_freq_6 = []
		i = 0

		while i < freq_6.shape[1]:
			# bandpass filtering            !! ATTENTION: how many channels you want<
			data_filt = filters.butter_bandpass_filter(freq_6[:, i], lowCut, highCut, fs, order=10)
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
			print('Channel ' + w.__str__() + ':' +
			      ' \t SNR = ' + calculateSNR(ps).__str__() +
			      ',\t Max = ' + max(ps).__str__() +
			      ',\t FREQ = ' + abs(freqs3[idx3][ps[idx3].tolist().index(max(ps[idx3].tolist()))]).__str__())
			lgSNR = ', SNR=' + "{:.5f}".format(calculateSNR(ps))
			lgMAX = ', Max=' + "{:.2e}".format(max(ps))
			lgFREQ = ' FREQ=' + "{:.4f}".format(abs(freqs3[idx3][ps[idx3].tolist().index(max(ps[idx3].tolist()))]))
			legnd = lb[w] + lgSNR + lgMAX + lgFREQ
			plt.plot(freqs3[idx3], ps[idx3], colors[w], label=legnd)
			# plt.title(
			# 	'Max = ' + round(max(ps), 3).__str__() +
			# 	', Freq = ' + round(abs(freqs3[idx3][ps[idx3].tolist().index(max(ps[idx3].tolist()))]), 3).__str__()
			# )
			plt.ylabel('Amplitude')
			plt.xlabel('Frequency (Hertz)')
		plt.xlim(left=0, right=40)
		plt.ylim(bottom=0)
		plt.legend(prop={"size": 9})
		# ----------- Saving figures ---------------
		figureName = os.path.splitext(os.path.basename(fileName))[0]
	# plt.savefig('C:/Users/ZN/Desktop/images/' + figureName + '.png', transparent=False)
	plt.show()


def printFFT(fileNames, lowCut=4, highCut=40, fs=250, enabledChannel=None):
	"""
	Creates a subplot of 4 plots, one for every class in the 'signal' dataset of the current hdf5 file.

	:param [str] fileNames: List of the full paths of the Hdf5 filenames contains the training dataset
	:return: None
	"""
	if enabledChannel is None:
		enabledChannel = [0, 1, 2, 3]

	for fileName in fileNames:
		with h5py.File(fileName, 'r') as f:
			signalData = f['signal'][:]

		signalDataInClassPackages = []
		for trClass in cnst.trainingClasses:
			if trClass == 0:
				continue
			signalDataInClassPackages.append([sample for sample in signalData if sample[8] == trClass])

		fig, axs = plt.subplots(2, 2)
		fig.suptitle(os.path.basename(fileName))
		axsCols, axsRows = axs.shape
		subCols = subRows = 0
		for tClass in range(len(cnst.trainingClasses) - 1):
			if subRows == axsRows:
				subCols += 1
				subRows = 0
			d1 = np.array(signalDataInClassPackages[tClass])
			freq_6 = None
			for channel in enabledChannel:
				if freq_6 is None:
					freq_6 = d1[:, channel]
				else:
					freq_6 = np.column_stack((freq_6, d1[:, channel]))
			mm = np.array(freq_6)
			tt = mm[1:]
			print('Class: ' + int(
				signalDataInClassPackages[tClass][0][8]).__str__() + ' --> Shape: ' + tt.shape.__str__())
			freq_6 = tt
			data_processed_freq_6 = []
			i = 0

			while i < freq_6.shape[1]:
				# bandpass filtering            !! ATTENTION: how many channels you want<
				data_filt = filters.butter_bandpass_filter(freq_6[:, i], lowCut, highCut, fs, order=10)
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
				print('Channel ' + w.__str__() + ':' +
				      ' \t SNR = ' + calculateSNR(ps).__str__() +
				      ',\t Max = ' + max(ps).__str__() +
				      ',\t FREQ = ' + abs(freqs3[idx3][ps[idx3].tolist().index(max(ps[idx3].tolist()))]).__str__())
				lgSNR = ', SNR=' + "{:.5f}".format(calculateSNR(ps))
				lgMAX = ', Max=' + "{:.2e}".format(max(ps))
				lgFREQ = ' FREQ=' + "{:.4f}".format(abs(freqs3[idx3][ps[idx3].tolist().index(max(ps[idx3].tolist()))]))
				legnd = lb[w] + lgSNR + lgMAX + lgFREQ
				axs[subCols, subRows].plot(freqs3[idx3], ps[idx3], colors[w], label=legnd)
				axs[subCols, subRows].set_title(
					'Class ' + cnst.trainingClasses[tClass + 1].__str__()
					+ ', Frequency: ' + cnst.trainingClassesFrequencies[tClass + 1].__str__()
					# + ', Max = ' + round(max(ps), 3).__str__()
					# + ', Freq = ' + round(abs(freqs3[idx3][ps[idx3].tolist().index(max(ps[idx3].tolist()))]), 3).__str__()
				)
			axs[subCols, subRows].set_xlim(left=0, right=40)
			axs[subCols, subRows].set_ylim(bottom=0)
			axs[subCols, subRows].legend(prop={"size": 9})
			subRows += 1
		for i, ax in enumerate(axs.flat):
			if i == 0:
				ax.set(ylabel='Amplitude')
			elif i == 1:
				continue
			elif i == 2:
				ax.set(xlabel='Frequency (Hertz)', ylabel='Amplitude')
			elif i == 3:
				ax.set(xlabel='Frequency (Hertz)')
	plt.show()


if __name__ == '__main__':
	sName = 'Training__29-09-2021__15-05-55'
	fName = "C:/Users/ZN/Desktop/Diplo/streamData/29-09-2021/goodLDA/" + sName + ".hdf5"
	fileList = [fName]
	printFFT(fileList)
