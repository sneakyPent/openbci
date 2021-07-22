import numpy as np

from utils.coloringPrint import printInfo, printWarning, printError


def windowing(board, windowingBuf, windowedData, newDataAvailable, _shutdownEvent):
	windowCounter = 0
	currentWindowList = []
	while not _shutdownEvent.is_set():
		newDataAvailable.wait(1)
		# the desired package-window size (windowSize*sampleRate) EG: 1*250
		window = board.getWindow()
		# the desired step size for each package
		step = board.getWindowStep()
		if newDataAvailable.is_set():
			while not windowingBuf.empty():
				dt = windowingBuf.get()
				currentWindowList.append(dt)
				# append until the package size, then put in queue and remove the first "step" samples
				if len(currentWindowList) == window:
					printWarning("created window No." + windowCounter.__str__())
					windowCounter += 1
					windowedData.put(np.copy(currentWindowList).tolist())
					del currentWindowList[0:step]
