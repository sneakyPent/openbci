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
from utils.coloringPrint import printError
from utils.constants import Constants as cnst


def connectTraining(trainingClassBuffer, socketConnection):
	"""
	* Responsible

		* to create a socket communication with the target executable.
		* to receive the training class byte from the open connection.
		* to put the receiving byte into trainingClassBuffer parameter.
		* to set the socketConnection event, only if socket connection established. When set,  the :py:meth:`source.training.startTrainingApp` process and the :py:meth:`source.boardEventHandler.BoardEventHandler.startStreaming` can be start.

	* When the connection could not be established then wait for 10 sec and then retrying.

	:param Queue(maxsize=1) trainingClassBuffer: Buffer used to 'give' the training class to :meth:`source.boardEventHandler.BoardEventHandler.startStreaming`.
	:param Event socketConnection: Used as flag so the main process :py:meth:`source.training.startTraining` can proceed to start the streaming and the training application.

	"""
	# create socket
	s = socket.socket()
	socket.setdefaulttimeout(None)
	print('socket created ')

	# IP and PORT connection
	port = 8080
	while not socketConnection.is_set():
		try:
			# s.bind(('139.91.190.32', port)) #local host
			s.bind(('127.0.0.1', port))  # local host
			s.listen(30)  # listening for connection for 30 sec?
			print('socket listensing ... ')
			socketConnection.set()
			# try:
			c, addr = s.accept()  # when port connected
			print("\ngot connection from ", addr)

			# 1st communication with Quest
			bytes_received = c.recv(1024)  # received bytes
			print(bytes_received.decode("utf-8"))

			# Send "True" string to start the Quest app
			nn_output = "True"
			arr2 = bytes(nn_output, 'utf-8')
			c.sendall(arr2)  # sending back

			# Quest sends the arrow number
			bytes_received = c.recv(1).decode("utf-8")  # received bytes
			# print(bytes_received)
			try:
				trainingClassBuffer.put_nowait(bytes_received)
			except queue.Full as error:
				print(error)
				c.shutdown(socket.SHUT_RDWR)
				c.close()
				continue

			if bytes_received != "E" and bytes_received != "":

				# q_label.put(int(bytes_received))
				bytes_received_old = bytes_received

				while True:  # bytes_received != "E": # "E" means end of the action

					bytes_received = c.recv(1).decode("utf-8")  # received bytes

					if bytes_received == "E" or bytes_received == "":
						break
					else:
						if bytes_received != bytes_received_old:
							# print(bytes_received)
							try:
								trainingClassBuffer.put_nowait(bytes_received)
							except queue.Full:
								c.shutdown(socket.SHUT_RDWR)
								c.close()
								continue
							bytes_received_old = bytes_received

			c.shutdown(socket.SHUT_RDWR)
			c.close()
		except socket.error as error:
			print(error.__str__() + '. Wait for 10 seconds before trying again')
			time.sleep(10)
			pass
	socketConnection.clear()


def startTrainingApp(boardApiCallEvents):
	"""
	Simple method, that only executes the unity target executable given in :data:`utils.constants.Constants.unityExePath`

	:param boardApiCallEvents: Events used in :py:class:`source.boardEventHandler.BoardEventHandler`

	"""
	with open(os.devnull, 'wb') as devnull:
		subprocess.check_call([cnst.unityExePath], stdout=devnull, stderr=subprocess.STDOUT)
	boardApiCallEvents["stopStreaming"].set()


def startTraining(board, startTrainingEvent, boardApiCallEvents, _shutdownEvent, trainingClassBuffer):
	"""
	* Method runs via trainingProcess in :py:mod:`source.UIManager`
	* Runs simultaneously with the boardEventHandler process and waits for the startTrainingEvent, which is set only by the boardEventHandler.
	* When the startTrainingEvent is set:

		* Starts streaming from existing connection.
		* Starts the connectTraining process.
		* Starts the startTrainingApp process.


	:param OpenBCICyton board: Represents the OpenBCICyton class
	:param Event startTrainingEvent: Event which this process will be waiting for, before starting the connectTraining, startTrainingApp processes. This Event is set only by the :py:meth:`source.pyGUI.GUI.trainingButtonClick`
	:param [Event] boardApiCallEvents:  Events used in :py:class:`source.boardEventHandler.BoardEventHandler`
	:param Event _shutdownEvent: Event used to know when to let every running process terminate
	:param Queue trainingClassBuffer: Buffer will be used to 'give' the training class to :meth:`source.boardEventHandler.BoardEventHandler.startStreaming`, via :meth:`source.training.connectTraining`
	"""
	socketConnection = Event()
	socketConnection.clear()

	socketProcess = Process(target=connectTraining, args=(trainingClassBuffer, socketConnection,))
	applicationProcess = Process(target=startTrainingApp, args=(boardApiCallEvents,))
	while not _shutdownEvent.is_set():
		startTrainingEvent.wait(1)
		if startTrainingEvent.is_set():
			if not board.isConnected():
				printError('Could not start straining without connected Board.')
				startTrainingEvent.clear()
				continue
			while not trainingClassBuffer.qsize() == 0:
				trainingClassBuffer.get_nowait()
			if not socketProcess.is_alive():
				socketProcess.start()
			socketConnection.wait(1)
			if socketConnection.is_set():
				boardApiCallEvents["startStreaming"].set()
				if not applicationProcess.is_alive():
					applicationProcess.start()
				socketProcess.join()
				applicationProcess.join()
				startTrainingEvent.clear()
				socketConnection.clear()
				# recreating process because eve after Process Termination cannot start a process twice
				socketProcess = Process(target=connectTraining, args=(trainingClassBuffer, socketConnection,))
				applicationProcess = Process(target=startTrainingApp, args=(boardApiCallEvents,))
