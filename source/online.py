"""
This module used only for the online session and in order to run it needs the unity target executable.
	Consist of 6 main methods:
		* :py:meth:`source.online.socketConnect`
		* :py:meth:`source.online.startTargetApp`
		* :py:meth:`source.online.onlineProcessing`
		* :py:meth:`source.online.debugPredict`
		* :py:meth:`source.online.wheelSerialPredict`
		* :py:meth:`source.online.startOnline`

"""

import logging
import queue
import socket
import subprocess
import os
import re
from multiprocessing.managers import SyncManager
from threading import Event
import time
from multiprocessing import Process, Event, Queue

import joblib
from time import sleep
import serial
from source import OpenBCICyton
from utils.constants import Constants as cnst, getSessionFilename
from utils.filters import *
from classification.train_processing_cca_3 import calculate_cca_correlations
from utils.general import emptyQueue


class Error(Exception):
	"""Base class for other exceptions"""
	pass


class SocketConnectionError(Error):
	"""Raised when there is a problem with the socket connection to unity application"""
	pass


def socketConnect(board, boardApiCallEvents, socketConnection, startOnlineEvent,
                  emergencyKeyboardEvent, keyboardBuffer, _shutdownEvent):
	"""
	Its the only method runs immediately via :py:meth:`source.online.startOnline` and waits for :py:attr:`startOnlineEvent`

	* Responsible

		* to create a socket communication with the target executable. By the time the connection's been established, it sets the :py:attr:`socketConnection`.
		* to start streaming through :py:attr:`boardApiCallEvents`, only if it receives the :py:const:`utils.constants.Constants.onlineUnitySentByte` by socket connection.
		* to stop streaming through :py:attr:`boardApiCallEvents`, only if it receives "E" or ""  by socket connection.


	* When the connection could not be established then wait for 10 sec and then retrying.

	:param OpenBCICyton board: Represents the OpenBCICyton object created from :py:class:`source.UIManager`.
	:param list[Event] boardApiCallEvents: Events used in :py:class:`source.boardEventHandler.BoardEventHandler`
	:param Event socketConnection: Used as flag so the processes :py:meth:`source.online.startTargetApp` :py:meth:`source.online.onlineProcessing` :py:meth:`source.online.debugPredict` :py:meth:`source.online.wheelSerialPredict` can proceed.
	:param Event startOnlineEvent: Event for which this method will be waiting. This Event is set only by the :py:meth:`source.pyGUI.GUI.onlineButtonClick`
	param Event emergencyKeyboardEvent: Event will be used for enable keyboard controlling of the wheelchair.
	:param Queue keyboardBuffer: Buffer for passing pressed key to :py:meth:`source.online.wheelSerialPredict` and used it for wheelchair movement
	:param Event _shutdownEvent: Event used to know when to allow every running process terminate

	"""
	logger = logging.getLogger(cnst.loggerName)
	while not _shutdownEvent.is_set():
		startOnlineEvent.wait(1)
		if startOnlineEvent.is_set():
			if not board.isConnected():
				logger.warning('Could not start online session without connected Board.')
				startOnlineEvent.clear()
				continue
			# create socket
			s = socket.socket()
			socket.setdefaulttimeout(None)
			logger.info('Socket created')
			# IP and PORT connection
			port = 8080
			while not socketConnection.is_set():
				try:
					# s.bind(('139.91.190.32', port)) #local host
					s.bind(('127.0.0.1', port))  # local host
					s.listen(30)  # listening for connection for 30 sec?
					logger.info('Socket listening ... ')
					# try:
					socketConnection.set()
					c, addr = s.accept()  # when port connected
					logger.info('Got connection from ' + addr.__str__())

					# 1st communication with Quest
					bytes_received = c.recv(1024)  # received bytes
					logger.info(bytes_received.decode("utf-8"))

					# Send "True" string to start the Quest app
					nn_output = "True"
					arr2 = bytes(nn_output, 'utf-8')
					c.sendall(arr2)  # sending back

					# Quest sends the arrow number
					bytes_received = c.recv(1).decode("utf-8")  # received bytes
					c.sendall('2'.encode())
					try:
						if int(bytes_received) == cnst.onlineUnitySentByte:
							boardApiCallEvents["startStreaming"].set()
					except:
						raise SocketConnectionError

					if bytes_received != "E" and bytes_received != "":

						# q_label.put(int(bytes_received))
						bytes_received_old = bytes_received
						while True:  # bytes_received != "E": # "E" means end of the action
							bytes_received = c.recv(1).decode("utf-8")  # received bytes
							c.sendall('2'.encode())
							if bytes_received == "E" or bytes_received == "":
								boardApiCallEvents["stopStreaming"].set()
								socketConnection.clear()
								break
							else:
								if bytes_received != bytes_received_old:
									try:
										if bytes_received in [*cnst.keyBoardCommands]:
											keyboardBuffer.put_nowait(bytes_received)
									except queue.Full:
										logging.getLogger(cnst.loggerName).info('keyboardBuffer full')
										emptyQueue(keyboardBuffer)
									except ValueError as error:
										logger.error(error)
									except:
										raise SocketConnectionError
									bytes_received_old = bytes_received
					c.shutdown(socket.SHUT_RDWR)
					c.close()
					break
				except socket.error as error:
					logger.warning(error.__str__() + '. Wait for 10 seconds before trying again')
					time.sleep(10)
					pass
				except SocketConnectionError:
					logger.error('SocketConnection problem', exc_info=True)
					c.shutdown(socket.SHUT_RDWR)
					boardApiCallEvents["stopStreaming"].set()
					c.close()
			socketConnection.clear()
			startOnlineEvent.clear()


