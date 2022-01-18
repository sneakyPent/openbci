"""
Consist of 3 method
	* connectTraining
	* startTrainingApp
	* startTraining

used only for the training and in order to run it needs the unity target executable.

"""
import queue
import socket
import subprocess
import os
import time
from multiprocessing import Process, Event
from utils.coloringPrint import printError, printInfo, printWarning
from utils.constants import Constants as cnst, TargetPlatform
from utils.general import emptyQueue
from source.SSVEPexperiment import SSVEP_screen_session


def connectTraining(board, boardApiCallEvents, startTrainingEvent, currentClassBuffer, socketConnection,
                    _shutdownEvent):
	"""
	* Wait for startTrainingEvent to get set.
	* Responsible

		* to create a socket communication with the target executable.
		* to receive the training class byte from the open connection.
		* to put the receiving byte into currentClassBuffer parameter.
		* to set the socketConnection event, only if socket connection established. When set,  the :py:meth:`source.training.startTrainingApp` process and the :py:meth:`source.boardEventHandler.BoardEventHandler.startStreaming` can be start.

	* When the connection could not be established then wait for 10 sec and then retrying.

	:param OpenBCICyton board: Represents the OpenBCICyton object created from :py:class:`source.UIManager`.
	:param [Event] boardApiCallEvents: Events used in :py:class:`source.boardEventHandler.BoardEventHandler`
	:param Event startTrainingEvent: Event for which this method will be waiting. This Event is set only by the :py:meth:`source.pyGUI.GUI.trainingButtonClick`
	:param Queue currentClassBuffer: Buffer used to 'give' the training class to :meth:`source.boardEventHandler.BoardEventHandler.startStreaming`.
	:param Event socketConnection: Used as flag so the main process :py:meth:`source.training.startTraining` can proceed to start the streaming and the training application.
	:param Event _shutdownEvent: Event used to know when to allow every running process terminate

	"""
	while not _shutdownEvent.is_set():
		startTrainingEvent.wait(1)
		if startTrainingEvent.is_set():
			if not board.isConnected():
				printWarning('Could not start training without connected Board.')
				startTrainingEvent.clear()
				continue
			emptyQueue(currentClassBuffer)
			# create socket
			s = socket.socket()
			socket.setdefaulttimeout(None)
			printInfo('socket created ')

			# IP and PORT connection
			port = 8080
			while not socketConnection.is_set():
				try:
					# s.bind(('139.91.190.32', port)) #local host
					s.bind(('127.0.0.1', port))  # local host
					s.listen(30)  # listening for connection for 30 sec?
					printInfo('socket listening ... ')
					socketConnection.set()
					# try:
					c, addr = s.accept()  # when port connected
					printInfo("Got connection from " + addr.__str__())

					# 1st communication with Quest
					bytes_received = c.recv(1024)  # received bytes
					printInfo(bytes_received.decode("utf-8"))

					# Send "True" string to start the Quest app
					nn_output = "True"
					arr2 = bytes(nn_output, 'utf-8')
					c.sendall(arr2)  # sending back

					board.setTrainingMode(True)
					boardApiCallEvents["startStreaming"].set()

					# Quest sends the arrow number
					bytes_received = c.recv(1).decode("utf-8")  # received bytes
					# print(bytes_received)
					currentClassBuffer.put_nowait(bytes_received)
					if bytes_received != "E" and bytes_received != "":
						# q_label.put(int(bytes_received))
						bytes_received_old = bytes_received
						while True:  # bytes_received != "E": # "E" means end of the action
							bytes_received = c.recv(1).decode("utf-8")  # received bytes
							if bytes_received == "E" or bytes_received == "":
								printInfo('Received termination byte from application.Stop training...')
								break
							else:
								if bytes_received != bytes_received_old:
									currentClassBuffer.put_nowait(bytes_received)
									bytes_received_old = bytes_received

					c.shutdown(socket.SHUT_RDWR)
					c.close()
				except queue.Full as ex:
					printError('Full queue.Stop training...' + ex.__str__())
					c.shutdown(socket.SHUT_RDWR)
					c.close()
					continue
				except socket.error as error:
					printWarning(error.__str__() + '. Wait for 10 seconds before trying again')
					time.sleep(10)
					pass
			socketConnection.clear()
			startTrainingEvent.clear()


def startTrainingApp(boardApiCallEvents, socketConnection, _shutdownEvent):
	"""
	* waits until socketConnection get set by :py:meth:`source.training.connectTraining`
	* Executes the unity target executable given in :data:`utils.constants.Constants.trainingUnityExePath`
	* Stop streaming after exiting unity target, via boardApiCallEvents

	:param boardApiCallEvents: Events used in :py:class:`source.boardEventHandler.BoardEventHandler`
	:param Event socketConnection: Used as flag so the method can proceed to start the training application.
	:param Event _shutdownEvent: Event used to know when to allow every running process terminate

	"""
	while not _shutdownEvent.is_set():
		socketConnection.wait(1)
		if socketConnection.is_set():
			with open(os.devnull, 'wb') as devnull:
				subprocess.check_call([cnst.trainingUnityExePath], stdout=devnull, stderr=subprocess.STDOUT)
			boardApiCallEvents["stopStreaming"].set()


def startTraining(board, startTrainingEvent, boardApiCallEvents, _shutdownEvent, currentClassBuffer, targetPlatform=TargetPlatform.PSYCHOPY):
	"""
	* Method runs via trainingProcess in :py:mod:`source.UIManager`
	* Runs simultaneously with the boardEventHandler process.
	* Starts two subprocesses

		1. socketProcess runs :py:meth:`source.training.connectTraining`
		2. startTRainingApp :py:meth:`source.training.startTrainingApp`

	:param OpenBCICyton board: Represents the OpenBCICyton object created from :py:class:`source.UIManager`.
	:param Event startTrainingEvent: Event for which socketProcess will be waiting, This Event is set only by the :py:meth:`source.pyGUI.GUI.trainingButtonClick`
	:param [Event] boardApiCallEvents:  Events used in :py:class:`source.boardEventHandler.BoardEventHandler`
	:param Event _shutdownEvent: Event used to know when to let every running process terminate
	:param Queue currentClassBuffer: Buffer will be used to pass the training class to :meth:`source.boardEventHandler.BoardEventHandler.startStreaming`, via :meth:`source.training.connectTraining`
	:param TargetPlatform targetPlatform: Choose whether the target will executed using unity or psychopy library. 
	"""
	procList = []
	
	if targetPlatform == TargetPlatform.UNITY:
		socketConnection = Event()
		socketConnection.clear()
		
		socketProcess = Process(target=connectTraining,
		                        args=(board, boardApiCallEvents, startTrainingEvent,
		                              currentClassBuffer, socketConnection, _shutdownEvent,))
		procList.append(socketProcess)
		applicationProcess = Process(target=startTrainingApp, args=(boardApiCallEvents, socketConnection, _shutdownEvent,))
		
		procList.append(applicationProcess)   
	elif targetPlatform == TargetPlatform.PSYCHOPY:
		mode = False
		board.setTrainingMode(True)
		applicationProcess = Process(target=SSVEP_screen_session,
									args=(board, startTrainingEvent, boardApiCallEvents, _shutdownEvent,
										  currentClassBuffer, cnst.targetDuration, cnst.frames_ch, mode))
		procList.append(applicationProcess)	
	
	for proc in procList:
		proc.start()

	# join processes
	for proc in procList:
		proc.join()
