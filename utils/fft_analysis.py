import math
import os
import h5py
import numpy as np
import matplotlib.pyplot as plt
from brainflow import DataFilter, NoiseTypes, WindowFunctions, FilterTypes
from utils.constants import Constants as cnst, FilterType, FftType
from utils.constants import ElectrodeType
from utils import filters, filteringCases
import sys

sys.path.append('..')


def createLegends(plotData, freq, idx, channel=None):
	lgSNR = 'SNR=' + "{:.5f}".format(calculateSNR(plotData[idx]))
	lgMAX = ', Max=' + "{:.5e}".format(max(plotData))
	lgFREQ = ' FREQ=' + "{:.4f}".format(
		abs(
			freq[idx][plotData[idx].tolist().index(max(plotData[idx].tolist()))]
		)
	)
	legnd = lgSNR + lgMAX + lgFREQ
	if channel is not None:
		lgChannel = 'Channel=' + channel.__str__() + ', '
		legnd = lgChannel + legnd
	return legnd


def calculateFFT(plotData, dtLen, samplingRate, lowBandBound, highBandBound, centerFreq, bandwidth,
                 fftType: FftType, filtered: bool, filterType: FilterType, noiseCancellation: bool):
	data, filterDescription = filteringCases(plotData, samplingRate, lowBandBound, highBandBound,
	                                         filtered, filterType, noiseCancellation, centerFreq, bandwidth)
	figName = fftType.name.upper() + filterDescription
	if fftType == FftType.brainflowFFT:
		retPSD, retFreq, retIdx = brainflowFFT(data, dtLen, samplingRate)
	elif fftType == FftType.pythonFFT:
		retPSD, retFreq, retIdx = pythonFFT(data, dtLen, samplingRate)
	else:
		return None
	return retPSD, retFreq, retIdx, figName


def brainflowFFT(data, dtLen, samplingRate):
	fft_data = DataFilter.perform_fft(np.array(data.tolist()), WindowFunctions.HANNING.value)
	PSD = fft_data * np.conj(fft_data) / dtLen
	PSD = np.array([value.real for value in PSD])
	freq = np.fft.fftfreq(data.size, 1 / samplingRate)[:fft_data.size]
	idx = np.argsort(freq)
	return PSD, freq, idx


def pythonFFT(data, dtLen, samplingRate):
	# hamming window
	data_fft = np.abs(np.fft.fft(data)) ** 2
	time_step = 1 / samplingRate
	# calculate the frequencies
	freq = np.fft.fftfreq(dtLen, time_step)
	idx = np.argsort(freq)
	return data_fft, freq, idx


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
	snr = 10*math.log((signal / noise),10)
	return snr


def printUniqueFFT(fileNames, lowCut=5, highCut=50, fs=250, enabledChannel=None,
                   usingElectrodes: ElectrodeType = ElectrodeType.DRY):
	"""
	Method used to plot a training fft without classification. Mainly used to test for unique target training.

	:param [str] fileNames: List of the full paths of the Hdf5 filenames contains the training dataset
	:param [int] enabledChannel: The EEG enabled channels' data will be retrieved from the dataset.
	:param int fs: The fs will be used for the bandpass filtering.
	:param int highCut: The high cut frequency will be used for the bandpass filtering.
	:param int lowCut: The low cut frequency will be used for the bandpass filtering.
	:return: None
	"""
	# set channels data for plotting if not given
	if enabledChannel is None:
		enabledChannel = [0, 1, 2, 3]

	# run for every given file
	for fileName in fileNames:
		fig = plt.figure(num=os.path.basename(fileName))
		# open file
		with h5py.File(fileName, 'r') as f:
			# create signalData list contained the plot data (signalData type is list!!!)
			signalData = None
			for channel in enabledChannel:
				if signalData is None:
					signalData = f['signal'][:, channel]
				else:
					signalData = np.column_stack((signalData, f['signal'][:, channel]))
		fig.suptitle(os.path.basename(fileName))
		# create signalDataArray from signalData
		signalDataArray = np.array(signalData)
		# check if signal contains only one channel
		if signalDataArray.ndim > 1:
			columns = signalDataArray.shape[1]
		else:
			columns = signalDataArray.ndim
		PSD = freq = idx = None
		plotRange = [1, 55]
		for column in range(columns):
			if columns > 1:
				colData = signalDataArray[:, column]
			else:
				colData = signalDataArray
			if usingElectrodes == ElectrodeType.DRY:
				# For dry electrodes, using brainflowFFT that needs data length to be power of 2
				dtLen = DataFilter.get_nearest_power_of_two(colData.shape[0])
				# chopping Data to have length equal to power of 2
				signalDataArrayChopped = np.array(colData[:dtLen].tolist())
				PSD, freq, idx, figName = calculateFFT(signalDataArrayChopped, dtLen, fs, lowCut, highCut, None, None,
				                                       fftType=FftType.brainflowFFT,
				                                       filtered=True,
				                                       filterType=FilterType.butter_bandpass_filter,
				                                       noiseCancellation=True)
				print(figName)
			elif usingElectrodes == ElectrodeType.WET:
				dtLen = colData.shape[0]
				dtLen = DataFilter.get_nearest_power_of_two(colData.shape[0])
				# chopping Data to have length equal to power of 2
				signalDataArrayChopped = np.array(colData[:dtLen].tolist())
				PSD, freq, idx, figName = calculateFFT(signalDataArrayChopped, dtLen, fs, lowCut, highCut, None, None,
				                                       fftType=FftType.pythonFFT,
				                                       filtered=True,
				                                       filterType=FilterType.butter_bandpass_filter,
				                                       noiseCancellation=False)
				print(figName)
			else:
				# TODO: RAISE UKNOWN ELECTRODE TYPE
				pass
			idx = [idx for idx, value in enumerate(freq) if plotRange[0] <= value <= plotRange[1]]
			print('Channel ' + column.__str__() + ':' +
			      ' \t SNR = ' + calculateSNR(PSD).__str__() +
			      ',\t Max = ' + max(PSD).__str__() +
			      ',\t FREQ = ' + abs(freq[idx][PSD[idx].tolist().index(max(PSD[idx].tolist()))]).__str__())
			plt.plot(freq[idx], PSD[idx], ls='-.', label=createLegends(PSD, freq, idx))

		plt.ylabel('Amplitude')
		plt.xlabel('Frequency (Hertz)')
		plt.xlim(plotRange[0], plotRange[1])
		plt.legend(prop={"size": 9})
		# ----------- Saving figures ---------------
		figureName = os.path.splitext(os.path.basename(fileName))[0]
	# plt.savefig('C:/Users/ZN/Desktop/images/' + figureName + '.png', transparent=False)
	plt.show()