def startTargetApp(socketConnection, _shutdownEvent):
	"""
	* Waits until :py:attr:`socketConnection` get set by :py:meth:`source.training.connectTraining`
	* Executes the unity target executable given in :data:`utils.constants.Constants.onlineUnityExePath`

	:param Event socketConnection: Used as flag so the method can proceed to start the online application.
	:param Event _shutdownEvent: Event used to know when to allow every running process terminate

	"""
	while not _shutdownEvent.is_set():
		socketConnection.wait(1)
		if socketConnection.is_set():
			with open(os.devnull, 'wb') as devnull:
				subprocess.check_call([cnst.onlineUnityExePath], stdout=devnull, stderr=subprocess.STDOUT)


def onlineProcessing(board, windowedDataBuffer, predictBuffer, socketConnection, newWindowAvailable, _shutdownEvent):
	"""

		* waits until :py:attr:`socketConnection` get set by :py:meth:`source.training.connectTraining`
		* loads classifier given in :py:const:`utils.constants.Constants.classifierFilename`
		* receive a windowed signal from the :py:attr:`windowedDataBuffer`
		* calculates the cca correlations through :py:meth:`classification.train_processing_cca_3.calculate_cca_correlations`
		* predicts the likely target class through "joblib"
		* pass the predicted class to :py:attr:`predictBuffer`

		:param OpenBCICyton board: Represents the OpenBCICyton object created from :py:class:`source.UIManager`.
		:param Queue windowedDataBuffer: Buffer used for communicating and getting the windowed Data data from :py:meth:`source.windowing.windowing`.
		:param Queue predictBuffer: Buffer used for communicating and passing the predicted data to :py:meth:`source.online.wheelSerialPredict`.
		:param Event socketConnection: Used as flag so the method can proceed to start the online application.
		:param Event newWindowAvailable: Event used to know when there is new window available data in :py:attr:`windowedDataBuffer` from :py:meth:`source.windowing.windowing`. It is set by :py:meth:`source.windowing.windowing`
		:param Event _shutdownEvent: Event used to know when to allow every running process terminate

		"""
	logger = logging.getLogger(cnst.loggerName)
	clf = joblib.load(cnst.classifierFilename)
	while not _shutdownEvent.is_set():
		socketConnection.wait(1)
		frames_ch = cnst.frames_ch
		lowcut = board.getLowerBoundFrequency()
		highcut = board.getHigherBoundFrequency()
		fs = board.getSampleRate()
		chan_ind = board.getEnabledChannels()
		while socketConnection.is_set():
			newWindowAvailable.wait(1)
			try:
				if newWindowAvailable.is_set() and socketConnection.is_set():
					segment_full = np.array(windowedDataBuffer.get())

					# # I sum the frames along axis 1 (i.e. I sum all the elements of each row)
					# frames_np = np.sum(np.array(frames_ch), 1)
					# # I divide the screen refresh rate by the frames_np for each stimulus frequency
					# stimulus_freqs = np.divide(np.full(frames_np.shape[0], 60.), frames_np)
					# # checkerboard invokes double of the stimuli freqs!!!!!!!!!!!!
					# stimulus_freqs = 2 * stimulus_freqs
					# choose channels (last column = label, it doesn't apply in online mode)
					segment = segment_full[:, np.asarray(chan_ind)]
					# filter the data
					segmentFiltered = butter_bandpass_filter(data=segment,
					                                         lowcut=lowcut,
					                                         highcut=highcut,
					                                         fs=fs,
					                                         order=10)
					# calculate cca correlations
					r_segment = calculate_cca_correlations(segment=segmentFiltered,
					                                       fs=fs,
					                                       frames_ch=frames_ch,
					                                       harmonics_num=cnst.harmonics_num)
					# predict
					tmp_command_predicted = clf.predict(r_segment)
					command_predicted = int(tmp_command_predicted[0])
					logger.critical(command_predicted)
					#  put prediction into the buffer
					predictBuffer.put_nowait(command_predicted)
			except queue.Full:
				logger.error('predictBuffer is Full.')
				emptyQueue(predictBuffer)
			except queue.Empty:
				logger.error('WindowedDataBuffer is empty.')
	emptyQueue(predictBuffer)


