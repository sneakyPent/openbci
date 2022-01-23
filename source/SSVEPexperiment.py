"""
This experiment was created using PsychoPy2 Experiment Builder (v1.82.01), 2015_10_16_1216
If you publish work using this script please cite the relevant PsychoPy publications
  Peirce, JW (2007) PsychoPy - Psychophysics software in Python. Journal of Neuroscience Methods, 162(1-2), 8-13.
  Peirce, JW (2009) Generating stimuli for neuroscience using PsychoPy. Frontiers in Neuroinformatics, 2:10. doi: 10.3389/neuro.11.010.2008
"""

# from __future__ import division  # so that 1/3=0.333 instead of 1/3=0
from asyncio import subprocess
from psychopy import visual, core, event, logging
from psychopy.constants import STARTED, NOT_STARTED, FINISHED  # things like STARTED, FINISHED
import numpy as np
import os  # handy system and path functions
import pylab
from time import process_time
from multiprocessing import Process, Queue
from PIL import Image
import cv2
import threading
from time import time, sleep
from playsound import playsound
from multiprocessing import Event
from utils.coloringPrint import printError, printHeader, printInfo, printWarning
from utils.constants import Constants as cnst


class Error(Exception):
	"""Base class for other exceptions"""
	pass


class psychopyWindowTermination(Error):
	"""Raised when there is a problem with the socket connection to unity application"""
	pass


# .............................................global variables ...........................................................

# set size variables
checker_s = 15  # checker size
checker_num = 10  # number of rows (and columns, i.e. checkers) of checkerboard
arrow_s = 50  # arrow size from center to peak vertex
rect_s = 30  # center rectangle half size

# set duration variables
targets_num = 4  # number of targets
videoW = 640  # width of video used in online mode
videoH = 480


# ...........................thread that will continuously read from the ip camera..........................................
class CameraRead(threading.Thread):
	def __init__(self, captureInst, imgT):
		threading.Thread.__init__(self)
		self.CaptureInst = captureInst
		self.ImgT = imgT

	def run(self):
		while (1):
			retT, self.ImgT = self.CaptureInst.read()
	# cv2.waitKey(100)


# ....................................................initialization and flash functions ..........................................................

def set_checkerboards_position(window):
	videoW = 640  # width of video used in online mode
	videoH = 480  # height of video used in online mode

	# distance between the right side of left checkerboard andthe left side of the video used online
	distance = (window.size[1]) / 2 - checker_s * checker_num - videoH / 2

	checkerboards_position = [[0 for j in range(2)] for i in range(4)]  # Positions of all 4 checkerboards
	checkerboards_position[0] = [-(videoW + distance * 2 + checker_s * checker_num) / 2,
	                             (window.size[1] - checker_s * checker_num) / 3]  # left
	checkerboards_position[1] = [(videoW + distance * 2 + checker_s * checker_num) / 2,
	                             (window.size[1] - checker_s * checker_num) / 3]  # right
	checkerboards_position[2] = [-(videoW + distance * 2 + checker_s * checker_num) / 2,
	                             -(window.size[1] - checker_s * checker_num) / 3]  # back
	checkerboards_position[3] = [(videoW + distance * 2 + checker_s * checker_num) / 2,
	                             -(window.size[1] - checker_s * checker_num) / 3]  # forward
	# checkerboards_position[0] = [0, (window.size[1]-checker_s*checker_num)/2]  # up
	# checkerboards_position[1] = [(videoW+distance*2+checker_s*checker_num)/2 , 0]  # right not at the edge of the screen
	# checkerboards_position[2] = [0, -(window.size[1]-checker_s*checker_num)/2]  # down
	# checkerboards_position[3] = [-(videoW+distance*2+checker_s*checker_num)/2 ,0]  # left  not at the edge of the screen

	return checkerboards_position


def set_arrows_position(checkerboards_position):
	arrows_position = [[0 for j in range(2)] for i in range(4)]  # Positions of all 4 arrows
	arrows_position[0] = [int(round(checkerboards_position[0][0])),
	                      int(round(checkerboards_position[0][1] / 2))]  # left
	arrows_position[1] = [int(round(checkerboards_position[1][0])),
	                      int(round(checkerboards_position[1][1] / 2))]  # right
	arrows_position[2] = [int(round(checkerboards_position[2][0])),
	                      int(round(checkerboards_position[2][1] / 2))]  # back
	arrows_position[3] = [int(round(checkerboards_position[3][0])),
	                      int(round(checkerboards_position[3][1] / 2))]  # forward

	return arrows_position


