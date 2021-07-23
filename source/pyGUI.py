import sys
from threading import Thread
import queue
import numpy as np
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import *
from checkComboBox import *
import pyqtgraph as pg

sys.path.append('..')
from utils.constants import Constants as cnst


class GUI(QMainWindow):
	def __init__(self, guiBuffer, newDataAvailableEvent, board, boardApiCallEvents, boardCytonSettings, _shutdownEvent,
	             writeDataEvent):
		super().__init__()
		# pg.setConfigOption('background', 'w')
		# pg.setConfigOption('foreground', 'k')
		self.guiBuffer = guiBuffer
		self.newDataAvailableEvent = newDataAvailableEvent
		self.board = board
		self.boardApiCallEvents = boardApiCallEvents
		self.shutdownEvent = _shutdownEvent
		self.writeDataEvent = writeDataEvent
		self.boardCytonSettings = boardCytonSettings
		self.graphData = []
		self.channelDataGraphWidgets = []
		# QMainWindow settings
		self.setWindowTitle("My GUI for Cyton Board")
		self.font = QFont('sanserif', 13)

		# create main widget will be used as CentralWidget in QMainWindow
		mainWidget = QWidget(parent=self)

		# add a menu bar
		self.menubar = self.menuBar()
		# add horizontal layout for the settings of the cyton board
		self.mainLayout = QGridLayout(mainWidget)
		self.boardSettingLayout = QHBoxLayout()
		self.mainLayout.addLayout(self.boardSettingLayout, 0, 0)
		# add a layout for the graphs
		self.graphLayout = QVBoxLayout()
		self.mainLayout.addLayout(self.graphLayout, 1, 0, 2, 5)

		# enable not stretching layouts on the vertical axis
		self.mainLayout.setRowStretch(self.mainLayout.rowCount(), 1)

		# init settings bar and menu bar
		self.initBoardSettingsBar()
		self.initMenuBar()

		# send board settings with current init choices
		self.freqComboClick(self.freqComboChoices.currentText())
		self.windowComboClick(self.timeWindowComboChoices.currentText())
		self.windowStepComboClick(self.stepWindowSizeComboChoices.currentText())
		self.filteringDataFunction(self.filterDataCheckbox.checkState())
		self.scalingDataFunction(self.scalingDataCheckbox.checkState())
		# set central widget
		self.setCentralWidget(mainWidget)
		#
		self.t_data = []
		self.t1 = Thread(target=self.acquirePlottingData)
		self.t1.daemon = True
		self.t1.start()
		self.timer = QTimer()
		self.timer.timeout.connect(self.graphUpdater)
		self.timer.setInterval(100)
		self.timer.start()

	#

	def initMenuBar(self):
		self.menubar.setFont(self.font)
		# Menu Bar options
		startStreamAction = QAction('&Start streaming', self)
		stopStreamAction = QAction('Sto&p streaming', self)
		connectAction = QAction('&Connect', self)
		disconnectAction = QAction('&Disconnect', self)
		quitting = QAction('&QUIT', self)

		graphs = self.menubar.addMenu('&Add Graphs')
		timeSeriesPlotAction = QAction('Time series', self)
		fftPlotAction = QAction('FFT', self)
		linearPlotAction = QAction('Linear', self)
		graphs.addActions([timeSeriesPlotAction, fftPlotAction, linearPlotAction])
		self.menubar.addActions(
			[startStreamAction, stopStreamAction, connectAction, disconnectAction, quitting])
		"""
				-MENU BAR ACTIONS FOR EACH OPTION 

		Adding every action in thread so as the GUI not freezing,
		when waiting each process to finished. In order to do this 
		we create a worker object, pass the function as argument,
		and then add the worker object to QThreadPool of GUI-QMainWindow
		object. Lastly pass this action in connect as lambda expression

		"""

		startStreamAction.triggered.connect(self.startStreaming)
		stopStreamAction.triggered.connect(self.stopStreaming)
		connectAction.triggered.connect(self.connectBoard)
		disconnectAction.triggered.connect(self.disconnectBoard)
		quitting.triggered.connect(self.quitGUI)

		timeSeriesPlotAction.triggered.connect(self.addTimeSeriesPlot)
		fftPlotAction.triggered.connect(self.addFFTPlot)
		linearPlotAction.triggered.connect(self.addLinearPlot)

		self.resize(1500, 800)

	def initBoardSettingsBar(self):
		boardSettingsSpacing = 30
		# create a combo menu for the frequencies bands
		freqCombo = QHBoxLayout()
		freqComboTitle = QLabel('Band pass frequencies:')
		self.freqComboChoices = QComboBox()
		freqComboTitle.setFont(self.font)
		self.freqComboChoices.setFont(self.font)
		self.freqComboChoices.setToolTip('Select the Frequencies where data will be filtered.')
		self.freqComboChoices.addItems(cnst.bandPassFreqList)
		freqCombo.addWidget(freqComboTitle)
		freqCombo.addWidget(self.freqComboChoices)
		self.freqComboChoices.activated[str].connect(self.freqComboClick)

		# add frequency combo to boardSettingLayout
		self.boardSettingLayout.addLayout(freqCombo)
		self.boardSettingLayout.addSpacing(boardSettingsSpacing)

		# create a combo menu for the Window choices
		timeWindowCombo = QHBoxLayout()
		timeWindowComboTitle = QLabel('Window size:')
		self.timeWindowComboChoices = QComboBox()
		timeWindowComboTitle.setFont(self.font)
		self.timeWindowComboChoices.setFont(self.font)
		self.timeWindowComboChoices.setEditable(True)
		self.timeWindowComboChoices.addItems(cnst.windowSizeList)
		timeWindowCombo.addWidget(timeWindowComboTitle)
		timeWindowCombo.addWidget(self.timeWindowComboChoices)
		self.timeWindowComboChoices.activated[str].connect(self.windowComboClick)

		# add timeWindow combo to boardSettingLayout
		self.boardSettingLayout.addLayout(timeWindowCombo)
		self.boardSettingLayout.addSpacing(boardSettingsSpacing)

		# create a combo menu for the stepWindowSize choices
		stepWindowSizeCombo = QHBoxLayout()
		stepWindowSizeComboTitle = QLabel('Step size:')
		self.stepWindowSizeComboChoices = QComboBox()
		stepWindowSizeComboTitle.setFont(self.font)
		self.stepWindowSizeComboChoices.setFont(self.font)
		self.stepWindowSizeComboChoices.setEditable(True)
		self.stepWindowSizeComboChoices.addItems(cnst.windowStepSizeList)
		stepWindowSizeCombo.addWidget(stepWindowSizeComboTitle)
		stepWindowSizeCombo.addWidget(self.stepWindowSizeComboChoices)
		self.stepWindowSizeComboChoices.activated[str].connect(self.windowStepComboClick)

		# add stepWindowSizeCombo combo to boardSettingLayout
		self.boardSettingLayout.addLayout(stepWindowSizeCombo)
		self.boardSettingLayout.addSpacing(boardSettingsSpacing)

		# add checkbox for enabling filtering Data
		self.filterDataCheckbox = QCheckBox("Filter Data")
		self.filterDataCheckbox.setChecked(True)
		self.filterDataCheckbox.setFont(self.font)
		self.filterDataCheckbox.stateChanged.connect(self.filteringDataFunction)
		self.boardSettingLayout.addWidget(self.filterDataCheckbox)
		self.boardSettingLayout.addSpacing(boardSettingsSpacing)

		# add checkbox for enabling scaling Data
		self.scalingDataCheckbox = QCheckBox("Scaling Data")
		self.scalingDataCheckbox.setChecked(True)
		self.scalingDataCheckbox.setFont(self.font)
		self.scalingDataCheckbox.stateChanged.connect(self.scalingDataFunction)
		self.boardSettingLayout.addWidget(self.scalingDataCheckbox)
		self.boardSettingLayout.addSpacing(boardSettingsSpacing)

		# add a push button to send query for RegisteSettings
		self.infoButton = QPushButton("Board info")
		self.infoButton.setFont(self.font)
		self.infoButton.clicked.connect(self.infoButtonClick)
		self.boardSettingLayout.addWidget(self.infoButton)
		self.boardSettingLayout.addSpacing(boardSettingsSpacing)

		# channelsList = ['channel 1', 'channel 2', 'channel 3', 'channel 4', 'channel 5', 'channel 6', 'channel 7',
		#            'channel 8']
		# channelsCombo = CheckComboBox(placeholderText='Enable Channels')
		# model = channelsCombo.model()
		# for i in range(len(channelsList)):
		#     channelsCombo.addItem(channelsList[i])
		#     model.item(i).setCheckable(True)
		#
		# channelsCombo.setFont(self.font)
		# channelsCombo.activated[str].connect(lambda: channelsComboChange("doklimi"))
		# self.boardSettingLayout.addWidget(channelsCombo)
		# self.boardSettingLayout.addSpacing(boardSettingsSpacing)

		self.boardSettingLayout.addStretch()

	def startStreaming(self):
		self.boardApiCallEvents.startStreaming.set()

	def stopStreaming(self):
		self.boardApiCallEvents.stopStreaming.set()

	def connectBoard(self):
		self.boardApiCallEvents.connect.set()

	def disconnectBoard(self):
		self.boardApiCallEvents.disconnect.set()

	def quitGUI(self):
		while self.writeDataEvent.is_set():
			pass
		self.shutdownEvent.set()
		QApplication.instance().quit()

	#  calling functions

	def channelsComboChange(self, choices):
		print("test")
		print(choices)

    def infoButtonClick(self, btn):
        self.board.setHigherBoundFrequency(200)
        print(self.board.getBoardType())
        # changing the text of label after button get clicked

	def freqComboClick(self, freq):
		try:
			lowerBound = int(freq.split("-")[0])
			upperBound = int(freq.split("-")[1])
			self.boardCytonSettings["lowerBand"] = lowerBound
			self.boardCytonSettings["upperBand"] = upperBound
			self.boardApiCallEvents.newBoardSettingsAvailable.set()
		except Exception:
			print("freqComboClick ERROR!")

	def windowComboClick(self, size):
		try:
			self.boardCytonSettings["windowSize"] = int(size)
			self.boardApiCallEvents.newBoardSettingsAvailable.set()
		except Exception:
			print("windowComboClick ERROR!")

	def windowStepComboClick(self, size):
		try:
			self.boardCytonSettings["windowStepSize"] = float(size)
			self.boardApiCallEvents.newBoardSettingsAvailable.set()
		except Exception:
			print("windowStepComboClick ERROR!")

	def filteringDataFunction(self, state):
		try:
			if state == Qt.Checked:
				self.boardCytonSettings["filtering_data"] = True
			else:
				self.boardCytonSettings["filtering_data"] = False
			self.boardApiCallEvents.newBoardSettingsAvailable.set()
		except Exception:
			print("filteringDataFunction ERROR!")

	def scalingDataFunction(self, state):
		try:
			if state == Qt.Checked:
				self.boardCytonSettings["scaling_output"] = True
			else:
				self.boardCytonSettings["scaling_output"] = False
			self.boardApiCallEvents.newBoardSettingsAvailable.set()
		except Exception:
			print("scalingDataFunction ERROR!")

	def addTimeSeriesPlot(self):
		for i in range(1, 9):
			graphWidget = pg.plot(title='Channel %d' % i,
			                      labels={'left': 'uV', 'bottom': 'sec'},
			                      )
			graphWidget.setStyleSheet("border : 2px solid black;"
			                          "padding : 0px;")
			self.channelDataGraphWidgets.append(graphWidget)
			self.graphLayout.addWidget(graphWidget)
		self.graphLayout.addStretch()

	def addFFTPlot(self):
		print('addFFTPlot')

	def addLinearPlot(self):
		print('addLinearPlot')

	def acquirePlottingData(self):
		while not self.shutdownEvent.is_set():
			self.newDataAvailableEvent.wait(1)
			if self.newDataAvailableEvent.is_set():
				try:
					dt = self.guiBuffer.get()
					if len(self.graphData) < self.board.getSampleRate() * 4:
						self.graphData.append(dt)
					else:
						del self.graphData[
						    0:len(self.graphData) - self.board.getSampleRate() * 4 + 1]
						self.graphData.append(dt)
				except queue.Empty:
					pass

	def graphUpdater(self):
		if not self.shutdownEvent.is_set():
			self.t_data = np.array(self.graphData).T
			for i in range(len(self.channelDataGraphWidgets)):
				if len(self.channelDataGraphWidgets) == 8:
					if len(self.t_data) > 0:
						self.channelDataGraphWidgets[i].clear()
						self.channelDataGraphWidgets[i].plot(pen=cnst.GUIChannelColors[i]).setData(self.t_data[i])


def startGUI(guiBuffer, newDataAvailableEvent, board, boardApiCallEvents, boardCytonSettings, _shutdownEvent,
             writeDataEvent):
	app = QApplication(sys.argv)
	gui = GUI(guiBuffer, newDataAvailableEvent, board, boardApiCallEvents, boardCytonSettings, _shutdownEvent,
	          writeDataEvent)
	gui.show()
	sys.exit(app.exec_())


if __name__ == "__main__":
	startGUI(None, None, None, None)
