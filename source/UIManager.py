#!/usr/bin/python
import argparse
import os
import signal

from pyGUI import *
from multiprocessing.managers import SyncManager
from multiprocessing import Process, Queue, Lock, Event, current_process
from dotted.collection import DottedDict
from boardEventHandler import BoardEventHandler
from source.mySocket import connectTraining
from source.windowing import windowing
from utils.coloringPrint import printWarning
from writeToFile import writing
from cyton import OpenBCICyton
from utils.constants import Constants as cnst

parser = argparse.ArgumentParser(prog='UIManager',
                                 description='Python scripts that determines which UI will be used for the cyton board ')
parser.add_argument('-m', '--mode', nargs=1, choices=('pygui', 'online'), help='Choose the preferred mode',
                    required=True)
args = parser.parse_args()

# process list in queue
processesList = []

# main events
writeDataEvent = Event()
shutdownEvent = Event()
newDataAvailable = Event()

windowedDataBuffer = Queue(maxsize=cnst.writeDataMaxQueueSize)
# Queue for the communication between socket and boardEventHandler
trainingClassBuffer = Queue(maxsize=1)


# create a SyncManager and register openbci cyton board object so as to create a proxy and share it to every subprocess
class MyManager(SyncManager):
	pass


# register the OpenBCICyton class; make its functions accessible via proxy
MyManager.register('OpenBCICyton', OpenBCICyton)


def printData(data, _newDataAvailable, _shutdownEvent):
	while not _shutdownEvent.is_set():
		_newDataAvailable.wait(1)
		if _newDataAvailable.is_set():
			while not data.qsize() == 0:
				dt = data.get()
				print(dt)


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

	# add the board settings in the boardCytonSettings will be given to the boardEventHandler and guiProcess
	# Through this dictionary, the board settings given from ui, will be applied to board data
	boardCytonSettings = manager.dict(board.getBoardSettingAttributes())

	# main queue that will read data from board
	guiBuffer = Queue(maxsize=cnst.maxQueueSize)
	printBuffer = Queue(maxsize=cnst.maxQueueSize)
	writingBuffer = Queue(maxsize=cnst.writeDataMaxQueueSize)
	windowingBuffer = Queue(maxsize=cnst.writeDataMaxQueueSize)
	# add queue and lock in the lists
	dataBuffersList = [writingBuffer, windowingBuffer, printBuffer]

	# Create a BoardEventHandler Instance
	boardEventHandler = BoardEventHandler(board, boardCytonSettings, newDataAvailable, dataBuffersList, writeDataEvent,trainingClassBuffer)
	# events will be used to control board through any gui
	boardApiCallEvents = DottedDict(boardEventHandler.getBoardHandlerEvents())

	mode = args.mode[0]
	if mode == 'pygui':

		# create Process for printing Data
		printData = Process(target=printData, name='printData',
		                    args=(printBuffer, newDataAvailable, shutdownEvent))
		processesList.append(printData)

		# create Process for the boardEventHandler
		boardEventHandlerProcess = Process(target=boardEventHandler.start, name='boardEventHandler',
		                                   args=(shutdownEvent,))
		processesList.append(boardEventHandlerProcess)

		# create Process for the gui
		guiProcess = Process(target=startGUI, name='startGUI',
		                     args=(guiBuffer, newDataAvailable, board, boardApiCallEvents,
		                           boardCytonSettings, shutdownEvent, writeDataEvent))
		processesList.append(guiProcess)

		# create Process to write data from board to file
		writeProcess = Process(target=writing, name='writing',
		                       args=(writingBuffer, windowedDataBuffer, writeDataEvent, shutdownEvent))
		processesList.append(writeProcess)

		# create Process for the windowing data
		windowingProcess = Process(target=windowing, name='windowing',
		                           args=(board, windowingBuffer, windowedDataBuffer, newDataAvailable, shutdownEvent))
		processesList.append(windowingProcess)

		# create Process for connecting to unity program socket
		socketProcess = Process(target=connectTraining, name='training',
		                        args=(trainingClassBuffer,))
		processesList.append(socketProcess)

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
