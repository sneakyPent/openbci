#!/usr/bin/python
import argparse
import os
import signal

from pyGUI import *
from dataManager import DataManager
from multiprocessing.managers import SyncManager
from multiprocessing import Process, Queue, Lock, Event, current_process
from dotted.collection import DottedDict
from boardEventHandler import BoardEventHandler
from writeToFile import writing
from cyton import OpenBCICyton

parser = argparse.ArgumentParser(prog='UIManager',
                                 description='Python scripts that determines which UI will be used for the cyton board ')
parser.add_argument('-m', '--mode', nargs=1, choices=('pygui', 'online'), help='Choose the preferred mode',
                    required=True)
args = parser.parse_args()

# queues Size
maxQueueSize = 2500
writeDataMaxQueueSize = maxQueueSize * 100  # approximate 15 minutes of streaming

# process list in queue
processesList = []

# main events
writeDataEvent = Event()
shutdownEvent = Event()
closeGui = Event()


# create a SyncManager and register openbci cyton board object so as to create a proxy and share it to every subprocess
class MyManager(SyncManager):
	pass


# register the OpenBCICyton class; make its functions accessible via proxy
MyManager.register('OpenBCICyton', OpenBCICyton)


def printData(br, dataDict, _newDataAvailable, _shutdownEvent):
	while not _shutdownEvent.is_set():
		_newDataAvailable.wait(1)
		if _newDataAvailable.is_set():
			b = br
			while not dataDict.queue.empty():
				dataDict.lock.acquire()
				try:
					dt = dataDict.queue.get()
					print(dt)
				finally:
					dataDict.lock.release()


def signal_handler(signal, frame):
	if type(current_process()) != Process:
		shutdownEvent.set()
		printWarning("shuttingDown")


if __name__ == '__main__':
	if not os.path.exists(cnst.destinationFolder):
		os.makedirs(cnst.destinationFolder)

	# catch keyboardinterupt exception and just set shutdownEvent
	signal.signal(signal.SIGINT, signal_handler)
	# create board through manager so as to have a proxy for the object to _share through processes
	manager = MyManager()
	manager.start()
	board = manager.OpenBCICyton()
	dataBuffer = manager.Queue(maxsize=maxQueueSize)

	# add the board settings in the boardCytonSettings will be given to the boardEventHandler and guiProcess
	# Through this dictionary, the board settings given from ui, will be applied to board data
	boardCytonSettings = manager.dict(board.getBoardSettingAttributes())

	# main queue that will read data from board
	guiProcArgs = DottedDict({"queue": Queue(maxsize=maxQueueSize), "lock": Lock()})
	printDataProcArgs = DottedDict({"queue": Queue(maxsize=maxQueueSize), "lock": Lock()})
	writeDataProcArgs = DottedDict({"queue": Queue(maxsize=maxQueueSize * 100), "lock": Lock()})
	# add queue and lock in the lists
	# processesArgsList = [guiProcArgs, printDataProcArgs, writeDataProcArgs]
	# processesArgsList = [printDataProcArgs, writeDataProcArgs]
	processesArgsList = [writeDataProcArgs]
	# processesArgsList = [printDataProcArgs]

	# Create a DataManager Instance
	dataManager = DataManager(dataBuffer, processesArgsList)
	# Events will be used for the dataManager
	dataManagerEvents = DottedDict(dataManager.getDataManagerEvents())
	# Create a BoardEventHandler Instance
	boardEventHandler = BoardEventHandler(board, boardCytonSettings, dataManagerEvents, dataBuffer,writeDataEvent)
	# events will be used to control board through any gui
	boardApiCallEvents = DottedDict(boardEventHandler.getBoardHandlerEvents())

	mode = args.mode[0]
	if mode == 'pygui':

		# create Process for the dataManager
		dataManagerProcess = Process(target=dataManager.shareData, args=(shutdownEvent,))
		processesList.append(dataManagerProcess)

		# create Process for printing Data
		printData = Process(target=printData,
		                    args=(board, printDataProcArgs, dataManagerEvents.newDataAvailable, shutdownEvent))
		# processesList.append(printData)

		# create Process for the boardEventHandler
		boardEventHandlerProcess = Process(target=boardEventHandler.start, args=(shutdownEvent,))
		processesList.append(boardEventHandlerProcess)

		# create Process for the gui
		guiProcess = Process(target=startGUI,
		                     args=(guiProcArgs, dataManagerEvents.newDataAvailable, board, boardApiCallEvents,
		                           boardCytonSettings, shutdownEvent, writeDataEvent))
		processesList.append(guiProcess)

		# create Process to write data from board to file
		writeProcess = Process(target=writing, args=(board, writeDataProcArgs, writeDataEvent, shutdownEvent))
		processesList.append(writeProcess)
		# start processes in the processList
		for proc in processesList:
			proc.start()

		# join processes in the processList
		for proc in processesList:
			proc.join()

	elif mode == 'online':
		print("online")
		# start processes
		for proc in processesList:
			proc.start()

		# join processes
		for proc in processesList:
			proc.join()
