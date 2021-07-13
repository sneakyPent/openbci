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
            # create other processes
            dataManagerProcess = Process(target=dataManager.shareData)
            guiProcess = Process(target=startGUI, args=(guiProcArgs, _share, _newDataAvailable))
            printData = Process(target=printData, args=(printDataProcArgs, _newDataAvailable))

            # start processes
            guiProcess.start()
            dataManagerProcess.start()
            printData.start()

            # add processes in the running process list
            runningProcesses.append(guiProcess)
            runningProcesses.append(dataManagerProcess)
            runningProcesses.append(printData)

            # join processes
            guiProcess.join()
            dataManagerProcess.join()
            printData.join()
        elif mode == 'online':
            print("online")
            dataManagerProcess = Process(target=dataManager.shareData)
            dataManagerProcess.start()
            runningProcesses.append(dataManagerProcess)
            dataManagerProcess.join()
    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt, terminating workers")
        # clearing events
        _newDataAvailable.clear()
        _share.clear()
        # terminate processes
        for proc in runningProcesses:
            proc.terminate()
