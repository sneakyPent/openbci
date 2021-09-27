import queue
import sys
from multiprocessing import Process, Event
from utils import *


class BoardEventHandler:
	"""
	Mainly responsible to manage the below Events and "control" the openbci board via the corresponding method
		* connectEvent -> connect()
		* disconnectEvent -> disconnect()
		* startStreamingEvent -> startStreaming()
		* stopStreamingEvent -> stopStreaming()
		* newBoardSettingsAvailableEvent -> newBoardSettingsAvailable()

	:param board: {} - Represents the OpenBCICyton class in BoardEventHandler class
	:param boardSettings: {Dotted dict} - Contains all board settings set by the GUI and used in cyton.py
	:param newDataAvailable: {Event} - Event which processes' owners of queues contained in dataBuffersList are waiting for to get the new sample read from board
	:param dataBuffersList: {[]} - list with every buffer we want to add streaming data into, and pass to other processes
	:param writeDataEvent: {Event} - Event to inform the writeProcess of UImanager.py to start writing the data into an hdf5 file
	:param trainingClassBuffer: {Queue} - Buffer letting this process to get sample's class, that the training program showing every frame via socket.py
	:param _shutdownEvent: {Event} - Event used to know when to let every running process terminate
	"""

	def __init__(self, board, boardSettings, newDataAvailable, dataBuffersList, writeDataEvent, trainingClassBuffer,
	             _shutdownEvent):
		self.board = board
		self.newDataAvailable = newDataAvailable
		self.boardSettings = boardSettings
		self.dataBuffersList = dataBuffersList
		self.shutdownEvent = _shutdownEvent
		self.writeDataEvent = writeDataEvent
		self.trainingClassBuffer = trainingClassBuffer
		self.trainingClass = cnst.unknownClass
		""" The current training class value read by trainingClassBuffer, initialized in :data:`utils.constants.Constants.unknownClass` value"""

		# events used to start and stop the BoardEventHandler functions
		self.connectEvent = Event()
		self.disconnectEvent = Event()
		self.startStreamingEvent = Event()
		self.stopStreamingEvent = Event()
		self.newBoardSettingsAvailableEvent = Event()

	def connect(self):
		"""
		Method runs via connectProcess:
			* A loop runs while not the shutdownEvent, declared in UIManager.py, is not set
			* When the connectEvent has been set it is trying to accomplish a connection with the openbci board, only if there is not an existed connection
			* Whether it successes or not, it clears the connectEvent
		"""

		while not self.shutdownEvent.is_set():
			self.connectEvent.wait(1)
			if self.connectEvent.is_set():
				if not self.board.isConnected():
					printInfo("Connecting...")
					try:
						self.board.connect()
					except OSError:
						printError("Could not connect to board. Make sure it is properly connected and enabled")
				else:
					printInfo("Already have a connection!")
				self.connectEvent.clear()

	def disconnect(self):
		"""
		Method runs via disconnectProcess:
			* A loop runs while not the shutdownEvent, declared in UIManager.py, is not set
			* When the disconnectEvent has been set it is trying to clear the existing connection with the openbci board, only if board is NOT streaming, which means that board is not transmitting data
			* Whether it successes or not, it clears the disconnectEvent
		"""

		while not self.shutdownEvent.is_set():
			self.disconnectEvent.wait(1)
			if self.disconnectEvent.is_set():
				if self.board.isStreaming():
					printWarning("Cannot disconnect while streaming")
					self.disconnectEvent.clear()
					continue
				if self.board.isConnected():
					printInfo("Disconnecting...")
					try:
						self.board.disconnect()
					except:
						printError("No connection to disconnect from ")
				else:
					printInfo("No connection to disconnect from")
				self.disconnectEvent.clear()

	def startStreaming(self):
		"""
		Method runs via startStreamingProcess:
			*   A loop runs while not the shutdownEvent, declared in UIManager.py, is not set
			*   Whether it successes or not, it clears the startStreamingEvent
			*   When the startStreamingProcess has been set, if there is a valid connection and an active streaming:

			    1. Starts the streaming
			    2. Appends the training class into the channel_data array, if training is enabled.
			    3. Puts the read sample, into every buffer contained in the dataBuffersList for the other processes
			    4. Inform other processes to get tha sample from the buffer, via the newDataAvailable Event

		"""
		numofsamples = 0
		"minor counter, helps to count the number of samples read by the cyton board"
		printing = False
		"minor flag, helps to print the number of samples read by the cyton board"
		while not self.shutdownEvent.is_set():
			self.startStreamingEvent.wait(1)
			if self.startStreamingEvent.is_set():

				if self.board.isConnected():
					printInfo("Starting streaming...")
					self.trainingClass = cnst.unknownClass
					while self.startStreamingEvent.is_set():
						try:
							printing = True
							# get sample from board
							sample = self.board.stream_one_sample()
							# append training class in the channel data before put in the buffer
							if self.board.isSynched():
								try:
									# check if training class has been changed, if so then replace
									if self.trainingClassBuffer.qsize() != 0:
										self.trainingClass = self.trainingClassBuffer.get()
								except Exception:
									printing = False
									printWarning("Something Went Wrong in boardEventHandler line 83")
								# append training class in the channel data before put in the buffer
								# TODO: append training class only while training
								sample.channel_data.append(self.trainingClass)
								# Put the read sample in every buffer contained in the dataBuffersList and then inform
								# other processes via newDataAvailable event
								for buffer in self.dataBuffersList:
									try:
										buffer.put_nowait(sample.channel_data)
										self.newDataAvailable.set()
									except queue.Full:
										printWarning("Queue full")
										printing = False
								numofsamples += 1
							# check for the synching zeros array sample ( [0, 0, 0, 0 ,0 , 0, 0, 0] )
							elif sample.channel_data == cnst.synchingSignal:
								self.board.setSynching(True)
						except Exception as e:
							printing = False
							self.startStreamingEvent.clear()
							exc_type, exc_obj, exc_tb = sys.exc_info()
							fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
							printError("There was a problem on starting streaming in: " + fname.__str__() +
							           ' line: ' + exc_tb.tb_lineno.__str__() + "\nError Message: " + repr(e))
				else:
					if not self.board.isConnected():
						printing = False
						printInfo("No connection to start streaming from.")
				self.startStreamingEvent.clear()
			else:
				self.newDataAvailable.clear()
				if self.shutdownEvent.is_set():
					# empty queues before terminating to prevent zombie processes
					for buffer in self.dataBuffersList:
						if buffer.qsize() != 0:
							printInfo("Empty the queues")
						while not buffer.qsize() == 0:
							buffer.get_nowait()
				if printing:
					print(numofsamples)
					printing = False

	def stopStreaming(self):
		"""
		Method runs via stopStreamingProcess:
			*   A loop runs while not the shutdownEvent, declared in UIManager.py, is not set
			*   Whether it successes or not, it clears the stopStreamingEvent
			*   When the stopStreamingEvent has been set, if there is a valid connection and an active streaming:

			    1. Stops the streaming
			    2. Inform the writeProcess of UIManager to start writing the data to hdf5 file via writeDataEvent
			    3. Reinitialize the trainingClass to :data:`utils.constants.Constants.unknownClass` value

		"""

		while not self.shutdownEvent.is_set():
			self.stopStreamingEvent.wait(1)
			if self.stopStreamingEvent.is_set():
				if self.board.isConnected() and self.board.isStreaming():
					printInfo("Stopping streaming...")
					try:
						self.startStreamingEvent.clear()
						self.writeDataEvent.set()
						self.board.stopStreaming()
						self.board.setSynching(False)
					except:
						printError("There is no stream to stop.")
				else:
					if not self.board.isConnected():
						printInfo("No connection to stop streaming from.")
					elif not self.board.isStreaming():
						printInfo("No active streaming to stop.")
				self.stopStreamingEvent.clear()

	def newBoardSettingsAvailable(self):
		"""
		Method runs via newBoardSettingsAvailableProcess:
			* A loop runs while not the shutdownEvent, declared in UIManager.py, is not set
			* When the newBoardSettingsAvailableEvent has been set it is calling the cyton board method :func:`source.cyton.OpenBCICyton.setBoardSettingAttributes` to change the board settings according to GUI
			* Whether it successes or not, it clears the newBoardSettingsAvailableEvent
		"""

		while not self.shutdownEvent.is_set():
			self.newBoardSettingsAvailableEvent.wait(1)
			if self.newBoardSettingsAvailableEvent.is_set():
				printInfo("New board setting Available...")
				self.board.setBoardSettingAttributes(self.boardSettings)
				self.newBoardSettingsAvailableEvent.clear()

	def getBoardHandlerEvents(self):
		"""
		Returns the events used to start and stop the BoardEventHandler functions in dictionary format

		"""
		return {
			"connect": self.connectEvent,
			"disconnect": self.disconnectEvent,
			"startStreaming": self.startStreamingEvent,
			"stopStreaming": self.stopStreamingEvent,
			"newBoardSettingsAvailable": self.newBoardSettingsAvailableEvent
		}

	def start(self):
		"""
		*   Its the only method of BoardEventHandler should be called from outer methods
		*   its responsible to run the five below methods in 5 independent processes
			*   :meth:`source.boardEventHandler.BoardEventHandler.connect`
			*   :meth:`source.boardEventHandler.BoardEventHandler.disconnect`
			*   :meth:`source.boardEventHandler.BoardEventHandler.startStreaming`
			*   :meth:`source.boardEventHandler.BoardEventHandler.stopStreaming`
			*   :meth:`source.boardEventHandler.BoardEventHandler.newBoardSettingsAvailable`
		*   The above methods are completely controlled by their corresponding events when they are triggered (set)
		"""
		procList = []
		printInfo("Starting eventHandler")
		connectProcess = Process(target=self.connect)
		disconnectProcess = Process(target=self.disconnect)
		startStreamingProcess = Process(target=self.startStreaming)
		stopStreamingProcess = Process(target=self.stopStreaming)
		newBoardSettingsAvailableProcess = Process(target=self.newBoardSettingsAvailable)

		procList.append(connectProcess)
		procList.append(disconnectProcess)
		procList.append(startStreamingProcess)
		procList.append(stopStreamingProcess)
		procList.append(newBoardSettingsAvailableProcess)

		for proc in procList:
			proc.start()

		# join processes
		for proc in procList:
			proc.join()