def debugPredict(socketConnection, predictBuffer, emergencyKeyboardEvent, keyboardBuffer, _shutdownEvent,
                 target3_=False):
	"""
	Same logic as :py:meth:`source.online.wheelSerialPredict`. Used for debug purposes, testing without connection with a wheelchair
	"""
	logger = logging.getLogger(cnst.loggerName)
	debugMode = False
	commandPrintFileObject = None
	while not _shutdownEvent.is_set():
		socketConnection.wait(1)
		if socketConnection.is_set():
			command = cnst.onlineStreamingCommands_STOP
			data = cnst.target4Class_STOP
			# If debug Mode enabled, create file for logging commands
			if debugMode:
				commandPrintFileObject = open(getSessionFilename(online=True), 'w')
			# 	Set stop as init command
			cmd_old = cnst.target4Class_STOP
			logger.info("Start Wheelchair")
			while not _shutdownEvent.is_set() and socketConnection.is_set():  # Running while there is socket connection with the
				if not predictBuffer.empty():  # New command Available
					data = predictBuffer.get_nowait()  # get the command and translate into move
					logger.warning(data)
					if not emergencyKeyboardEvent.is_set():
						if not cmd_old == cnst.target4Class_STOP and data == cnst.target4Class_STOP:  # sut the "stop" between commands
							temp = data
							data = cmd_old
							cmd_old = temp
						else:
							cmd_old = data
						# Translate and send the command
						# if command is stop then start reducing speed
						if data == cnst.target4Class_STOP:
							# Get the next command when receiving stop class
							if command == cnst.onlineStreamingCommands_FORWARD:  # if previous_command == forward
								tmpCommand = cnst.onlineStreamingCommands_REDUCE_SPEED_1  # reduce the speed
								# check environment with sensors for the given command
								# if checkEnvironment(tmpCommand, sensorSerial):
								# 	command = tmpCommand
								# else:
								# 	command = cnst.onlineStreamingCommands_STOP
								command = tmpCommand
							elif command == cnst.onlineStreamingCommands_REDUCE_SPEED_1:
								tmpCommand = cnst.onlineStreamingCommands_REDUCE_SPEED_2  # reduce the speed
								# check environment with sensors for the given command
								# if checkEnvironment(tmpCommand, sensorSerial):
								# 	command = tmpCommand
								# else:
								# 	command = cnst.onlineStreamingCommands_STOP
								command = tmpCommand
							else:
								command = cnst.onlineStreamingCommands_STOP

							msg = cnst.commandsTranslationForDebug.get(command, 'NOT AVAILABLE COMMAND') \
							      + ': ' + command
							# 	Apply command
							if debugMode:
								commandPrintFileObject.write(msg)
							logger.debug(msg)
							sleep(0.08)  # delay before the next command

						else:  # otherwise (every other command) just check environment and write it
							tmpCommand = getClassCommand(data, target3_)
							# check environment with sensors for the given data
							command = tmpCommand
							# if checkEnvironment(tmpCommand, sensorSerial):
							# 	command = tmpCommand
							# else:
							# 	command = cnst.onlineStreamingCommands_STOP
							msg = cnst.commandsTranslationForDebug.get(command, 'NOT AVAILABLE COMMAND') \
							      + ': ' + command
							if debugMode:
								commandPrintFileObject.write(msg)
							logger.debug(msg)
							sleep(0.08)  # delay before the next command
					else:
						logger.warning("Keyboard movement")
						if not keyboardBuffer.empty():
							data = keyboardBuffer.get_nowait()

							tmpCommand = cnst.keyBoardCommands.get(data, cnst.onlineStreamingCommands_STOP)
							# check environment with sensors for the given data
							command = tmpCommand
							# if checkEnvironment(tmpCommand, sensorSerial):
							# 	command = tmpCommand
							# else:
							# 	command = cnst.onlineStreamingCommands_STOP
							msg = cnst.commandsTranslationForDebug.get(command, 'NOT AVAILABLE COMMAND') \
							      + ': ' + command
							if debugMode:
								commandPrintFileObject.write(msg)
							logger.debug(msg)
							sleep(0.08)  # delay before the next command

						else:
							command = command
							# if checkEnvironment(command, sensorSerial):
							# 	command = command
							# else:
							# 	command = cnst.onlineStreamingCommands_STOP
							msg = cnst.commandsTranslationForDebug.get(command, 'NOT AVAILABLE COMMAND') \
							      + ': ' + command
							# check environment with sensors for the given command if ok write it else write stop
							if debugMode:
								commandPrintFileObject.write(msg)
							logger.debug(msg)
							sleep(0.08)
				else:  # if command_buffer is empty send the previous command to wheelchair
					# check environment with sensors for the given command
					command = command
					# if checkEnvironment(command, sensorSerial):
					# 	command = command
					# else:
					# 	command = cnst.onlineStreamingCommands_STOP
					msg = cnst.commandsTranslationForDebug.get(command, 'NOT AVAILABLE COMMAND') \
					      + ': ' + command
					# check environment with sensors for the given command if ok write it else write stop
					if debugMode:
						commandPrintFileObject.write(msg)
					logger.debug(msg)
					sleep(0.08)
			emptyQueue(predictBuffer)
			# emptyQueue(keyboardBuffer)
			logger.info("End Wheelchair")
			if debugMode:
				commandPrintFileObject.close()


