import os
import sys
import queue
from multiprocessing import Process, Event
from utils.coloringPrint import *


class BoardEventHandler:
	"""
	Args:
		dataBuffersList: {[]} - list with every buffer we want to add streaming data into
		newDataAvailable: {Event} - Event in which process owners of queues contained in dataBuffersList are waiting for
	"""

	def __init__(self, board, boardSettings, newDataAvailable, dataBuffersList, writeDataEvent, trainingClassBuffer):
		self.board = board
		self.newDataAvailable = newDataAvailable
		self.boardSettings = boardSettings
		# The list with the buffers, the streaming data will be stored
		self.dataBuffersList = dataBuffersList
		self.connected = Event()
		self.shutdownEvent = None
		self.writeDataEvent = writeDataEvent
		self.trainingClassBuffer = trainingClassBuffer
		self.trainingClass = 200
		# events used to start and stop the BoardEventHandler functions
		self.connectEvent = Event()
		self.disconnectEvent = Event()
		self.startStreamingEvent = Event()
		self.stopStreamingEvent = Event()
		self.newBoardSettingsAvailableEvent = Event()

	""" 
				Action Functions
	"""

	def connect(self):
		while not self.shutdownEvent.is_set():
			self.connectEvent.wait(1)
			if self.connectEvent.is_set():
				if not self.connected.is_set():
					printInfo("Connecting...")
					try:
						self.board.connect()
						self.connected.set()
					except OSError:
						printError("Could not connect to board. Make sure it is properly connected and enabled")
				else:
					printInfo("Already have a connection!")
				self.connectEvent.clear()

	def disconnect(self):
		while not self.shutdownEvent.is_set():
			self.disconnectEvent.wait(1)
			if self.disconnectEvent.is_set():
				if self.connected.is_set():
					printInfo("Disconnecting...")
					try:
						self.board.disconnect()
						self.connected.clear()
					except:
						printError("No connection to disconnect from ")
				else:
					printInfo("No connection to disconnect from")
				self.disconnectEvent.clear()

	def startStreaming(self):
		numofsamples = 0
		printing = False

		while not self.shutdownEvent.is_set():
			self.startStreamingEvent.wait(1)
			if self.startStreamingEvent.is_set():
				printing = True
				if self.connected.is_set():
					printInfo("Starting streaming...")
					while self.startStreamingEvent.is_set():
						try:
							sample = self.board.stream_one_sample()
							# append training class in the channel data before put in the buffer
							try:
								# check if training class has been changed, if so then replace
								if self.trainingClassBuffer.qsize() != 0:
									self.trainingClass = self.trainingClassBuffer.get()
							except Exception:
								printWarning("Something Went Wrong in boardEventHandler line 83")
							sample.channel_data.append(self.trainingClass)
							for buffer in self.dataBuffersList:
								try:
									buffer.put_nowait(sample.channel_data)
									self.newDataAvailable.set()
								except queue.Full:
									printWarning("Queue full")
							numofsamples += 1
						except Exception as e:
							self.startStreamingEvent.clear()
							exc_type, exc_obj, exc_tb = sys.exc_info()
							fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
							printError("There was a problem on starting streaming in: " + fname.__str__() +
							           ' line: ' + exc_tb.tb_lineno.__str__() + "\nError Message: " + repr(e))
				else:
					if not self.connected.is_set():
						printInfo("No connection to stop streaming from.")
				self.startStreamingEvent.clear()
			else:
				self.newDataAvailable.clear()
				if self.shutdownEvent.is_set():
					for buffer in self.dataBuffersList:
						if buffer.qsize() != 0:
							printInfo("Empty the queues")
						while not buffer.qsize() == 0:
							buffer.get_nowait()
				if printing:
					print(numofsamples)
					printing = False

	def stopStreaming(self):
		while not self.shutdownEvent.is_set():
			self.stopStreamingEvent.wait(1)
			if self.stopStreamingEvent.is_set():
				if self.connected.is_set() and self.startStreamingEvent.is_set():
					printInfo("Stopping streaming...")
					try:
						self.startStreamingEvent.clear()
						self.writeDataEvent.set()
						self.board.stopStreaming()
					except:
						printError("There is no stream to stop.")
				else:
					if not self.connected.is_set():
						printInfo("No connection to stop streaming from.")
					elif not self.startStreamingEvent.is_set():
						printInfo("No active streaming to stop.")
				self.stopStreamingEvent.clear()

	def newBoardSettingsAvailable(self):
		while not self.shutdownEvent.is_set():
			self.newBoardSettingsAvailableEvent.wait(1)
			if self.newBoardSettingsAvailableEvent.is_set():
				printInfo("New board setting Available...")
				self.board.setBoardSettingAttributes(self.boardSettings)
				self.newBoardSettingsAvailableEvent.clear()

	"""     Assistive functions     """

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

	def start(self, _shutdownEvent):
		procList = []
		self.shutdownEvent = _shutdownEvent
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
