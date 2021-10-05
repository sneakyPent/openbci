#!/usr/bin/python
import argparse
import os
import signal
import sys

sys.path.append('..')
from multiprocessing.managers import SyncManager
from multiprocessing import Process, Queue, Lock, Event, current_process
from source.boardEventHandler import BoardEventHandler
from source.pyGUI import startGUI
from source.training import startTraining
from source.windowing import windowing
from utils.coloringPrint import printWarning
from source.writeToFile import writing
from source.cyton import OpenBCICyton
from utils.constants import Constants as cnst
from online import *


def printData(data, _newDataAvailable, _shutdownEvent):
	"""
	* Runs simultaneously with the boardEventHandler process and waits for the writeDataEvent, which is set only by the boardEventHandler.
	* Simple process that just printing the data read from cyton board in the terminal.

	:param Queue data: Buffer used for communicating and getting the transmitted data from :py:meth:`source.boardEventHandler.BoardEventHandler.startStreaming`.
	:param Event _newDataAvailable: The event the method is waiting for, before proceeding to the next step (printing).
	:param Event _shutdownEvent: Used as condition for the method to run.
	:return: None
	"""
	while not _shutdownEvent.is_set():
		_newDataAvailable.wait(1)
		if _newDataAvailable.is_set():
			while not data.qsize() == 0:
				dt = data.get()
				print(dt)


def signal_handler(signal, frame):
	"""
	Used to catch the ctrl^c signal to stop the application via shutdownEvent
	"""
	if type(current_process()) != Process:
		shutdownEvent.set()
		printWarning("shuttingDown")


shutdownEvent = Event()


def uiManager():
	"""
	* It's the main process to run
	* Creates every other process needed for main use.

		1. boardEventHandlerProcess
		2. guiProcess
		3. printDataProcess
		4. writeProcess
		5. windowingProcess
		6. trainingProcess
	"""
	# register the OpenBCICyton class; make its functions accessible via proxy
	SyncManager.register('OpenBCICyton', OpenBCICyton)

	parser = argparse.ArgumentParser(prog='UIManager',
	                                 description='Python scripts that determines which UI will be used for the cyton board ')
	parser.add_argument('-m', '--mode', nargs=1, choices=('pygui', 'online'), help='Choose the preferred mode',
	                    required=True)
	args = parser.parse_args()

	# process list in queue
	processesList = []

	# main events
	writeDataEvent = Event()

	newDataAvailable = Event()
	startTrainingEvent = Event()
	startOnlineEvent = Event()

	windowedDataBuffer = Queue(maxsize=cnst.writeDataMaxQueueSize)
	# Queue for the communication between socket and boardEventHandler
	trainingClassBuffer = Queue(maxsize=1)

	# catch keyboardinterupt exception and just set shutdownEvent
	signal.signal(signal.SIGINT, signal_handler)
	# create board through manager so as to have a proxy for the object to _share through processes
	manager = SyncManager()
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
	# add queues in the list
	# dataBuffersList = [writingBuffer, windowingBuffer, printBuffer, guiBuffer]
	dataBuffersList = [writingBuffer, windowingBuffer, guiBuffer]

	# Create a BoardEventHandler Instance
	boardEventHandler = BoardEventHandler(board, boardCytonSettings, newDataAvailable, dataBuffersList, writeDataEvent,
	                                      trainingClassBuffer, shutdownEvent)
	# events will be used to control board through any gui
	boardApiCallEvents = boardEventHandler.getBoardHandlerEvents()

	mode = args.mode[0]
	if mode == 'pygui':

		# create Process for printing Data
		printDataProcess = Process(target=printData, name='printData',
		                           args=(printBuffer, newDataAvailable, shutdownEvent))
		processesList.append(printDataProcess)

		# create Process for the boardEventHandler
		boardEventHandlerProcess = Process(target=boardEventHandler.start, name='boardEventHandler', )
		processesList.append(boardEventHandlerProcess)

		# create Process for the gui
		guiProcess = Process(target=startGUI, name='startGUI',
		                     args=(guiBuffer, newDataAvailable, board, boardApiCallEvents,
		                           boardCytonSettings, shutdownEvent, writeDataEvent, startTrainingEvent,
								   startOnlineEvent))
		processesList.append(guiProcess)

		# create Process to write data from board to file
		writeProcess = Process(target=writing, name='writing',
		                       args=(board, writingBuffer, windowedDataBuffer, writeDataEvent, shutdownEvent))
		processesList.append(writeProcess)

		# create Process for the windowing data
		windowingProcess = Process(target=windowing, name='windowing',
		                           args=(board, windowingBuffer, windowedDataBuffer, newDataAvailable, shutdownEvent))
		processesList.append(windowingProcess)

		# create Process for connecting to unity program socket
		trainingProcess = Process(target=startTraining, name='training',
		                          args=(
			                          board, startTrainingEvent, boardApiCallEvents, shutdownEvent,
			                          trainingClassBuffer))
		processesList.append(trainingProcess)

		# create Process for connecting to unity program socket fro online session
		onlineProcess = Process(target=startOnline, name='online',
								  args=(
									  board, startOnlineEvent, boardApiCallEvents, shutdownEvent,
									  trainingClassBuffer))
		processesList.append(onlineProcess)

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


if __name__ == '__main__':
	uiManager()
