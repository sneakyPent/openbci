from scipy import signal
import numpy as np
from brainflow import DataFilter, NoiseTypes, FilterTypes
from utils.constants import FilterType


# Bandpass filter
def bandpass(data, start, stop, fs):
	bp_Hz = np.array([start, stop])
	b, a = signal.butter(5, bp_Hz / (fs / 2.0), btype='bandpass')
	return signal.lfilter(b, a, data, axis=0)


def butter_bandpass(lowcut, highcut, fs, order=5):
	# ************************************************** Resolve the order issue!!! ********************************
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


def filterDryElectrodes(signalData, samplingRate, lowBandBound, highBandBound, order=None):
	filteredData, _ = filteringCases(signalData, samplingRate, lowBandBound, highBandBound, filtered=True,
	                                 filterType=FilterType.butter_bandpass_filter, noiseCancellation=True, order=order)
	return filteredData


def filterWetElectrodes(signalData, samplingRate, lowBandBound, highBandBound, order=None):
	filteredData, _ = filteringCases(signalData, samplingRate, lowBandBound, highBandBound, filtered=True,
	                                 filterType=FilterType.butter_bandpass_filter, noiseCancellation=False, order=order)
	return filteredData


def filteringCases(signalData, samplingRate, lowBandBound, highBandBound, filtered: bool, filterType: FilterType,
                   noiseCancellation: bool, centerFreq=None, bandwidth=None, order=None):
	data = np.copy(signalData)
	filterTypeFigureText = ', without filtering'
	noiseCancellationFigureText = ', without noise cancellation'

	if noiseCancellation:
		if signalData.ndim > 1:
			for column in range(signalData.shape[1]):
				DataFilter.remove_environmental_noise(data[:, column], samplingRate, NoiseTypes.FIFTY.value)
		else:
			DataFilter.remove_environmental_noise(data, samplingRate, NoiseTypes.FIFTY.value)
		noiseCancellationFigureText = ', noise Cancellation applied (brainflow remove_environmental_noise)'

	if filtered:
		if filterType == FilterType.brainflow_bandpass:
			if order is None:
				order = 5
			DataFilter.perform_bandpass(data, samplingRate, centerFreq, bandwidth, order, FilterTypes.BESSEL.value, 1)
			filterTypeFigureText = ', data filtered with brainflow bandpass centerFreq=' + centerFreq.__str__() + ' bandwidth= ' \
			                       + bandwidth.__str__() + ' and order=' + order.__str__()
		elif filterType == FilterType.butter_bandpass_filter:
			if order is None:
				order = 10
			data = butter_bandpass_filter(data, lowBandBound, highBandBound, samplingRate, order=order)
			filterTypeFigureText = ', data filtered with butter bandpass ' + lowBandBound.__str__() + '-' \
			                       + highBandBound.__str__() + ' and order=' + order.__str__()
		elif filterType == FilterType.lowpass_highpass:
			if order is None:
				order = 5
			if signalData.ndim > 1:
				for column in range(data.shape[1]):
					DataFilter.perform_lowpass(data[:, column], samplingRate, highBandBound, order,
					                           FilterTypes.BUTTERWORTH.value,
					                           1)
					DataFilter.perform_highpass(data[:, column], samplingRate, lowBandBound, order,
					                            FilterTypes.BUTTERWORTH.value,
					                            1)
			else:
				DataFilter.perform_lowpass(data, samplingRate, highBandBound, order, FilterTypes.BUTTERWORTH.value, 1)
				DataFilter.perform_highpass(data, samplingRate, lowBandBound, order, FilterTypes.BUTTERWORTH.value, 1)
			filterTypeFigureText = ', data filtered with highpass ' + lowBandBound.__str__() + ' and lowpass ' \
			                       + highBandBound.__str__() + ' filters independently and order=' + order.__str__()
	filterDescription = filterTypeFigureText + noiseCancellationFigureText
	return data, filterDescription
