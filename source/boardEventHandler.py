from multiprocessing import Process


class BoardEventHandler:
 	def __init__(self, board, boardApiCallEvents, boardSettings):
		self.board = board
		self.boardApiCallEvents = boardApiCallEvents
		self.boardSettings = boardSettings

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
		ev = self.boardApiCallEvents.startStreaming
		while True:
			ev.wait()
			print("startStreaming")
			ev.clear()

	def stopStreaming(self):
		ev = self.boardApiCallEvents.stopStreaming
		while True:
			ev.wait()
			print("stopStreaming")
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
        print("Starting eventHandler")
        connectProcess = Process(target=self.connect)
        disconnectProcess = Process(target=self.disconnect)
        startStreamingProcess = Process(target=self.startStreaming)
        stopStreamingProcess = Process(target=self.stopStreaming)
        newBoardSettingsAvailableProcess = Process(target=self.newBoardSettingsAvailable)

        connectProcess.start()
        disconnectProcess.start()
        startStreamingProcess.start()
        stopStreamingProcess.start()
        newBoardSettingsAvailableProcess.start()

        connectProcess.join()
        disconnectProcess.join()
        startStreamingProcess.join()
        stopStreamingProcess.join()
        newBoardSettingsAvailableProcess.join()