def getClassCommand(commandClass, target3_):
	"""
	For given class, returns the command using either :py:const:`utils.constants.Constants.class4Switcher` or :py:const:`utils.constants.Constants.class3Switcher`

	:param int commandClass: The unity class, to get the wheel command.
	:param bool target3_: True, only if the 3 target unity application will be used, defaults to False.

	:return: The command for the wheel depends on the :py:attr:`target3_` and :py:attr:`commandClass`
	:rtype: str
	"""
	return cnst.class4Switcher.get(commandClass, cnst.onlineStreamingCommands_STOP) \
		if not target3_ else cnst.class3Switcher.get(commandClass, cnst.onlineStreamingCommands_STOP)


def checkEnvironment(command, sensorSerial):
	"""
	Check environment through connected sensors and

	:param str command: The next command for which, we want to check the around environment.
	:param Serial sensorSerial: The serial for the sensors

	:return: True if the environment is clean and the command can be executed, otherwise False.
	:rtype: bool
	"""
	# read Sensors
	distance = sensorSerial.readline().decode('utf-8')
	temp = re.findall(r'\d+', distance)
	sensorMeasurements = list(map(int, temp))
	#
	if command == cnst.onlineStreamingCommands_STOP:
		return True
	if ((command == cnst.onlineStreamingCommands_FORWARD) or (
			command == cnst.onlineStreamingCommands_REDUCE_SPEED_1) or (
			command == cnst.onlineStreamingCommands_REDUCE_SPEED_2)):
		return False if ((1 < sensorMeasurements[0] < cnst.sensorLimit_FRONT) or (
				1 < sensorMeasurements[1] < cnst.sensorLimit_FRONT)) else True
	elif command == cnst.onlineStreamingCommands_RIGHT:
		return False if 1 < sensorMeasurements[3] < cnst.sensorLimit_SIDE else True
	elif command == cnst.onlineStreamingCommands_LEFT:
		return False if 1 < sensorMeasurements[2] < cnst.sensorLimit_SIDE else True
	else:
		return False