# flash stimuli initialization
def flash_init(win_local, position, square_size, columns, rows, mode):
	global flash_up_ON, flash_right_ON, flash_down_ON, flash_left_ON, flash_up_OFF, flash_right_OFF, flash_down_OFF, flash_left_OFF
	col2 = [0, 0, 0]  # black

	if mode == False:
		col1 = [255, 0, 0]  # red
	elif mode == True:
		col1 = [255, 255, 255]  # white
	# col2 = [-1, -1, -1] #black

	cell_number = columns * rows
	f_colors = []
	f_colors2 = []

	# fill an array with coordinate for each color square. First square should be at the upper left
	# and next should follow from left to right and up to down.
	xys = []
	x_left = (1 - columns) * square_size / 2
	y_top = (1 - rows) * square_size / 2
	for l in range(rows):
		for c in range(columns):
			xys.append((x_left + c * square_size, y_top + l * square_size))

	for i in range(rows):
		for j in range(columns):
			if (i % 2 == 1 and j % 2 == 1) or (i % 2 == 0 and j % 2 == 0):
				f_colors.append(col1)
			else:
				f_colors.append(col2)

	for i in range(rows):
		for j in range(columns):
			if (i % 2 == 1 and j % 2 == 1) or (i % 2 == 0 and j % 2 == 0):
				f_colors2.append(col2)
			else:
				f_colors2.append(col1)

	flash_left_ON = visual.ElementArrayStim(win=win_local,
	                                        fieldPos=position[0],
	                                        fieldShape='sqr',
	                                        nElements=cell_number,
	                                        sizes=square_size,
	                                        xys=xys,
	                                        colors=f_colors,
	                                        colorSpace='rgb255',
	                                        elementTex=None,
	                                        elementMask=None,
	                                        name='flash',
	                                        autoLog=False)
	flash_right_ON = visual.ElementArrayStim(win=win_local,
	                                         fieldPos=position[1],
	                                         fieldShape='sqr',
	                                         nElements=cell_number,
	                                         sizes=square_size,
	                                         xys=xys,
	                                         colors=f_colors,
	                                         colorSpace='rgb255',
	                                         elementTex=None,
	                                         elementMask=None,
	                                         name='flash',
	                                         autoLog=False)
	flash_down_ON = visual.ElementArrayStim(win=win_local,
	                                        fieldPos=position[2],
	                                        fieldShape='sqr',
	                                        nElements=cell_number,
	                                        sizes=square_size,
	                                        xys=xys,
	                                        colors=f_colors,
	                                        colorSpace='rgb255',
	                                        elementTex=None,
	                                        elementMask=None,
	                                        name='flash',
	                                        autoLog=False)
	flash_up_ON = visual.ElementArrayStim(win=win_local,
	                                      fieldPos=position[3],
	                                      fieldShape='sqr',
	                                      nElements=cell_number,
	                                      sizes=square_size,
	                                      xys=xys,
	                                      colors=f_colors,
	                                      colorSpace='rgb255',
	                                      elementTex=None,
	                                      elementMask=None,
	                                      name='flash',
	                                      autoLog=False)
	flash_left_OFF = visual.ElementArrayStim(win=win_local,
	                                         fieldPos=position[0],
	                                         fieldShape='sqr',
	                                         nElements=cell_number,
	                                         sizes=square_size,
	                                         xys=xys,
	                                         colors=f_colors2,
	                                         colorSpace='rgb255',
	                                         elementTex=None,
	                                         elementMask=None,
	                                         name='flash',
	                                         autoLog=False)

	flash_right_OFF = visual.ElementArrayStim(win=win_local,
	                                          fieldPos=position[1],
	                                          fieldShape='sqr',
	                                          nElements=cell_number,
	                                          sizes=square_size,
	                                          xys=xys,
	                                          colors=f_colors2,
	                                          colorSpace='rgb255',
	                                          elementTex=None,
	                                          elementMask=None,
	                                          name='flash',
	                                          autoLog=False)
	flash_down_OFF = visual.ElementArrayStim(win=win_local,
	                                         fieldPos=position[2],
	                                         fieldShape='sqr',
	                                         nElements=cell_number,
	                                         sizes=square_size,
	                                         xys=xys,
	                                         colors=f_colors2,
	                                         colorSpace='rgb255',
	                                         elementTex=None,
	                                         elementMask=None,
	                                         name='flash',
	                                         autoLog=False)
	flash_up_OFF = visual.ElementArrayStim(win=win_local,
	                                       fieldPos=position[3],
	                                       fieldShape='sqr',
	                                       nElements=cell_number,
	                                       sizes=square_size,
	                                       xys=xys,
	                                       colors=f_colors2,
	                                       colorSpace='rgb255',
	                                       elementTex=None,
	                                       elementMask=None,
	                                       name='flash',
	                                       autoLog=False)


# Arrows initialization
def arrow_init(window, position):
	global triangle_up, triangle_right, triangle_down, triangle_left, rect_center, rect_center_eyes

	triangle_up = visual.ShapeStim(win=window, name='triangle_up', units='pix',
	                               vertices=[[0, arrow_s], [arrow_s / 2, -arrow_s], [0, -arrow_s / 2],
	                                         [-arrow_s / 2, -arrow_s]],
	                               ori=0, pos=position[0],
	                               lineWidth=1, lineColor=[255, 255, 128], lineColorSpace='rgb255',
	                               fillColor=[255, 255, 128], fillColorSpace='rgb255',
	                               opacity=1, depth=-2.0,
	                               interpolate=True)
	triangle_right = visual.ShapeStim(win=window, name='triangle_right', units='pix',
	                                  vertices=[[0, arrow_s], [arrow_s / 2, -arrow_s], [0, -arrow_s / 2],
	                                            [-arrow_s / 2, -arrow_s]],
	                                  ori=0, pos=position[1],
	                                  lineWidth=1, lineColor=[255, 255, 128], lineColorSpace='rgb255',
	                                  fillColor=[255, 255, 128], fillColorSpace='rgb255',
	                                  opacity=1, depth=-2.0,
	                                  interpolate=True)
	triangle_down = visual.ShapeStim(win=window, name='triangle_down', units='pix',
	                                 vertices=[[0, arrow_s], [arrow_s / 2, -arrow_s], [0, -arrow_s / 2],
	                                           [-arrow_s / 2, -arrow_s]],
	                                 ori=180, pos=position[2],
	                                 lineWidth=1, lineColor=[255, 255, 128], lineColorSpace='rgb255',
	                                 fillColor=[255, 255, 128], fillColorSpace='rgb255',
	                                 opacity=1, depth=-2.0,
	                                 interpolate=True)
	triangle_left = visual.ShapeStim(win=window, name='triangle_left', units='pix',
	                                 vertices=[[0, arrow_s], [arrow_s / 2, -arrow_s], [0, -arrow_s / 2],
	                                           [-arrow_s / 2, -arrow_s]],
	                                 ori=180, pos=position[3],
	                                 lineWidth=1, lineColor=[255, 255, 128], lineColorSpace='rgb255',
	                                 fillColor=[255, 255, 128], fillColorSpace='rgb255',
	                                 opacity=1, depth=-2.0,
	                                 interpolate=True)
	rect_center = visual.ShapeStim(win=window, name='rect_center', units='pix',
	                               vertices=[[rect_s, rect_s], [rect_s, -rect_s], [-rect_s, -rect_s],
	                                         [-rect_s, rect_s]],
	                               ori=0, pos=[0, 0],
	                               lineWidth=1, lineColor=[255, 255, 128], lineColorSpace='rgb255',
	                               fillColor=[255, 255, 128], fillColorSpace='rgb255',
	                               opacity=1, depth=-2.0,
	                               interpolate=True)
	rect_center_eyes = visual.ShapeStim(win=window, name='rect_center_eyes', units='pix',
	                                    vertices=[[rect_s, rect_s], [rect_s, -rect_s], [-rect_s, -rect_s],
	                                              [-rect_s, rect_s]],
	                                    ori=0, pos=[0, 0],
	                                    lineWidth=1, lineColor=[216, 219, 220], lineColorSpace='rgb255',
	                                    fillColor=[216, 219, 220], fillColorSpace='rgb255',
	                                    opacity=1, depth=-2.0,
	                                    interpolate=True)


