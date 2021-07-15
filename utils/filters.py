from scipy import signal
import numpy as np


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


# Notch Filter
def notch_filter(val, data, fs=250):
	notch_freq_Hz = np.array([float(val)])
	for freq_Hz in np.nditer(notch_freq_Hz):
		bp_stop_Hz = freq_Hz + 3.0 * np.array([-1, 1])
		b, a = signal.butter(3, bp_stop_Hz / (fs / 2.0), 'bandstop')
		fin = data = signal.lfilter(b, a, data)
	return fin
