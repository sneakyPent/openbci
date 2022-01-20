import sys
from threading import Thread
import queue
import numpy as np
from PyQt5.QtCore import QTimer, Qt, QRect
from PyQt5.QtGui import QFont, QTextCursor, QIcon, QPalette
from PyQt5.QtWidgets import *
import pyqtgraph as pg
from classification import *
from utils import filters
from utils.coloringPrint import printError, printInfo
from utils.constants import Constants as cnst, ElectrodeType
from utils import fft_analysis


class ComboBox(QComboBox):
	# https://code.qt.io/cgit/qt/qtbase.git/tree/src/widgets/widgets/qcombobox.cpp?h=5.15.2#n3173
	def paintEvent(self, event):

		painter = QStylePainter(self)
		painter.setPen(self.palette().color(QPalette.Text))

		# draw the combobox frame, focusrect and selected etc.
		opt = QStyleOptionComboBox()
		self.initStyleOption(opt)
		painter.drawComplexControl(QStyle.CC_ComboBox, opt)

		if self.currentIndex() < 0:
			opt.palette.setBrush(
				QPalette.ButtonText,
				opt.palette.brush(QPalette.ButtonText).color().lighter(),
			)
			if self.placeholderText():
				opt.currentText = self.placeholderText()

		# draw the icon and text
		painter.drawControl(QStyle.CE_ComboBoxLabel, opt)


class CheckableComboBox(ComboBox):
	def __init__(self):
		super().__init__()
		self.selectedItemsList = []
		self._changed = False
		self.currentIndexChanged.connect(self.getSelectedItems)
		self.view().pressed.connect(self.handleItemPressed)
		self.setPlaceholderText("None")
		self.setCurrentIndex(-1)

	def updatePlaceHolder(self):
		enabledChannels = self.getSelectedItems()
		if len(enabledChannels) > 0:
			self.setPlaceholderText([i + 1 for i in enabledChannels].__str__())
		elif len(enabledChannels) == 0:
			self.setPlaceholderText("None")
		self.setCurrentIndex(-1)
		self.setSizeAdjustPolicy(QComboBox.AdjustToContents)

	def setItemChecked(self, index, checked=False):
		item = self.model().item(index, self.modelColumn())  # QStandardItem object

		if checked:
			item.setCheckState(Qt.Checked)
		else:
			item.setCheckState(Qt.Unchecked)

	def handleItemPressed(self, index):
		item = self.model().itemFromIndex(index)

		if item.checkState() == Qt.Checked:
			# self.selectedItemsList.remove(index)
			item.setCheckState(Qt.Unchecked)
		else:
			item.setCheckState(Qt.Checked)
		# self.selectedItemsList.append(index)
		self._changed = True

	def hidePopup(self):
		if not self._changed:
			super().hidePopup()
		self._changed = False

	def itemChecked(self, index):
		item = self.model().item(index, self.modelColumn())
		return item.checkState() == Qt.Checked

	def getSelectedItems(self):
		lst = []
		for index in range(self.model().rowCount()):
			item = self.model().item(index)
			if item.checkState() == Qt.Checked:
				lst.append(item.row())
		return lst


class MyQComboBox(QComboBox):
	def addItems(self, Iterable, p_str=None):
		newIterable = []
		for vl in Iterable:
			if isinstance(vl, int):
				newIterable.append(vl.__str__())
		super().addItems(newIterable)


class MyStepSizeQComboBox(QComboBox):
	def addItems(self, Iterable, p_str=None):
		newIterable = []
		for vl in Iterable:
			val = float(vl) * cnst.SAMPLE_RATE_250
			if val.is_integer():
				newIterable.append(vl.__str__())
		super().addItems(newIterable)