# flash stimulus change
def flash_change(flash):
	# global flash_up
	# global flash_right
	colors_tmp = flash.colors
	flash.setColors(-colors_tmp)


def commandPredLine(win):
	global lineUP, lineRIGHT, lineDOWN, lineLEFT

	lineUP = visual.Line(win=win, units="pix", lineColor='green')
	lineRIGHT = visual.Line(win=win, units="pix", lineColor='green')
	lineDOWN = visual.Line(win=win, units="pix", lineColor='green')
	lineLEFT = visual.Line(win=win, units="pix", lineColor='green')
	# lineSTOP = visual.Line(win=win, units="pix", lineColor='blue')

	position = set_checkerboards_position(win)

	lineUP.lineWidth = 15
	lineRIGHT.lineWidth = 15
	lineDOWN.lineWidth = 15
	lineLEFT.lineWidth = 15
	# lineSTOP.lineWidth = 30

	lineLEFT.start = [position[0][0] - 50, position[0][1] - 100]
	lineLEFT.end = [position[0][0] - 50 + 100, position[0][1] - 100]

	lineRIGHT.start = [position[1][0] - 100, position[1][1] + 50]
	lineRIGHT.end = [position[1][0] - 100, position[1][1] - 50]

	lineDOWN.start = [position[2][0] + 50, position[2][1] + 100]
	lineDOWN.end = [position[2][0] + 50 - 100, position[2][1] + 100]

	lineUP.end = [position[3][0] + 100, position[3][1] - 50]
	lineUP.start = [position[3][0] + 100, position[3][1] + 50]


# *********************************************************************************************************************
# ************************************ SCREEN session SSVEP presentation ************************************************
# *********************************************************************************************************************


