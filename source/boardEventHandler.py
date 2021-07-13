from multiprocessing import Process
from multiprocessing.managers import BaseManager


# TODO : check all exceptions
#           E.G. no board found, start before connect..

class BoardEventHandler:

	def __init__(self, board, boardApiCallEvents, boardSettings, dataManagerEvents, dataBuffer):
		self.board = board
		self.boardApiCallEvents = boardApiCallEvents
		self.dataManagerEvents = dataManagerEvents
		self.boardSettings = boardSettings
		self.dataBuffer = dataBuffer

	def connect(self):
		ev = self.boardApiCallEvents.connect
		while True:
			ev.wait()
			self.board.connect()
			ev.clear()

	def disconnect(self):
		ev = self.boardApiCallEvents.disconnect
		while True:
			ev.wait()
			print("disconnect")
			self.board.disconnect()
			ev.clear()

	def startStreaming(self):
		class MyManager(BaseManager):
			pass

		class SampleHandler:
			tst = self.dataBuffer
			e = self.dataManagerEvents

			def addInQueue(self, sample):
				self.tst.put(sample.channel_data)
				self.e.share.set()

			def printSample(self, sample):
				print(sample.channel_data)

		MyManager.register('SampleHandler', SampleHandler)

		manager = MyManager()
		manager.start()
		sampleHandler = manager.SampleHandler()

		ev = self.boardApiCallEvents.startStreaming
		while True:
			ev.wait()
			print("startStreaming")
			ev.clear()
			self.board.start_streaming(sampleHandler.addInQueue)

	def stopStreaming(self):
		ev = self.boardApiCallEvents.stopStreaming
		while True:
			ev.wait()
			print("stopStreaming")
			self.board.stopStreaming()
			# self.dataManagerEvents.share.clear()
			ev.clear()

	def newBoardSettingsAvailable(self):
		ev = self.boardApiCallEvents.newBoardSettingsAvailable
		while True:
			ev.wait()
			print("newBoardSettingsAvailable-------")
			if self.boardSettings["lowerBand"] != self.board.getLowerBoundFrequency():
				self.board.setLowerBoundFrequency(self.boardSettings["lowerBand"])
			if self.boardSettings["upperBand"] != self.board.getHigherBoundFrequency():
				self.board.setHigherBoundFrequency(self.boardSettings["upperBand"])
			if self.boardSettings["windowSize"] != self.board.getWindowSize():
				self.board.setWindowSize(self.boardSettings["windowSize"])
			if self.boardSettings["filtering_data"] != self.board.isFilteringData():
				self.board.setFilteringData(self.boardSettings["filtering_data"])
			if self.boardSettings["scaling_output"] != self.board.isScalingOutput():
				self.board.setScaledOutput(self.boardSettings["scaling_output"])
			ev.clear()

	def start(self):
		procList = []
		try:
			print("Starting eventHandler")
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
		except KeyboardInterrupt:
			# terminate processes
			for proc in procList:
				proc.terminate()
