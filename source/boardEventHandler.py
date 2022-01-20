import queue
import traceback
from multiprocessing import Process, Event
from utils import *
from utils.general import emptyQueue


class BoardEventHandler:
	"""
	Mainly responsible to manage the below Events and "control" the openbci board via the corresponding method
		* connectEvent -> connect()
		* disconnectEvent -> disconnect()
		* startStreamingEvent -> startStreaming()
		* stopStreamingEvent -> stopStreaming()
		* newBoardSettingsAvailableEvent -> newBoardSettingsAvailable()

	:param OpenBCICyton board: Represents the OpenBCICyton class in BoardEventHandler class
	:param dict boardSettings: Contains all board settings set by the GUI and used in cyton.py
	:param Event newDataAvailable:  Event which other process are waiting for to get the new sample read from board
	:param dataBuffersList: List with every buffer we want to add streaming data into, and pass to other processes
	:type dataBuffersList: list(Queue)
	:param Queue writingBuffer:  Buffer to pass the stream data to :py:meth:`source.writeToFile.writing`.
	:param Event writeDataEvent:  Event to inform the writeProcess of UImanager.py to start writing the data into an hdf5 file
	:param Queue currentClassBuffer:  Buffer lets this process to get sample's class, that either the training program showing every frame via :py:mod:`source.training` or the online session using as the predicted command in :py:mod:`source.online`
	:param Event _shutdownEvent:  Event used to know when to allow every running process terminate

	:var int currentClass: The current training class value read by currentClassBuffer, initialized in :data:`utils.constants.Constants.unknownClass` value
	:var Event connectEvent: When this one get set the :py:meth:`source.boardEventHandler.BoardEventHandler.connect` method is allowed to continue to main process
	:var Event disconnectEvent:  When this one get set the :py:meth:`source.boardEventHandler.BoardEventHandler.disconnect` method is allowed to continue to main process
	:var Event startStreamingEvent:  When this one get set the :py:meth:`source.boardEventHandler.BoardEventHandler.startStreaming` method is allowed to continue to main process
	:var Event stopStreamingEvent:  When this one get set the :py:meth:`source.boardEventHandler.BoardEventHandler.stopStreaming` method is allowed to continue to main process
	:var Event newBoardSettingsAvailableEvent:  When this one get set the :py:meth:`source.boardEventHandler.BoardEventHandler.newBoardSettingsAvailable` method is allowed to continue to main process
	"""

	def __init__(self, board, boardSettings, newDataAvailable, dataBuffersList, writingBuffer, writeDataEvent,
	             currentClassBuffer, groundTruthClassBuffer, _shutdownEvent):
		self.board = board
		self.boardSettings = boardSettings
		self.newDataAvailable = newDataAvailable
		self.dataBuffersList = dataBuffersList
		self.writingBuffer = writingBuffer
		self.writeDataEvent = writeDataEvent
		self.currentClassBuffer = currentClassBuffer
		self.groundTruthClassBuffer = groundTruthClassBuffer
		self.shutdownEvent = _shutdownEvent

		self.currentClass = cnst.unknownClass
		self.groundTruthClass = cnst.unknownClass
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
					try:
						self.board.connect()
					except OSError as er:
						printWarning("Make sure board is properly connected and enabled. " + er.__str__())
				else:
					printWarning("Already have a connection!")
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
					printWarning("No connection to disconnect from")
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
		streamingQueues = [self.writingBuffer, self.currentClassBuffer, self.groundTruthClassBuffer]
		streamingQueues.extend(self.dataBuffersList)
		numOfSamples = 0
		"minor counter, helps to count the number of samples read by the cyton board"
		printing = False
		"minor flag, helps to print the number of samples read by the cyton board"
		while not self.shutdownEvent.is_set():
			self.startStreamingEvent.wait(1)
			if self.startStreamingEvent.is_set():
				if self.board.isConnected():
					emptyQueue(streamingQueues)
					printInfo("Starting streaming...")
					self.currentClass = cnst.unknownClass
					numOfSamples = 0
					printing = True
					while self.startStreamingEvent.is_set():
						try:
							# get sample from board
							sample = self.board.stream_one_sample()
							# append training class in the channel data before put in the buffer
							if self.board.isSynched():
								# check if training class has been changed, if so then replace
								if not self.currentClassBuffer.empty():
									self.currentClass = self.currentClassBuffer.get_nowait()
								if not self.groundTruthClassBuffer.empty():
									self.groundTruthClass = self.groundTruthClassBuffer.get_nowait()
								# append training class in the channel data before put in the buffer
								if self.board.isTrainingMode():
									sample.channel_data.append(self.currentClass)
									sample.channel_data.append(self.groundTruthClass)

								# Put the read sample in every buffer contained in the dataBuffersList and then inform other processes via newDataAvailable event
								for buffer in self.dataBuffersList:
									buffer.put_nowait(sample.channel_data)
									self.newDataAvailable.set()
								if self.board.isTrainingMode():
									self.writingBuffer.put_nowait(sample.channel_data)
									self.newDataAvailable.set()
								numOfSamples += 1
								self.newDataAvailable.clear()
							# check for the synching zeros array sample ( [0, 0, 0, 0 ,0 , 0, 0, 0] )
							elif sample.channel_data == cnst.synchingSignal:
								printInfo('Synching completed')
								self.board.setSynching(True)
						except queue.Full:
							printError("Queue full, stop streaming...")
							self.stopStreamingEvent.set()
							printing = False
							break
						except Exception as er:
							printError('Stop streaming: ' + er.__str__())
							self.stopStreamingEvent.set()
							printing = False
				else:
					printing = False
					printWarning("No connection to start streaming from.")
				self.startStreamingEvent.clear()
			else:
				self.newDataAvailable.clear()
				if printing:
					printInfo('Total streamed samples received: ' + numOfSamples.__str__())
					printing = False
		emptyQueue(streamingQueues)

	def stopStreaming(self):
		"""
		Method runs via stopStreamingProcess:
			*   A loop runs while not the shutdownEvent, declared in UIManager.py, is not set
			*   Whether it successes or not, it clears the stopStreamingEvent
			*   When the stopStreamingEvent has been set, if there is a valid connection and an active streaming:

			    1. Stops the streaming
			    2. Inform the writeProcess of UIManager to start writing the data to hdf5 file via writeDataEvent
			    3. Reinitialize the currentClass to :data:`utils.constants.Constants.unknownClass` value

		"""

		while not self.shutdownEvent.is_set():
			self.stopStreamingEvent.wait(1)
			if self.stopStreamingEvent.is_set():
				if self.board.isConnected() and self.board.isStreaming():
					printInfo("Stopping streaming...")
					try:
						self.startStreamingEvent.clear()
						if self.board.isTrainingMode():
							self.writeDataEvent.set()
							self.board.setTrainingMode(False)
						self.board.stopStreaming()
						self.board.setSynching(False)
					except:
						printError("There is no stream to stop.")
				else:
					if not self.board.isConnected():
						printWarning("No connection to stop streaming from.")
					elif not self.board.isStreaming():
						printWarning("No active streaming to stop.")
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
