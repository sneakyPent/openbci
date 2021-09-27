import h5py
import numpy as np

from utils.coloringPrint import printInfo, printError, printWarning
from utils.constants import getSessionFilename


def writing(board, writeBuf, windowedData, writeDataEvent, _shutdownEvent):
	"""
	* Runs simultaneously with the boardEventHandler process and waits for the writeDataEvent, which is set only by the boardEventHandler.
	* Creates an hdf5 file with name specified by dateTime.
	* The hdf5 file contains 2 datasets

		1. The unfiltered and unprocessed data samples as read by the cyton board, named ”signal”.
		2. The same data as “signal” but in this dataset the data are broken into windows, named “packages”.

	:param OpenBCICyton board: Represents the OpenBCICyton class
	:param Queue writeBuf: Buffer used for communicating and getting the transmitted data from :py:meth:`source.boardEventHandler.BoardEventHandler.startStreaming`.
	:param Queue windowedData: Buffer used for communicating and getting the windowed Data data from :py:meth:`source.windowing.windowing`.
	:param Event writeDataEvent: The event the method is waiting for, before proceeding to the next step (writing into the file). Sets only by :py:meth:`source.boardEventHandler.BoardEventHandler.stopStreaming`
	:param Event _shutdownEvent: Used as condition for the method to run.

	:return: None
	"""
	while not _shutdownEvent.is_set():
		writeDataEvent.wait(1)
		if writeDataEvent.is_set():
			printInfo('Start writing data into file...')
			signal = []
			windowedSignal = []
			filename = getSessionFilename(training=board.isTrainingMode())
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
			hf.create_dataset("packages", data=windowedSignal)
			printInfo("Finish with windowed signal")
			utf8_type = h5py.string_dtype('utf-8', 100)
			boardSettings = np.array(list(board.getBoardSettings().items()), dtype=utf8_type)
			hf.create_dataset("settings", data=boardSettings)
			printInfo("Finish with settings")
			hf.close()
			writeDataEvent.clear()
		if _shutdownEvent.is_set():
			break
