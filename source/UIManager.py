#!/usr/bin/python
import argparse

from pyGUI import *
from dataManager import DataManager
from multiprocessing.managers import SyncManager
from multiprocessing import Process, Queue, Lock, Event
from dotted.collection import DottedDict
from boardEventHandler import BoardEventHandler
from cyton import OpenBCICyton

parser = argparse.ArgumentParser(prog='UIManager',
                                 description='Python scripts that determines which UI will be used for the cyton board ')
parser.add_argument('-m', '--mode', nargs=1, choices=('pygui', 'online'), help='Choose the preferred mode',
                    required=True)
args = parser.parse_args()

# queues Size
maxQueueSize = 2500

# process list in queue
processesList = []


# create a SyncManager and register openbci cyton board object so as to create a proxy and share it to every subprocess
class MyManager(SyncManager):
	pass


# register the OpenBCICyton class; make its functions accessible via proxy
MyManager.register('OpenBCICyton', OpenBCICyton)


def printData(br, dataDict, _newDataAvailable):
	while True:
		_newDataAvailable.wait()
		b = br
		while not dataDict.queue.empty():
			dataDict.lock.acquire()
			try:
				dt = dataDict.queue.get()
				print(dt)
			finally:
				dataDict.lock.release()


if __name__ == '__main__':
	try:
		# create board through manager so as to have a proxy for the object to _share through processes
		manager = MyManager()
		manager.start()
		board = manager.OpenBCICyton()
		dataBuffer = manager.Queue(maxsize=maxQueueSize)
		# add the board settings in the boardCytonSettings will be given to the boardEventHandler and guiProcess
		# Through this dictionary, the board settings given from ui, will be applied to board data
		boardCytonSettings = manager.dict(board.getBoardSettingAttributes())

		# Events will be used for the dataManager
		dataManagerEvents = DottedDict({
			"share": Event(),
			"newDataAvailable": Event(),
		})

		# main queue that will read data from board
		guiProcArgs = DottedDict({"queue": Queue(maxsize=maxQueueSize), "lock": Lock()})
		printDataProcArgs = DottedDict({"queue": Queue(maxsize=maxQueueSize), "lock": Lock()})
		# add queue and lock in the lists
		processesArgsList = [guiProcArgs, printDataProcArgs]

		# init DataManager and event BoardEventHandler
		dataManager = DataManager(dataBuffer, processesArgsList, dataManagerEvents)
		boardEventHandler = BoardEventHandler(board, boardCytonSettings, dataManagerEvents,
		                                      dataBuffer)
		# events will be used to control board through any gui
		boardApiCallEvents = DottedDict(boardEventHandler.getBoardHandlerEvents())
		mode = args.mode[0]
		if mode == 'pygui':

			# create Process for the dataManager
			dataManagerProcess = Process(target=dataManager.shareData)
			processesList.append(dataManagerProcess)

			# create Process for printing Data
			printData = Process(target=printData,
			                    args=(board, printDataProcArgs, dataManagerEvents.newDataAvailable))
			processesList.append(printData)

			# create Process for the boardEventHandler
			boardEventHandlerProcess = Process(target=boardEventHandler.start)
			processesList.append(boardEventHandlerProcess)

			# create Process for the gui
			guiProcess = Process(target=startGUI,
			                     args=(guiProcArgs, board, boardApiCallEvents, boardCytonSettings))
			processesList.append(guiProcess)

			# start processes in the processList
			for proc in processesList:
				proc.start()

			# join processes in the processList
			for proc in processesList:
				proc.join()

		elif mode == 'online':
			print("online")
			dataManagerProcess = Process(target=dataManager.shareData)

			processesList.append(dataManagerProcess)
			# start processes
			for proc in processesList:
				proc.start()

			# join processes
			for proc in processesList:
				proc.join()
	except KeyboardInterrupt:
		print("Caught KeyboardInterrupt, terminating workers")
		# clearing events
		# terminate processes
		for proc in processesList:
			proc.terminate()
