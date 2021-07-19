import h5py

from utils.coloringPrint import printInfo
from utils.constants import dateTimeFilename


def writing(br, dataDict, writeDataEvent, _shutdownEvent ):
	while not _shutdownEvent.is_set():
		writeDataEvent.wait(1)
		if writeDataEvent.is_set():
			printInfo('Start writing data into file...')
			signal = []
			filename = dateTimeFilename()
			print(filename)
			hf = h5py.File(filename + '.hdf5', 'w')
			while not dataDict.queue.empty():
				dataDict.lock.acquire()
				try:
					dt = dataDict.queue.get()
					signal.append(dt)
				finally:
					dataDict.lock.release()
			hf.create_dataset("signal", data=signal)
			print("Finish with signal")
			hf.close()
			writeDataEvent.clear()
		if _shutdownEvent.is_set():
			break