def SSVEP_screen_session(board, startPresentation, boardApiCallEvents, _shutdownEvent, currentClassBuffer, target_dur,
                         frames_ch, mode):
	while not _shutdownEvent.is_set():
		startPresentation.wait(1)
		# -------------------------- START PRESENTATION --------------------------------------------
		# ------------------------------------------------------------------------------------------
		if startPresentation.is_set():
			if not board.isConnected():
				printWarning('Could not start training without connected Board.')
				startPresentation.clear()
				continue
			try:
				logging.console.setLevel(logging.WARNING)  # this outputs to the screen, not a file

				endExpNow = False  # flag for 'escape' or other condition => quit the exp

				# Setup the Window
				win = visual.Window(size=(1536, 864), fullscr=True, screen=0, allowGUI=False, allowStencil=False,
				                    monitor=u'testMonitor', color=[-1, -1, -1], colorSpace='rgb',
				                    blendMode='avg', useFBO=True,
				                    units='pix')

				# Global event key (with modifier) to quit the experiment ("shutdown key").

				win.setRecordFrameIntervals(True)
				win._refreshThreshold = 1 / 60.0 + 0.004  # i've got 60Hz monitor and want to allow 4ms tolerance

				# store frame rate of monitor
				frameRate = win.getActualFrameRate()
				if frameRate != None:
					frameDur = 1.0 / round(frameRate)
				else:
					frameDur = 1.0 / 60.0  # couldn't get a reliable measure so guess

				# Initialize all flash components
				init_experimentClock = core.Clock()

				ch_p = set_checkerboards_position(win)  # set the checkerboards and arrows positions
				arrow_p = set_arrows_position(ch_p)

				flash_init(win, ch_p, checker_s, checker_num, checker_num,
				           mode)  # Initialize the checkerboards in specific positions
				arrow_init(win, arrow_p)  # Initialize the arrows and central rectangle in specific positions

				# construct a list of the arrows-targets, we will use it later
				# Index in list: 0 = center, 1 = left, 2 = right, 3 = down, 4 = forward
				target_list = []
				target_list.append(rect_center)
				target_list.append(triangle_up)
				target_list.append(triangle_right)
				target_list.append(triangle_down)
				target_list.append(triangle_left)

				# Initialize components for Routine "show_grey_monitor"
				show_grey_monitorClock = core.Clock()
				instruct_text = visual.TextStim(win=win, ori=0, name='instruct_text',
				                                text='Press <Space> to continue', font='Arial',
				                                units='pix', pos=[0, 0], height=50, wrapWidth=1000,
				                                color=[255, 255, 128], colorSpace='rgb255', opacity=1,
				                                depth=0.0)

				# Initialize components for Routine "flash_checkerboard"
				flash_checkerboardClock = core.Clock()

				# Create some handy timers
				globalClock = core.Clock()  # to track the time since experiment started
				routineTimer = core.CountdownTimer()  # to track time remaining of each (non-slip) routine

				# #------Prepare to start Routine "show_grey_monitor"-------
				t = 0
				show_grey_monitorClock.reset()  # clock
				frameN = -1
				# update component parameters for each repeat
				key_start = event.BuilderKeyResponse()  # create an object of type KeyResponse
				key_start.status = NOT_STARTED
				# keep track of which components have finished
				show_grey_monitorComponents = []
				show_grey_monitorComponents.append(instruct_text)
				show_grey_monitorComponents.append(key_start)
				for thisComponent in show_grey_monitorComponents:
					if hasattr(thisComponent, 'status'):
						thisComponent.status = NOT_STARTED

				# -------Start Routine "show_grey_monitor"-------
				continueRoutine = True
				while continueRoutine:
					# get current time
					t = show_grey_monitorClock.getTime()
					frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
					# update/draw components on each frame

					# *instruct_text* updates
					if t >= 0.0 and instruct_text.status == NOT_STARTED:
						# keep track of start time/frame for later
						instruct_text.tStart = t  # underestimates by a little under one frame
						instruct_text.frameNStart = frameN  # exact frame index
						instruct_text.setAutoDraw(True)

					# *key_start* updates
					if t >= 0.0 and key_start.status == NOT_STARTED:
						# keep track of start time/frame for later
						key_start.tStart = t  # underestimates by a little under one frame
						key_start.frameNStart = frameN  # exact frame index
						key_start.status = STARTED
						# keyboard checking is just starting
						event.clearEvents(eventType='keyboard')
					if key_start.status == STARTED:
						theseKeys = event.getKeys(keyList=['space'])
						# check for quit:
						if "escape" in theseKeys:
							endExpNow = True
						if len(theseKeys) > 0:  # at least one key was pressed
							boardApiCallEvents["startStreaming"].set()
							# a response ends the routine
							continueRoutine = False

					# check if all components have finished
					if not continueRoutine:  # a component has requested a forced-end of Routine
						break
					continueRoutine = False  # will revert to True if at least one component still running
					for thisComponent in show_grey_monitorComponents:
						if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
							continueRoutine = True
							break  # at least one component has not yet finished

					# check for quit (the Esc key)
					if endExpNow or event.getKeys(keyList=["escape"]):
						# boardApiCallEvents["stopStreaming"].set()
						# startPresentation.clear()
						# win.close()
						raise psychopyWindowTermination('1st')
					# return

					# refresh the screen
					if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
						win.flip()

				# -------Ending Routine "show_grey_monitor"-------
				for thisComponent in show_grey_monitorComponents:
					if hasattr(thisComponent, "setAutoDraw"):
						thisComponent.setAutoDraw(False)
				# the Routine "show_grey_monitor" was not non-slip safe, so reset the non-slip timer
				routineTimer.reset()

				# create shuffled list of the targets
				
				shuffled_targets = cnst.shuffled_targets

				# ------Prepare to start Routine "flash_checkerboard"-------

				frameN = -1

				f_change = [0 for i in range(4)]
				pattern_state = [1 for j in range(4)]

				for target_ind in shuffled_targets:

					thisTarget = target_list[target_ind]

					t = 0
					flash_checkerboardClock.reset()  # clock

					# update component parameters for each repeat
					# flash begin routine

					end_fl = event.BuilderKeyResponse()  # create an object of type KeyResponse
					end_fl.status = NOT_STARTED
					# keep track of which components have finished
					flash_checkerboardComponents = []
					flash_checkerboardComponents.append(end_fl)
					flash_checkerboardComponents.append(thisTarget)

					for thisComponent in flash_checkerboardComponents:
						if hasattr(thisComponent, 'status'):
							thisComponent.status = NOT_STARTED

					# -------Start Routine "flash_checkerboard"-------
					continueRoutine = True
					t = flash_checkerboardClock.getTime()

					while continueRoutine and t < (
							0.0 + (target_dur - win.monitorFramePeriod * 0.75)) and startPresentation.is_set():
						# get current time
						t = flash_checkerboardClock.getTime()
						# t1 = flash_checkerboardClock.getTime()
						frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
						# update/draw components on each frame
						# flash each frame
						# .................................................................................
						if frameN >= f_change[0]:
							# flash_change(flash_left)
							if pattern_state[0] == 1:
								f_change[0] += frames_ch[0][1]  # f_change +=frames_off
								pattern_state[0] = 0
							else:
								f_change[0] += frames_ch[0][0]  # f_change += frames_on
								pattern_state[0] = 1

						# ......................................................................................
						if frameN >= f_change[1]:
							# flash_change(flash_right)
							if pattern_state[1] == 1:
								f_change[1] += frames_ch[1][1]  # f_change +=frames_off
								pattern_state[1] = 0
							else:
								f_change[1] += frames_ch[1][0]  # f_change += frames_on
								pattern_state[1] = 1

						# .........................................................................................
						if frameN >= f_change[2]:
							# flash_change(flash_back)
							if pattern_state[2] == 1:
								f_change[2] += frames_ch[2][1]  # f_change +=frames_off
								pattern_state[2] = 0
							else:
								f_change[2] += frames_ch[2][0]  # f_change += frames_on
								pattern_state[2] = 1

						# ...........................................................................................
						if frameN >= f_change[3]:
							# flash_change(flash_forward)
							if pattern_state[3] == 1:
								f_change[3] += frames_ch[3][1]  # f_change +=frames_off
								pattern_state[3] = 0
							else:
								f_change[3] += frames_ch[3][0]  # f_change += frames_on
								pattern_state[3] = 1

						# ............................................................................................
						if pattern_state[0] == 1:
							flash_left_ON.draw()
						else:
							flash_left_OFF.draw()
						if pattern_state[1] == 1:
							flash_right_ON.draw()
						else:
							flash_right_OFF.draw()
						if pattern_state[2] == 1:
							flash_down_ON.draw()
						else:
							flash_down_OFF.draw()
						if pattern_state[3] == 1:
							flash_up_ON.draw()
						else:
							flash_up_OFF.draw()

						# *end_fl* updates
						if t >= 0.0 and end_fl.status == NOT_STARTED:
							# keep track of start time/frame for later
							end_fl.tStart = t  # underestimates by a little under one frame
							end_fl.frameNStart = frameN  # exact frame index
							end_fl.status = STARTED
							# keyboard checking is just starting
							event.clearEvents(eventType='keyboard')
						if end_fl.status == STARTED:
							theseKeys = event.getKeys()

							# check for quit:
							if "escape" in theseKeys:
								endExpNow = True
							if len(theseKeys) > 0:  # at least one key was pressed
								# a response ends the routine
								continueRoutine = False

						# *thisTarget* updates
						if t >= 0.0 and thisTarget.status == NOT_STARTED:

							# put the labels corresponding to each target
							if target_ind == 55:
								label = 0
							else:
								label = target_ind
							currentClassBuffer.put(label)

							# keep track of start time/frame for later
							thisTarget.tStart = t  # underestimates by a little under one frame
							thisTarget.frameNStart = frameN  # exact frame index
							thisTarget.setAutoDraw(True)

						if thisTarget.status == STARTED and t >= (
								0.0 + (1.0 - win.monitorFramePeriod * 0.75)):  # most of one frame period left
							thisTarget.setAutoDraw(False)

						# check if all components have finished
						if not continueRoutine:  # a component has requested a forced-end of Routine
							break
						continueRoutine = False  # will revert to True if at least one component still running
						for thisComponent in flash_checkerboardComponents:
							if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
								continueRoutine = True
								break  # at least one component has not yet finished

						# check for quit (the Esc key)
						if endExpNow or event.getKeys(keyList=["escape"]):
							boardApiCallEvents["stopStreaming"].set()
							# startPresentation.clear()
							# win.close()
							raise psychopyWindowTermination('2nd')
						# return

						# t2 = flash_checkerboardClock.getTime()
						# print(t2-t1)

						# refresh the screen
						if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
							win.flip()

					# -------Ending Routine "flash_checkerboard"-------
					for thisComponent in flash_checkerboardComponents:
						if hasattr(thisComponent, "setAutoDraw"):
							thisComponent.setAutoDraw(False)
				# print(t)
				# the Routine "flash_checkerboard" was not non-slip safe, so reset the non-slip timer
				routineTimer.reset()

				# -------------------------------------------------------------------------------------- #

				# stop reading
				boardApiCallEvents["stopStreaming"].set()

				# -------------------------------------------------------------------------------------- #
				# pylab.plot(win.frameIntervals)
				startPresentation.clear()
				win.close()

				# pylab.show()
				# raise psychopyWindowTermination('final')
				return
			except psychopyWindowTermination as term:
				startPresentation.clear()
				win.close()
				# core.quit()
				printInfo('Training Window closing...')
				return


