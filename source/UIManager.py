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
runningProcesses = []
def printData(dataDict, _newDataAvailable):
    while True:
        _newDataAvailable.wait()
        while not dataDict.queue.empty():
            dataDict.lock.acquire()
            try:
                dt = dataDict.queue.get()
                print("printData func:" + dt.__str__())
            finally:
                dataDict.lock.release()


if __name__ == '__main__':
    try:
        # main queue that will read data from board
        data = Queue(maxsize=maxQueueSize)
        # create Other Processes queues an their locks in dictionary format and append them in the list
        guiProcArgs = DottedDict({"queue": Queue(maxsize=maxQueueSize), "lock": Lock()})
        printDataProcArgs = DottedDict({"queue": Queue(maxsize=maxQueueSize), "lock": Lock()})
        # add queue and lock in the lists
        processesArgsList = [guiProcArgs, printDataProcArgs]
        # init DataManager
        dataManager = DataManager(data, processesArgsList, _share, _newDataAvailable)

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
