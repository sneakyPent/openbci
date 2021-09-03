import h5py
import numpy as np

from utils.coloringPrint import printInfo, printError, printWarning
from utils.constants import dateTimeFilename


def writing(writeBuf, windowedData, writeDataEvent, _shutdownEvent):
	while not _shutdownEvent.is_set():
		writeDataEvent.wait(1)
		if writeDataEvent.is_set():
			printInfo('Start writing data into file...')
			signal = []
			windowedSignal = []
			filename = dateTimeFilename()
			print(filename)
			hf = h5py.File(filename + '.hdf5', 'w')
			printWarning('signal buffer size: ' + writeBuf.qsize().__str__())
			while not writeBuf.qsize() == 0:
				dt = writeBuf.get()
				signal.append(dt)
			signal = np.array(signal).astype(float)
			hf.create_dataset("signal", data=signal)
			printInfo("Finish with signal")
			printWarning('windowData buffer size: ' + windowedData.qsize().__str__())
			while not windowedData.qsize() == 0:
				dt = windowedData.get()
				windowedSignal.append(dt)
			windowedSignal = np.array(windowedSignal).astype(float)
			hf.create_dataset("windowed", data=windowedSignal)
			printInfo("Finish with windowed signal")
			hf.close()
			writeDataEvent.clear()
		if _shutdownEvent.is_set():
			break