def printFFT(fileNames, lowCut=4, highCut=40, fs=250, enabledChannel=None,
             usingElectrodes: ElectrodeType = ElectrodeType.DRY):
	"""
	Creates a subplot of 4 plots, one for every class in the 'signal' dataset of the current hdf5 file.

	:param [str] fileNames: List of the full paths of the Hdf5 filenames contains the training dataset
	:param [int] enabledChannel: The EEG enabled channels' data will be retrieved from the dataset.
	:param int fs: The fs will be used for the bandpass filtering.
	:param int highCut: The high cut frequency will be used for the bandpass filtering.
	:param int lowCut: The low cut frequency will be used for the bandpass filtering.
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
			plotData = None
			for channel in enabledChannel:
				if plotData is None:
					plotData = d1[:, channel]
				else:
					plotData = np.column_stack((plotData, d1[:, channel]))
			plotDataArray = np.array(plotData)
			print('Class: ' + int(
				signalDataInClassPackages[tClass][0][8]).__str__() + ' --> Shape: ' + plotDataArray.shape.__str__())

			# check if signal contains only one channel
			if plotDataArray.ndim > 1:
				columns = plotDataArray.shape[1]
			else:
				columns = plotDataArray.ndim
			PSD = freq = idx = None
			plotRange = [1, 55]
			for column in range(columns):
				if columns > 1:
					colData = plotDataArray[:, column]
				else:
					colData = plotDataArray
				if usingElectrodes == ElectrodeType.DRY:
					# For dry electrodes, using brainflowFFT that needs data length to be power of 2
					dtLen = DataFilter.get_nearest_power_of_two(colData.shape[0])
					# chopping Data to have length equal to power of 2
					signalDataArrayChopped = np.array(colData[:dtLen].tolist())
					PSD, freq, idx, figName = calculateFFT(signalDataArrayChopped, dtLen, fs, lowCut, highCut, None,
					                                       None,
					                                       fftType=FftType.brainflowFFT,
					                                       filtered=True,
					                                       filterType=FilterType.butter_bandpass_filter,
					                                       noiseCancellation=True)
					print(figName)
				elif usingElectrodes == ElectrodeType.WET:
					dtLen = colData.shape[0]
					# For dry electrodes, using brainflowFFT that needs data length to be power of 2
					dtLen = DataFilter.get_nearest_power_of_two(colData.shape[0])
					# chopping Data to have length equal to power of 2
					signalDataArrayChopped = np.array(colData[:dtLen].tolist())
					PSD, freq, idx, figName = calculateFFT(signalDataArrayChopped, dtLen, fs, lowCut, highCut, None, None,
					                                       fftType=FftType.brainflowFFT,
					                                       filtered=True,
					                                       filterType=FilterType.butter_bandpass_filter,
					                                       noiseCancellation=False)
					print(figName)
				else:
					# TODO: RAISE UKNOWN ELECTRODE TYPE
					pass
				idx = [idx for idx, value in enumerate(freq) if plotRange[0] <= value <= plotRange[1]]
				print('Channel ' + column.__str__() + ':' +
				      ' \t SNR = ' + calculateSNR(PSD).__str__() +
				      ',\t Max = ' + max(PSD).__str__() +
				      ',\t FREQ = ' + abs(freq[idx][PSD[idx].tolist().index(max(PSD[idx].tolist()))]).__str__())
				axs[subCols, subRows].plot(freq[idx], PSD[idx], ls='-.', label=createLegends(PSD, freq, idx))
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
