import traceback

import numpy as np
from utils.general import emptyQueue

from utils.coloringPrint import printInfo, printWarning, printError


def windowing(board, windowingBuf, windowedData, newDataAvailable, _shutdownEvent, writeDataEvent):
	"""
	* Runs simultaneously with the boardEventHandler process and waits for the newDataAvailable event.
	* Creates windows according to :py:data:`board` object's windowSize and stepSize.
	* Puts every created window into the :py:data:`windowedData` buffer.
	* Every created window is a 3d numpy array as [number of windows][window size][sample size].

	:param board: :py:class:`source.cyton.OpenBCICyton` object created from :py:class:`source.UIManager`.
	:param Queue windowingBuf: Buffer used for communicating and getting the transmitted data from :py:meth:`source.boardEventHandler.BoardEventHandler.startStreaming`.
	:param Queue windowedData: Buffer used for communicating and passing the windowed data to :py:meth:`source.writeToFile.writing`.
	:param Event newDataAvailable: The event the method is waiting for, before proceeding to the next step (windowing).
	:param Event _shutdownEvent: Used as condition for the method to run.
	:return: None
	"""
	windowCounter = 0
	currentWindowList = []
	while not _shutdownEvent.is_set():
		if not board.isStreaming() and not writeDataEvent.is_set():
			emptyQueue(windowedData)
			currentWindowList = []
		newDataAvailable.wait(1)
		# the desired package-window size (windowSize*sampleRate) EG: 1*250
		window = board.getWindow()
		# the desired step size for each package
		step = board.getWindowStep()
		if not board.isStreaming():
			currentWindowList = []
		if newDataAvailable.is_set():
			while not windowingBuf.empty():
				dt = windowingBuf.get()
				currentWindowList.append(dt)
				# append until the package size, then put in queue and remove the first "step" samples
				if len(currentWindowList) == window:
					# printWarning("created window No." + windowCounter.__str__())
					windowCounter += 1
					windowedData.put(np.copy(currentWindowList))
					del currentWindowList[0:step]
	# empty buffers
	emptyQueue(windowedData)