class CustomDialog(QDialog):
	def __init__(self, parent=None, message=None, buttons=None):
		super().__init__(parent)
		self.buttons = buttons
		self.buttonBox = QDialogButtonBox(Qt.Horizontal)
		self.buttonBox.setCenterButtons(True)
		for btn in self.buttons:
			if isinstance(btn, str):
				findButton = QPushButton(self.tr(btn))
				findButton.setCheckable(True)
				findButton.setAutoDefault(False)
				self.buttonBox.addButton(findButton, QDialogButtonBox.ActionRole)

		self.buttonBox.clicked.connect(self.cl)

		self.layout = QVBoxLayout()
		msg = QLabel(message)
		self.layout.addWidget(msg)
		self.layout.addWidget(self.buttonBox)
		self.setLayout(self.layout)

	def cl(self, buttonClicked):
		# 1 and 2 used ny qDialog so we use 101 102 and we take the (qdialog.result mod 100)
		self.done(100 + self.buttons.index(buttonClicked.text()))


class GUI(QMainWindow):
	def __init__(self, guiBuffer, newDataAvailableEvent, board, boardApiCallEvents, boardCytonSettings, _shutdownEvent,
	             writeDataEvent, startTrainingEvent, startOnlineEvent):
		super().__init__()
		# pg.setConfigOption('background', 'w')
		# pg.setConfigOption('foreground', 'k')
		self.guiBuffer = guiBuffer
		self.newDataAvailableEvent = newDataAvailableEvent
		self.board = board
		self.boardApiCallEvents = boardApiCallEvents
		self.shutdownEvent = _shutdownEvent
		self.writeDataEvent = writeDataEvent
		self.startTrainingEvent = startTrainingEvent
		self.startOnlineEvent = startOnlineEvent
		self.boardCytonSettings = boardCytonSettings
		self.graphData = []
		self.channelDataGraphWidgets = []
		self.channelFftWidget = None
		# QMainWindow settings
		self.setWindowTitle("Cyton Board GUI")
		self.setWindowIcon(QIcon('../media/openbci_large.png'))
		self.font = QFont('Roboto', 11)

		# create main widget will be used as CentralWidget in QMainWindow
		mainWidget = QWidget(parent=self)

		# add a menu bar
		self.menubar = self.menuBar()
		self.mainLayout = QGridLayout(mainWidget)
		# add a radio button group for the electrodes
		self.electrodesRadio = QHBoxLayout()
		self.electrodesButtonGroup = QButtonGroup(self)
		self.wetButton = QRadioButton("WET")
		self.wetButton.toggled.connect(self.electrodesButtonClick)
		self.dryButton = QRadioButton("DRY")
		self.dryButton.toggled.connect(self.electrodesButtonClick)
		self.electrodesButtonGroup.addButton(self.wetButton,id=ElectrodeType.WET.value)
		self.electrodesButtonGroup.addButton(self.dryButton,id=ElectrodeType.DRY.value)
		reqComboTitle = QLabel('Using Electrodes')
		self.electrodesRadio.addWidget(reqComboTitle)
		self.electrodesRadio.addWidget(self.wetButton)
		self.electrodesRadio.addWidget(self.dryButton)
		self.electrodesRadio.addStretch()
		# add horizontal layout for the settings of the cyton board
		self.boardSettingLayout = QVBoxLayout()
		self.mainLayout.addLayout(self.electrodesRadio, 0, 0)
		self.mainLayout.addLayout(self.boardSettingLayout, 1, 0)

		# add a layout for the graphs
		self.graphLayout = QVBoxLayout()
		self.mainLayout.addLayout(self.graphLayout, 2, 0, -1, 2)

		# add a layout for the fft
		self.fftLayout = QVBoxLayout()
		self.mainLayout.addLayout(self.fftLayout, 2, 2, -1, -1)

		# enable not stretching layouts on the vertical axis
		self.mainLayout.setRowStretch(self.mainLayout.rowCount(), 1)

		# init settings bar and menu bar
		self.initBoardSettingsBar()
		self.initMenuBar()

		# send board settings with current init choices
		self.initBoardSettings()

		# set central widget
		self.setCentralWidget(mainWidget)
		#
		self.t_data = []
		self.t1 = Thread(target=self.acquirePlottingData)
		self.t1.daemon = True
		self.t1.start()
		self.timer = QTimer()
		self.timer.timeout.connect(self.graphUpdater)
		self.timer.timeout.connect(self.fftUpdater)
		self.timer.setInterval(50)
		self.timer.start()

	def initMenuBar(self):
		self.menubar.setFont(self.font)
		# Menu Bar options
		boardInfo = QAction('&Board Info', self)
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
		tests = self.menubar.addMenu('Tests')
		connectToInternalGND = QAction("Connecting all pins to ground", self)
		connectToDCSignal = QAction("Connecting all pins to Vcc", self)
		connectingPinsToLowFrequency1xAmpSignal = QAction("Connecting pins to low frequency 1x amp signal", self)
		connectingPinsToHighFrequency1xAmpSignal = QAction("Connecting pins to high frequency 1x amp signal", self)
		connectingPinsToLowFrequency2xAmpSignal = QAction("Connecting pins to low frequency 2x amp signal", self)
		connectingPinsToHighFrequency2xAmpSignal = QAction("Connecting pins to high frequency 2x amp signal", self)
		tests.addActions([connectToInternalGND, connectToDCSignal, connectingPinsToLowFrequency1xAmpSignal,
		                  connectingPinsToHighFrequency1xAmpSignal, connectingPinsToLowFrequency2xAmpSignal,
		                  connectingPinsToHighFrequency2xAmpSignal])
		self.menubar.addActions(
			[boardInfo, startStreamAction, stopStreamAction, connectAction, disconnectAction, quitting])
		boardInfo.triggered.connect(self.printBoardInfo)
		startStreamAction.triggered.connect(self.startStreaming)
		stopStreamAction.triggered.connect(self.stopStreaming)
		connectAction.triggered.connect(self.connectBoard)
		disconnectAction.triggered.connect(self.disconnectBoard)
		quitting.triggered.connect(self.quitGUI)

		timeSeriesPlotAction.triggered.connect(self.addTimeSeriesPlot)
		fftPlotAction.triggered.connect(self.addFFTPlot)
		linearPlotAction.triggered.connect(self.addLinearPlot)

		connectToInternalGND.triggered.connect(lambda: self.startTest(0))
		connectToDCSignal.triggered.connect(lambda: self.startTest(1))
		connectingPinsToLowFrequency1xAmpSignal.triggered.connect(lambda: self.startTest(2))
		connectingPinsToHighFrequency1xAmpSignal.triggered.connect(lambda: self.startTest(3))
		connectingPinsToLowFrequency2xAmpSignal.triggered.connect(lambda: self.startTest(4))
		connectingPinsToHighFrequency2xAmpSignal.triggered.connect(lambda: self.startTest(5))

		# self.resize(1500, 800)
		self.resize(1000, 100)

	def initBoardSettingsBar(self):
		self.horizontalGroupBox = QGroupBox()
		layout = QHBoxLayout()
		boardSettingsSpacing = 30
		# create a combo menu for the frequencies bands
		freqCombo = QHBoxLayout()
		freqComboTitle = QLabel('Bandpass freq:')
		self.freqComboChoices = QComboBox()
		freqComboTitle.setFont(self.font)
		self.freqComboChoices.setFont(self.font)
		self.freqComboChoices.setToolTip('Select the Frequencies where data will be filtered.')
		self.freqComboChoices.addItems(cnst.bandPassFreqList)
		# Set the init value form the cnst.bandPassFreqList
		initValueIndex = cnst.bandPassFreqList.index(cnst.initBandPassFreqList)
		self.freqComboChoices.setCurrentIndex(initValueIndex)
		freqCombo.addWidget(freqComboTitle)
		freqCombo.addWidget(self.freqComboChoices)
		self.freqComboChoices.currentIndexChanged.connect(self.freqComboClick)

		# add frequency combo to boardSettingLayout
		layout.addLayout(freqCombo)
		layout.addSpacing(boardSettingsSpacing)

		# create a combo menu for the channels
		channelsCombo = QHBoxLayout()
		channelsComboTitle = QLabel('channels: ')
		self.channelsComboChoices = CheckableComboBox()
		self.channelsComboChoices.setFont(self.font)
		for idx, val in enumerate(cnst.channelsList):
			self.channelsComboChoices.addItem(val)
			if idx in cnst.initEnabledChannels:
				self.channelsComboChoices.setItemChecked(idx, True)
			else:
				self.channelsComboChoices.setItemChecked(idx, False)
		self.channelsComboChoices.setSizeAdjustPolicy(QComboBox.AdjustToContents)
		channelsComboTitle.setFont(self.font)
		channelsCombo.addWidget(channelsComboTitle)
		channelsCombo.addWidget(self.channelsComboChoices)
		self.channelsComboChoices.currentIndexChanged.connect(self.channelComboClick)
		self.channelsComboChoices.updatePlaceHolder()

		# add timeWindow combo to boardSettingLayout
		layout.addLayout(channelsCombo)
		layout.addSpacing(boardSettingsSpacing)

		# create a combo menu for the Window choices
		timeWindowCombo = QHBoxLayout()
		timeWindowComboTitle = QLabel('Window size:')
		self.timeWindowComboChoices = MyQComboBox()
		timeWindowComboTitle.setFont(self.font)
		self.timeWindowComboChoices.setFont(self.font)
		self.timeWindowComboChoices.setEditable(True)
		self.timeWindowComboChoices.addItems(cnst.windowSizeList)
		self.timeWindowComboChoices.setSizeAdjustPolicy(QComboBox.AdjustToContents)
		# Set the init value form the cnst.windowSizeList
		initValueIndex = cnst.windowSizeList.index(cnst.initWindowSizeValue)
		self.timeWindowComboChoices.setCurrentIndex(initValueIndex)
		timeWindowCombo.addWidget(timeWindowComboTitle)
		timeWindowCombo.addWidget(self.timeWindowComboChoices)
		self.timeWindowComboChoices.currentIndexChanged.connect(self.windowComboClick)

		# add timeWindow combo to boardSettingLayout
		layout.addLayout(timeWindowCombo)
		layout.addSpacing(boardSettingsSpacing)

		# create a combo menu for the stepWindowSize choices
		stepWindowSizeCombo = QHBoxLayout()
		stepWindowSizeComboTitle = QLabel('Step size:')
		self.stepWindowSizeComboChoices = MyStepSizeQComboBox()
		stepWindowSizeComboTitle.setFont(self.font)
		self.stepWindowSizeComboChoices.setFont(self.font)
		self.stepWindowSizeComboChoices.setEditable(True)
		self.stepWindowSizeComboChoices.addItems(cnst.windowStepSizeList)
		self.stepWindowSizeComboChoices.setSizeAdjustPolicy(QComboBox.AdjustToContents)
		# Set the init value form the cnst.windowSizeList
		initValueIndex = cnst.windowStepSizeList.index(cnst.initStepSizeValue)
		self.stepWindowSizeComboChoices.setCurrentIndex(initValueIndex)
		stepWindowSizeCombo.addWidget(stepWindowSizeComboTitle)
		stepWindowSizeCombo.addWidget(self.stepWindowSizeComboChoices)
		self.stepWindowSizeComboChoices.currentIndexChanged.connect(self.windowStepComboClick)

		# add stepWindowSizeCombo combo to boardSettingLayout
		layout.addLayout(stepWindowSizeCombo)
		layout.addSpacing(boardSettingsSpacing)

		# add checkbox for enabling filtering Data
		self.filterDataCheckbox = QCheckBox("Filter Data")
		self.filterDataCheckbox.setChecked(False)
		self.filterDataCheckbox.setFont(self.font)
		self.filterDataCheckbox.stateChanged.connect(self.filteringDataFunction)
		layout.addWidget(self.filterDataCheckbox)
		layout.addSpacing(boardSettingsSpacing)

		# add checkbox for enabling scaling Data
		self.scalingDataCheckbox = QCheckBox("Scaling Data")
		self.scalingDataCheckbox.setChecked(True)
		self.scalingDataCheckbox.setFont(self.font)
		self.scalingDataCheckbox.stateChanged.connect(self.scalingDataFunction)
		layout.addWidget(self.scalingDataCheckbox)
		layout.addSpacing(boardSettingsSpacing)

		# add a push button to plot FFT from specific file
		self.plotFftButton = QPushButton("Plot stream FFT")
		self.plotFftButton.setFont(self.font)
		self.plotFftButton.clicked.connect(self.plotFftButtonClick)
		layout.addWidget(self.plotFftButton)
		layout.addSpacing(boardSettingsSpacing)

		# add a push button to start Training mode
		self.classificationButton = QPushButton("Classification")
		self.classificationButton.setFont(self.font)
		self.classificationButton.clicked.connect(self.classificationButtonClick)
		layout.addWidget(self.classificationButton)
		layout.addSpacing(boardSettingsSpacing)

		# add a push button to start Training mode
		self.trainingButton = QPushButton("Training")
		self.trainingButton.setFont(self.font)
		self.trainingButton.clicked.connect(self.trainingButtonClick)
		layout.addWidget(self.trainingButton)
		layout.addSpacing(boardSettingsSpacing)

		# add a push button to start Training mode
		self.onlineButton = QPushButton("Online")
		self.onlineButton.setFont(self.font)
		self.onlineButton.clicked.connect(self.onlineButtonClick)
		layout.addWidget(self.onlineButton)
		layout.addSpacing(boardSettingsSpacing)

		layout.addStretch()
		self.horizontalGroupBox.setLayout(layout)
		self.boardSettingLayout.addWidget(self.horizontalGroupBox)

	# send board settings with current init choices
	def initBoardSettings(self):
		self.freqComboClick(self.freqComboChoices.currentIndex())
		self.channelComboClick()
		self.windowComboClick()
		self.windowStepComboClick()
		self.filteringDataFunction(self.filterDataCheckbox.checkState())
		self.scalingDataFunction(self.scalingDataCheckbox.checkState())
		self.electrodesButtonGroup.button(cnst.initUsingElectrodes.value).setChecked(True)

	def startStreaming(self):
		self.boardApiCallEvents["startStreaming"].set()

	def stopStreaming(self):
		self.boardApiCallEvents["stopStreaming"].set()

	def connectBoard(self):
		self.boardApiCallEvents["connect"].set()

	def disconnectBoard(self):
		self.boardApiCallEvents["disconnect"].set()

	def quitGUI(self):
		if self.board.isStreaming():
			printInfo('Exiting GUI')
			self.stopStreaming()
		while self.writeDataEvent.is_set():
			pass
		self.shutdownEvent.set()
		QApplication.instance().quit()

	#  calling functions
	def electrodesButtonClick(self, state):
		try:
			button = self.sender()
			if button.isChecked():
				self.boardCytonSettings["usingElectrodes"] = ElectrodeType[button.text()]
				self.boardApiCallEvents["newBoardSettingsAvailable"].set()
		except Exception:
			self.logger.error(msg="electrodesButtonClick ERROR!", exc_info=True)

	def trainingButtonClick(self):
		self.startTrainingEvent.set()

	def onlineButtonClick(self):
		self.startOnlineEvent.set()

	def plotFftButtonClick(self):
		options = QFileDialog.Options()
		options |= QFileDialog.DontUseNativeDialog
		file_filter = 'HDF5 File (*.hdf5 )'
		fileNames, _ = QFileDialog.getOpenFileNames(self, "Choose HDF5 Stream file ",
		                                            directory="../streamData",
		                                            filter=file_filter, options=options)
		btns = ['one', 'four']
		if fileNames:
			dlg = CustomDialog(parent=self,
			                   message="How many different target classes in the file? ",
			                   buttons=btns)
			if dlg.exec():
				# The CustomDialog.result() returns the index of the pressed button
				# 1 and 2 used ny qDialog so we use 101 102 and we take the (qdialog.result mod 100)
				btnIndex = dlg.result() % 100
				if btns[btnIndex] == 'one':
					fft_analysis.printUniqueFFT(fileNames,
					                            lowCut=self.board.getLowerBoundFrequency(),
					                            highCut=self.board.getHigherBoundFrequency(),
					                            fs=self.board.getSampleRate(),
					                            enabledChannel=self.board.getEnabledChannels(),
					                            usingElectrodes=self.board.getUsingElectrodes())
				elif btns[btnIndex] == 'four':
					fft_analysis.printFFT(fileNames,
					                      lowCut=self.board.getLowerBoundFrequency(),
					                      highCut=self.board.getHigherBoundFrequency(),
					                      fs=self.board.getSampleRate(),
					                      enabledChannel=self.board.getEnabledChannels(),
					                      usingElectrodes=self.board.getUsingElectrodes())

	def classificationButtonClick(self):
		options = QFileDialog.Options()
		options |= QFileDialog.DontUseNativeDialog
		file_filter = 'HDF5 File (*.hdf5 )'
		fileNames, _ = QFileDialog.getOpenFileNames(self, "Choose HDF5 Stream file ",
		                                            directory="../streamData",
		                                            filter=file_filter, options=options)
		if fileNames:
			classificationOpenBCI.classify(fileNames, enabledChannels=self.board.getEnabledChannels())

	def freqComboClick(self, index):
		try:
			freq = cnst.bandPassFreqList[index]
			lowerBound = int(freq.split("-")[0])
			upperBound = int(freq.split("-")[1])
			self.boardCytonSettings["lowerBand"] = lowerBound
			self.boardCytonSettings["upperBand"] = upperBound
			self.boardApiCallEvents["newBoardSettingsAvailable"].set()
		except Exception as ex:
			printError("freqComboClick ERROR! " + ex.__str__())

	def channelComboClick(self):
		enabledChannels = self.channelsComboChoices.getSelectedItems()

		self.boardCytonSettings["enabledChannels"] = enabledChannels
		self.boardApiCallEvents["newBoardSettingsAvailable"].set()
		self.channelsComboChoices.updatePlaceHolder()

	def windowComboClick(self):
		try:
			self.boardCytonSettings["windowSize"] = int(self.timeWindowComboChoices.currentText())
			self.boardApiCallEvents["newBoardSettingsAvailable"].set()
		except Exception:
			self.timeWindowComboChoices.removeItem(self.timeWindowComboChoices.currentIndex())
			# Set the init value form the cnst.windowSizeList
			initValueIndex = cnst.windowSizeList.index(cnst.initWindowSizeValue)
			self.timeWindowComboChoices.setCurrentIndex(initValueIndex)
			printInfo("Non-Valid value: Window size can only be an integer")

	def windowStepComboClick(self):
		val = float(self.stepWindowSizeComboChoices.currentText()) * cnst.SAMPLE_RATE_250
		try:
			if not val.is_integer():
				raise ValueError
			self.boardCytonSettings["windowStepSize"] = float(self.stepWindowSizeComboChoices.currentText())
			self.boardApiCallEvents["newBoardSettingsAvailable"].set()
		except ValueError:
			printError("Non-Valid value: stepSize * samplingRate must be an integer")
		except Exception as ex:
			printError(ex.__str__())
			initValueIndex = cnst.windowStepSizeList.index(cnst.initStepSizeValue)
			self.stepWindowSizeComboChoices.setCurrentIndex(initValueIndex)
			self.stepWindowSizeComboChoices.removeItem(self.stepWindowSizeComboChoices.currentIndex())

	def filteringDataFunction(self, state):
		try:
			if state == Qt.Checked:
				self.boardCytonSettings["filtering_data"] = True
			else:
				self.boardCytonSettings["filtering_data"] = False
			self.boardApiCallEvents["newBoardSettingsAvailable"].set()
		except Exception as ex:
			printError("filteringDataFunction ERROR! " + ex.__str__())

	def scalingDataFunction(self, state):
		try:
			if state == Qt.Checked:
				self.boardCytonSettings["scaling_output"] = True
			else:
				self.boardCytonSettings["scaling_output"] = False
			self.boardApiCallEvents["newBoardSettingsAvailable"].set()
		except Exception as ex:
			printError("scalingDataFunction ERROR! " + ex.__str__())

	def addTimeSeriesPlot(self):
		for i in range(1, 9):
			graphWidget = pg.PlotWidget(title='Channel %d' % i)
			graphWidget.setLabel('left', 'Voltage (uv)')
			graphWidget.setLabel('bottom', 'Time (sec)')
			self.channelDataGraphWidgets.append(graphWidget)
			self.graphLayout.addWidget(graphWidget)
		self.graphLayout.addStretch()

	def addFFTPlot(self):
		graphWidget = pg.PlotWidget()
		graphWidget.setTitle("FFT Plot", size="20pt")
		graphWidget.setXRange(0, 10, padding=0)
		self.channelFftWidget = graphWidget
		self.fftLayout.addWidget(graphWidget)

	def addLinearPlot(self):
		print('addLinearPlot')

	def acquirePlottingData(self):
		while not self.shutdownEvent.is_set():
			self.newDataAvailableEvent.wait(1)
			if self.newDataAvailableEvent.is_set():
				try:
					dt = self.guiBuffer.get()[0:8]
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

	def fftUpdater(self):
		if not self.shutdownEvent.is_set() and self.channelFftWidget:
			d1 = np.array(self.graphData)
			if len(self.t_data) > 0:
				lowcut = self.board.getLowerBoundFrequency()
				highcut = self.board.getHigherBoundFrequency()
				fs = self.board.getSampleRate()
				channels = 8
				freq_6 = d1[:, 0:channels]
				mm = np.array(freq_6)
				tt = mm[1:]
				freq_6 = tt
				data_processed_freq_6 = []
				i = 0

				while i < freq_6.shape[1]:
					# bandpass filtering            !! ATTENTION: how many channels you want<
					data_filt = filters.butter_bandpass_filter(freq_6[:, i], lowcut, highcut, fs, order=10)
					# hamming window
					data_fft = np.abs(np.fft.fft(data_filt)) ** 2
					# # fft
					data_processed_freq_6.append(data_fft)  # = np.array(data_processed)
					i = i + 1

				time_step = 1 / fs

				colors = cnst.GUIChannelColors[0:channels]
				lb = ['ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6', 'ch7', 'ch8']

				# calculate the frequencies
				freqs3 = np.fft.fftfreq(freq_6[:, 0].size, time_step)
				idx3 = np.argsort(freqs3)

				for w in range(len(data_processed_freq_6)):
					ps = data_processed_freq_6[w]
					self.channelFftWidget.clear()
					self.channelFftWidget.plot(pen=colors[w], label=lb[w]).setData(freqs3[idx3], ps[idx3])

	def startTest(self, signal):
		print(signal)
		self.board.test_signal(signal)

	def printBoardInfo(self):
		self.board.print_register_settings()


def startGUI(guiBuffer, newDataAvailableEvent, board, boardApiCallEvents, boardCytonSettings, _shutdownEvent,
             writeDataEvent, startTrainingEvent, startOnlineEvent):
	app = QApplication(sys.argv)
	gui = GUI(guiBuffer, newDataAvailableEvent, board, boardApiCallEvents, boardCytonSettings, _shutdownEvent,
	          writeDataEvent, startTrainingEvent, startOnlineEvent)
	gui.show()
	sys.exit(app.exec_())


if __name__ == "__main__":
	startGUI(None, None, None, None)