def wheelSerialPredict(socketConnection, predictBuffer, usb_port_,
                       emergencyKeyboardEvent, keyboardBuffer, _shutdownEvent, target3_=False):
	"""
	Connects with the wheelchair and send the commands through the given serial port = :py:attr:`usb_port_`.

	:param Event socketConnection: Used as flag so the method can proceed to start the online application.
	:param Queue predictBuffer: Buffer used for communicating and getting the predicted data to :py:meth:`source.online.onlineProcessing`.
	:param str usb_port_: Name of the port, the wheelchair use for connection. (Windows: COMx, linux: /dev/ttyUSBx).
	:param Event emergencyKeyboardEvent: Event will be used for enable keyboard controlling of the wheelchair.
	:param Queue keyboardBuffer: Buffer for getting pressed key from :py:mod:`source.keyboardMove' and used it for wheelchair movement
	:param Event _shutdownEvent: Event used to know when to allow every running process terminate.
	:param bool target3_: When True, means that it will be used the unity with 3 targets for the session.
	"""
	logger = logging.getLogger(cnst.loggerName)
	debugMode = False
	commandPrintFileObject = None
	while not _shutdownEvent.is_set():
		socketConnection.wait(1)
		if socketConnection.is_set():
			command = cnst.onlineStreamingCommands_STOP
			data = cnst.target4Class_STOP
			try:
				# Serial connections with the wheelchair and sensors
				wheelCharSerial = serial.Serial(port=usb_port_, baudrate=115200, parity=serial.PARITY_NONE,
				                                stopbits=serial.STOPBITS_ONE,
				                                bytesize=serial.EIGHTBITS)
				wheelCharSerial.write(cnst.online_connection_serial.encode())  # connect to port
				wheelCharSerial.readline().decode()

				wheelCharSerial.write(cnst.online_info.encode())
				info_list = wheelCharSerial.readline().decode().split(",", 6)
				sensorSerial = serial.Serial(port=cnst.sensorUsbPort, baudrate=115200, parity=serial.PARITY_NONE,
				                             stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS)  # serial sensor
				logger.info(info_list)
				# If debug Mode enabled, create file for logging commands
				if debugMode:
					commandPrintFileObject = open(getSessionFilename(online=True), 'w')
				# 	Set stop as init command
				cmd_old = cnst.target4Class_STOP
				logger.info("Start Wheelchair")
				while not _shutdownEvent.is_set() and socketConnection.is_set():  # Running while there is socket connection with the
					if not predictBuffer.empty():  # New command Available
						data = predictBuffer.get_nowait()  # get the command and translate into move
						if not emergencyKeyboardEvent.is_set():
							if not cmd_old == cnst.target4Class_STOP and data == cnst.target4Class_STOP:  # sut the "stop" between commands
								temp = data
								data = cmd_old
								cmd_old = temp
							else:
								cmd_old = data

							# Translate and send the command
							# if command is stop then start reducing speed
							if data == cnst.target4Class_STOP:
								# Get the next command when receiving stop class
								if command == cnst.onlineStreamingCommands_FORWARD:  # if previous_command == forward
									tmpCommand = cnst.onlineStreamingCommands_REDUCE_SPEED_1  # reduce the speed
									# check environment with sensors for the given command
									if checkEnvironment(tmpCommand, sensorSerial):
										command = tmpCommand
									else:
										command = cnst.onlineStreamingCommands_STOP
								elif command == cnst.onlineStreamingCommands_REDUCE_SPEED_1:
									tmpCommand = cnst.onlineStreamingCommands_REDUCE_SPEED_2  # reduce the speed
									# check environment with sensors for the given command
									if checkEnvironment(tmpCommand, sensorSerial):
										command = tmpCommand
									else:
										command = cnst.onlineStreamingCommands_STOP
								else:
									command = cnst.onlineStreamingCommands_STOP

								msg = cnst.commandsTranslationForDebug.get(command, 'NOT AVAILABLE COMMAND') \
								      + ': ' + command
								# 	Apply command
								if debugMode:
									commandPrintFileObject.write(msg)
								else:
									wheelCharSerial.write(command.encode())
								logger.debug(msg)
								sleep(0.08)  # delay before the next command

							else:  # otherwise (every other command) just check environment and write it
								tmpCommand = getClassCommand(data, target3_)
								# check environment with sensors for the given data
								if checkEnvironment(tmpCommand, sensorSerial):
									command = tmpCommand
								else:
									command = cnst.onlineStreamingCommands_STOP
								msg = cnst.commandsTranslationForDebug.get(command, 'NOT AVAILABLE COMMAND') \
								      + ': ' + command
								if debugMode:
									commandPrintFileObject.write(msg)
								else:
									wheelCharSerial.write(command.encode())
								logger.debug(msg)
								sleep(0.08)  # delay before the next command
						else:
							logger.warning("Keyboard movement")
							if not keyboardBuffer.empty():
								data = keyboardBuffer.get_nowait()

								tmpCommand = cnst.keyBoardCommands.get(data, cnst.onlineStreamingCommands_STOP)
								# check environment with sensors for the given data
								if checkEnvironment(tmpCommand, sensorSerial):
									command = tmpCommand
								else:
									command = cnst.onlineStreamingCommands_STOP
								msg = cnst.commandsTranslationForDebug.get(command, 'NOT AVAILABLE COMMAND') \
								      + ': ' + command
								if debugMode:
									commandPrintFileObject.write(msg)
								else:
									wheelCharSerial.write(command.encode())
								logger.debug(msg)
								sleep(0.08)  # delay before the next command

							else:
								if checkEnvironment(command, sensorSerial):
									command = command
								else:
									command = cnst.onlineStreamingCommands_STOP
								msg = cnst.commandsTranslationForDebug.get(command, 'NOT AVAILABLE COMMAND') \
								      + ': ' + command
								# check environment with sensors for the given command if ok write it else write stop
								if debugMode:
									commandPrintFileObject.write(msg)
								else:
									wheelCharSerial.write(command.encode())
								logger.debug(msg)
								sleep(0.08)
					else:  # if command_buffer is empty send the previous command to wheelchair
						# check environment with sensors for the given command
						if checkEnvironment(command, sensorSerial):
							command = command
						else:
							command = cnst.onlineStreamingCommands_STOP
						msg = cnst.commandsTranslationForDebug.get(command, 'NOT AVAILABLE COMMAND') \
						      + ': ' + command
						# check environment with sensors for the given command if ok write it else write stop
						if debugMode:
							commandPrintFileObject.write(msg)
						else:
							wheelCharSerial.write(command.encode())
						logger.debug(msg)
						sleep(0.08)
				emptyQueue(predictBuffer)
				# emptyQueue(keyboardBuffer)
				logger.info("End Wheelchair")
				if debugMode:
					commandPrintFileObject.close()
			except serial.SerialException:
				logger.warning("Problem connecting to serial device.")
				emptyQueue(predictBuffer)
				emptyQueue(keyboardBuffer)
				if debugMode:
					commandPrintFileObject.close()