# *********************************************************************************************************************
# ************************************ Online session SSVEP presentation ************************************************
# *********************************************************************************************************************

# ********* DO NOT FORGET REMOVE return
def SSVEP_online_SCREEN_session(board, startPresentation, boardApiCallEvents, _isReading, _shutdownEvent,
                                currentClassBuffer, groundTruthBuffer, frames_ch, _streaming,
                                releaseData, emergency_arduino, emergency_buffer, ip_cam_, mode, commandPred):
	# print the id of the process
	# info("SSVEP_experiment")
	# mouse = event.Mouse() # CHECK
	printInfo('Starting online_SSVEP process')
	# wait until acquisition and reading start
	while not _shutdownEvent.is_set():
		startPresentation.wait(1)
		# -------------------------- START PRESENTATION --------------------------------------------
		# ------------------------------------------------------------------------------------------
		if startPresentation.is_set():
			if not board.isConnected():
				printWarning('Could not start training without connected Board.')
				startPresentation.clear()
				continue
			printInfo('Starting targets')
			logging.console.setLevel(logging.WARNING)  # this outputs to the screen, not a file

			endExpNow = False  # flag for 'escape' or other condition => quit the exp

			vcap = cv2.VideoCapture(ip_cam_)  # ("http://139.91.190.222:8080/video")#
			# ("http://139.91.190.182:8080/video")
			# ("http://139.91.190.209  :8080/video")  #for Robot wifi
			if vcap is None or not vcap.isOpened():

				vcap.release()
				cv2.destroyAllWindows()
				# _isReading.clear()
				startPresentation.clear()
				while not commandPred.empty():
					commandPred.get_nowait()

				return
			printHeader("Let's create the window")
			# Setup the Window
			win = visual.Window(size=(1536, 864), fullscr=True, screen=0, allowGUI=False, allowStencil=False,
			                    monitor=u'testMonitor', color=[-1, -1, -1], colorSpace='rgb',
			                    blendMode='avg', useFBO=True,
			                    units='pix')

			win.setRecordFrameIntervals(True)
			win._refreshThreshold = 1 / 60.0 + 0.004  # i've got 60Hz monitor and want to allow 4ms tolerance

			# store frame rate of monitor if we can measure it successfully
			frameRate = win.getActualFrameRate()
			if frameRate != None:
				frameDur = 1.0 / round(frameRate)
			else:
				frameDur = 1.0 / 60.0  # couldn't get a reliable measure so guess

			# Initialize all flash components
			init_experimentClock = core.Clock()

			ch_p = set_checkerboards_position(win)  # set the checkerboards and arrows positions
			arrow_p = set_arrows_position(ch_p)

			# direction arrows
			img_lf = visual.ImageStim(win=win, image=cnst.mediaPath + "left_a.png", units="pix", opacity=0.75, ori=360,
			                          pos=arrow_p[0], color=[0, 0, 0], colorSpace='rgb255')
			img_ri = visual.ImageStim(win=win, image=cnst.mediaPath + "right_a.png", units="pix", opacity=0.75, ori=360,
			                          pos=arrow_p[1], color=[0, 0, 0], colorSpace='rgb255')
			img_up = visual.ImageStim(win=win, image=cnst.mediaPath + "up_a.png", units="pix", opacity=0.75, ori=180,
			                          pos=arrow_p[2], color=[0, 0, 0], colorSpace='rgb255')
			img_do = visual.ImageStim(win=win, image=cnst.mediaPath + "up_a.png", units="pix", opacity=0.75, ori=0,
			                          pos=arrow_p[3], color=[0, 0, 0], colorSpace='rgb255')

			flash_init(win, ch_p, checker_s, checker_num, checker_num,
			           mode)  # Initialize the checkerboards in specific positions

			# Initialize components for Routine "show_grey_monitor"
			show_grey_monitorClock = core.Clock()
			instruct_text = visual.TextStim(win=win, ori=0, name='instruct_text',
			                                text='Press <Space> to continue', font='Arial',
			                                units='pix', pos=[0, 0], height=50, wrapWidth=1000,
			                                color=[255, 255, 128], colorSpace='rgb255', opacity=1,
			                                depth=0.0)

			# Initialize components for Routine "flash_checkerboard"
			flash_checkerboardClock = core.Clock()

			# Create some handy timers
			globalClock = core.Clock()  # to track the time since experiment started
			routineTimer = core.CountdownTimer()  # to track time remaining of each (non-slip) routine

			# ------Prepare to start Routine "show_grey_monitor"-------
			t = 0
			show_grey_monitorClock.reset()  # clock
			frameN = -1
			# update component parameters for each repeat
			key_start = event.BuilderKeyResponse()  # create an object of type KeyResponse
			key_start.status = NOT_STARTED
			# keep track of which components have finished
			show_grey_monitorComponents = []
			show_grey_monitorComponents.append(instruct_text)
			show_grey_monitorComponents.append(key_start)
			for thisComponent in show_grey_monitorComponents:
				if hasattr(thisComponent, 'status'):
					thisComponent.status = NOT_STARTED

			# -------Start Routine "show_grey_monitor"-------
			continueRoutine = True
			while continueRoutine:
				# get current time
				t = show_grey_monitorClock.getTime()
				frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
				# update/draw components on each frame

				# *instruct_text* updates
				if t >= 0.0 and instruct_text.status == NOT_STARTED:
					# keep track of start time/frame for later
					instruct_text.tStart = t  # underestimates by a little under one frame
					instruct_text.frameNStart = frameN  # exact frame index
					instruct_text.setAutoDraw(True)

				# *key_start* updates
				if t >= 0.0 and key_start.status == NOT_STARTED:
					# keep track of start time/frame for later
					key_start.tStart = t  # underestimates by a little under one frame
					key_start.frameNStart = frameN  # exact frame index
					key_start.status = STARTED
					# keyboard checking is just starting
					event.clearEvents(eventType='keyboard')
				if key_start.status == STARTED:
					theseKeys = event.getKeys(keyList=['space'])
					# check for quit:
					if "escape" in theseKeys:
						endExpNow = True
					if len(theseKeys) > 0:  # at least one key was pressed
						boardApiCallEvents["startStreaming"].set()
						# a response ends the routine
						continueRoutine = False

				# check if all components have finished
				if not continueRoutine:  # a component has requested a forced-end of Routine
					break
				continueRoutine = False  # will revert to True if at least one component still running
				for thisComponent in show_grey_monitorComponents:
					if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
						continueRoutine = True
						break  # at least one component has not yet finished

				# check for quit (the Esc key)
				if endExpNow or event.getKeys(keyList=["escape"]):
					boardApiCallEvents["stopStreaming"].set()
					# _isReading.clear()
					startPresentation.clear()
					while not commandPred.empty():
						commandPred.get_nowait()
					# pylab.plot(win.frameIntervals)
					win.close()
					# pylab.show()
					return

				# refresh the screen
				if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
					win.flip()

			# -------Ending Routine "show_grey_monitor"-------
			for thisComponent in show_grey_monitorComponents:
				if hasattr(thisComponent, "setAutoDraw"):
					thisComponent.setAutoDraw(False)
			# the Routine "show_grey_monitor" was not non-slip safe, so reset the non-slip timer
			routineTimer.reset()

			# releaseData.set() # store and process data

			# ------Prepare to start Routine "flash_checkerboard"-------
			t = 0
			flash_checkerboardClock.reset()  # clock
			frameN = -1
			# update component parameters for each repeat
			# flash begin routine
			f_change = [0 for i in range(4)]
			pattern_state = [1 for j in range(4)]

			end_fl = event.BuilderKeyResponse()  # create an object of type KeyResponse
			end_fl.status = NOT_STARTED
			# keep track of which components have finished
			flash_checkerboardComponents = []
			flash_checkerboardComponents.append(end_fl)

			for thisComponent in flash_checkerboardComponents:
				if hasattr(thisComponent, 'status'):
					thisComponent.status = NOT_STARTED

			# draw a green line under the predicted target
			commandPredLine(win)

			# -------Start Routine "flash_checkerboard"-------
			try:

				ret, img = vcap.read()
				imgRows, imgColumns, imgColors = img.shape
				# transform the output of camera read, in order to create a visual stimulus from an image
				pic = Image.frombytes("RGB", (imgColumns, imgRows), img.tostring(), "raw", "BGR", 0, 1)
				# print pi.size
				myStim = visual.ImageStim(win, pic, pos=[0, 0], size=[imgColumns, imgRows], opacity=1.0, units='pix')
				myStim.setAutoDraw(True)

				threadVIDEO = CameraRead(vcap, img)
				threadVIDEO.start()

				continueRoutine = True
				t = flash_checkerboardClock.getTime()
				while continueRoutine and startPresentation.is_set():
					# get current time
					t = flash_checkerboardClock.getTime()
					frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
					# update/draw components on each frame
					# flash each frame
					# .................................................................................
					if frameN >= f_change[0]:
						# flash_change(flash_up)
						if pattern_state[0] == 1:
							f_change[0] += frames_ch[0][1]  # f_change +=frames_off
							pattern_state[0] = 0
						else:
							f_change[0] += frames_ch[0][0]  # f_change += frames_on
							pattern_state[0] = 1

					# ......................................................................................
					if frameN >= f_change[1]:
						# flash_change(flash_right)
						if pattern_state[1] == 1:
							f_change[1] += frames_ch[1][1]  # f_change +=frames_off
							pattern_state[1] = 0
						else:
							f_change[1] += frames_ch[1][0]  # f_change += frames_on
							pattern_state[1] = 1

					# .........................................................................................
					if frameN >= f_change[2]:
						# flash_change(flash_down)
						if pattern_state[2] == 1:
							f_change[2] += frames_ch[2][1]  # f_change +=frames_off
							pattern_state[2] = 0
						else:
							f_change[2] += frames_ch[2][0]  # f_change += frames_on
							pattern_state[2] = 1

					# ...........................................................................................
					if frameN >= f_change[3]:
						# flash_change(flash_left)
						if pattern_state[3] == 1:
							f_change[3] += frames_ch[3][1]  # f_change +=frames_off
							pattern_state[3] = 0
						else:
							f_change[3] += frames_ch[3][0]  # f_change += frames_on
							pattern_state[3] = 1

					# ............................................................................................
					if pattern_state[0] == 1:
						flash_left_ON.draw()
					else:
						flash_left_OFF.draw()
					if pattern_state[1] == 1:
						flash_right_ON.draw()
					else:
						flash_right_OFF.draw()
					if pattern_state[2] == 1:
						flash_down_ON.draw()
					else:
						flash_down_OFF.draw()
					if pattern_state[3] == 1:
						flash_up_ON.draw()
					else:
						flash_up_OFF.draw()

					img_lf.draw()
					img_ri.draw()
					img_up.draw()
					img_do.draw()

					#########################################################################################
					#########################################################################################
					# show predicted command
					if not commandPred.empty():
						cmd = commandPred.get_nowait()
						# print(cmd)
						if cmd == 1:
							lineLEFT.draw()
						elif cmd == 2:
							lineRIGHT.draw()
						elif cmd == 3:
							lineDOWN.draw()
						elif cmd == 4:
							lineUP.draw()
					# elif cmd == 55:
					# 	lineSTOP.draw()

					#########################################################################################
					#########################################################################################

					# Show IP camera image
					imgN = threadVIDEO.ImgT
					if not np.array_equal(imgN, img):
						pi = Image.frombytes("RGB", (imgColumns, imgRows), threadVIDEO.ImgT.tostring(), "raw", "BGR", 0,
						                     1)
						myStim.setImage(pi)
					img = imgN

					# *end_fl* updates
					if t >= 0.0 and end_fl.status == NOT_STARTED:
						currentClassBuffer.put_nowait(300)
						groundTruthBuffer.put(cnst.unknownClass)

						# keep track of start time/frame for later
						end_fl.tStart = t  # underestimates by a little under one frame
						end_fl.frameNStart = frameN  # exact frame index
						end_fl.status = STARTED
						# keyboard checking is just starting
						event.clearEvents(eventType='keyboard')
					if end_fl.status == STARTED:
						theseKeys = event.getKeys()
						# print(theseKeys)
						# check for quit:
						if cnst.emergencyKeyboardCommands[cnst._keyboardKey_EXIT_PRESENTATION] in theseKeys:
							endExpNow = True

							currentClassBuffer.put_nowait(300)
						elif cnst.emergencyKeyboardCommands[cnst._keyboardKey_FORWARD] in theseKeys:
							emergency_arduino.set()
							emergency_buffer.put("f")
							currentClassBuffer.put_nowait(300)
							print("EMERGENCY SET FORWARD")
						elif cnst.emergencyKeyboardCommands[cnst._keyboardKey_RIGHT] in theseKeys:
							emergency_arduino.set()
							emergency_buffer.put("r")
							currentClassBuffer.put_nowait(300)
							print("EMERGENCY SET RIGHT")
						elif cnst.emergencyKeyboardCommands[cnst._keyboardKey_LEFT] in theseKeys:
							emergency_arduino.set()
							emergency_buffer.put("l")
							currentClassBuffer.put_nowait(300)
							print("EMERGENCY SET LEFT")
						elif cnst.emergencyKeyboardCommands[cnst._keyboardKey_BACK] in theseKeys:
							emergency_arduino.set()
							emergency_buffer.put("b")
							currentClassBuffer.put_nowait(300)
							print("EMERGENCY SET BACK")
						elif cnst.emergencyKeyboardCommands[cnst._keyboardKey_STOP] in theseKeys:
							emergency_arduino.set()
							emergency_buffer.put("s")
							currentClassBuffer.put_nowait(300)
							print("EMERGENCY SET STOP")
						elif cnst.emergencyKeyboardCommands[cnst._keyboardKey_RETURN_EEG] in theseKeys:
							emergency_arduino.clear()
							emergency_buffer.put("s")
							currentClassBuffer.put_nowait(300)
							print("RETURN EEG")
						# add the commands for the ground truth
						elif cnst.groundTruthKeyboardCommands[cnst._keyboardKey_FORWARD] in theseKeys:
							groundTruthBuffer.put(
								cnst.groundTruthKeyboardCommands_class4Switcher[cnst._keyboardKey_FORWARD])
							currentClassBuffer.put_nowait(300)
							print("GROUND TRUTH SET FORWARD")
						elif cnst.groundTruthKeyboardCommands[cnst._keyboardKey_RIGHT] in theseKeys:
							groundTruthBuffer.put(
								cnst.groundTruthKeyboardCommands_class4Switcher[cnst._keyboardKey_RIGHT])
							currentClassBuffer.put_nowait(300)
							print("GROUND TRUTH SET RIGHT")
						elif cnst.groundTruthKeyboardCommands[cnst._keyboardKey_LEFT] in theseKeys:
							groundTruthBuffer.put(
								cnst.groundTruthKeyboardCommands_class4Switcher[cnst._keyboardKey_LEFT])
							currentClassBuffer.put_nowait(300)
							print("GROUND TRUTH SET LEFT")
						elif cnst.groundTruthKeyboardCommands[cnst._keyboardKey_BACK] in theseKeys:
							groundTruthBuffer.put(
								cnst.groundTruthKeyboardCommands_class4Switcher[cnst._keyboardKey_BACK])
							currentClassBuffer.put_nowait(300)
							print("GROUND TRUTH SET BACK")
						elif cnst.groundTruthKeyboardCommands[cnst._keyboardKey_STOP] in theseKeys:
							groundTruthBuffer.put(
								cnst.groundTruthKeyboardCommands_class4Switcher[cnst._keyboardKey_STOP])
							currentClassBuffer.put_nowait(300)
							print("GROUND TRUTH SET STOP")

					# check if all components have finished
					if not continueRoutine:  # a component has requested a forced-end of Routine
						break
					continueRoutine = False  # will revert to True if at least one component still running
					for thisComponent in flash_checkerboardComponents:
						if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
							continueRoutine = True
							break  # at least one component has not yet finished

					# check for quit (the Esc key)
					# if endExpNow or event.getKeys(keyList=["escape"]) or not _streaming.is_set():
					if endExpNow or event.getKeys(keyList=["escape"]):
						vcap.release()
						cv2.destroyAllWindows()
						boardApiCallEvents["stopStreaming"].set()
						# _isReading.clear()
						startPresentation.clear()
						while not commandPred.empty():
							commandPred.get_nowait()
						# pylab.plot(win.frameIntervals)
						win.close()
						# pylab.show()
						# break
						return
					# core.quit()

					# refresh the screen
					if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
						win.flip()

				# -------Ending Routine "flash_checkerboard"-------
				for thisComponent in flash_checkerboardComponents:
					if hasattr(thisComponent, "setAutoDraw"):
						thisComponent.setAutoDraw(False)

				# the Routine "flash_checkerboard" was not non-slip safe, so reset the non-slip timer
				routineTimer.reset()

				# -------------------------------------------------------------------------------------- #
				vcap.release()
				cv2.destroyAllWindows()

				# stop reading
				boardApiCallEvents["stopStreaming"].set()
				# _isReading.clear()
				startPresentation.clear()

				# -------------------------------------------------------------------------------------- #
				# pylab.plot(win.frameIntervals)

				win.close()

				# pylab.show()

				return
			except:
				# the Routine "flash_checkerboard" was not non-slip safe, so reset the non-slip timer
				routineTimer.reset()

				# -------------------------------------------------------------------------------------- #
				vcap.release()
				cv2.destroyAllWindows()
				print("EXCEPTION PRESENTATION")
				# stop reading
				boardApiCallEvents["stopStreaming"].set()
				# _isReading.clear()
				startPresentation.clear()
				while not commandPred.empty():
					commandPred.get_nowait()

				# -------------------------------------------------------------------------------------- #
				# pylab.plot(win.frameIntervals)

				win.close()

				# pylab.show()

				return

	print("presentation out")

# -------------------------- ONLINE MUSEUM --------------------------------------------
# ------------------------------------------------------------------------------------------