def startOnline(board, startOnlineEvent, boardApiCallEvents, _shutdownEvent, windowedDataBuffer, newWindowAvailable,
                emergencyKeyboardEvent, keyboardBuffer, debugMode=True):
	"""
	* Method runs via onlineProcess in :py:mod:`source.UIManager`
	* Runs simultaneously with the boardEventHandler process and waits for the startOnlineEvent, which is set only by the boardEventHandler.
	* When the startOnlineEvent is set:

		* Starts process for:

			* :py:meth:`source.online.socketConnect`
			* :py:meth:`source.online.startTargetApp`
			* :py:meth:`source.online.onlineProcessing`
			* :py:meth:`source.online.debugPredict`
			* :py:meth:`source.online.wheelSerialPredict`

	:param OpenBCICyton board: Represents the OpenBCICyton object created from :py:class:`source.UIManager`.
	:param Event startOnlineEvent: Event which this process will be waiting for, before starting the above processes. This Event is set only by the :py:meth:`source.pyGUI.GUI.onlineButtonClick`
	:param [Event] boardApiCallEvents:  Events used in :py:class:`source.boardEventHandler.BoardEventHandler`
	:param Event _shutdownEvent: Event used to know when to let every running process terminate
	:param Queue windowedDataBuffer: Buffer will be used to 'give' the training class to :meth:`source.boardEventHandler.BoardEventHandler.startStreaming`, via :meth:`source.training.connectTraining`
	:param Event newWindowAvailable: Event used to know when there is new window available from :py:meth:`source.windowing.windowing`. It is set by :py:meth:`source.windowing.windowing`
	:param bool debugMode: When True, print messages used instead of serial connection with wheel.
	:param Event emergencyKeyboardEvent: Event will be used for enable keyboard controlling of the wheelchair.
	:param Queue keyboardBuffer: Buffer for getting pressed key from :py:mod:`source.keyboardMove' and used it for wheelchair movement

	"""
	procList = []
	socketConnection = Event()
	socketConnection.clear()
	mngr = SyncManager()
	mngr.start()
	predictBuffer = mngr.Queue(maxsize=100)

	# Create the process needed
	socketProcess = Process(target=socketConnect,
	                        args=(board, boardApiCallEvents, socketConnection, startOnlineEvent,
	                              emergencyKeyboardEvent, keyboardBuffer, _shutdownEvent,))
	applicationProcess = Process(target=startTargetApp, args=(socketConnection, _shutdownEvent,))
	onlineProcessingProcess = Process(target=onlineProcessing,
	                                  args=(board, windowedDataBuffer, predictBuffer, socketConnection,
	                                        newWindowAvailable, _shutdownEvent,))
	debugPredictProcess = Process(target=debugPredict,
	                              args=(socketConnection, predictBuffer, emergencyKeyboardEvent, keyboardBuffer,
	                                    _shutdownEvent,))
	wheelSerialPredictProcess = Process(target=wheelSerialPredict,
	                                    args=(
		                                    socketConnection, predictBuffer, cnst.wheelchairUsbPort,
		                                    emergencyKeyboardEvent, keyboardBuffer, _shutdownEvent,))

	procList.append(socketProcess)
	procList.append(applicationProcess)
	procList.append(onlineProcessingProcess)
	if debugMode:
		procList.append(debugPredictProcess)
	else:
		procList.append(wheelSerialPredictProcess)

	for proc in procList:
		proc.start()

	# join processes
	for proc in procList:
		proc.join()
	emptyQueue(predictBuffer)
