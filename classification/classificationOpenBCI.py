from distutils import command
from fileinput import filename
import os
from tkinter import filedialog, Tk
from tkinter.filedialog import asksaveasfilename

import h5py
import joblib
from multiprocessing import Event
import numpy as np
from classification import calculate_cca_corrs_all_segments
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix
from utils.constants import Constants as cnst, getSessionFilename
from utils.coloringPrint import printError

root = Tk()
root.withdraw()
# parameters
# ................................................................

frames_ch = cnst.frames_ch
harmonics_num = cnst.harmonics_num

_dataInFile = Event()  # event that is set if we read data from file, 
# not set if we procced to the proccessing code directly after presentation
_dataInFile.set()


# ................................................................
# ................................................................

# functions 
# classifier's training
def training(segment_buffer, chan_ind, fs, frames_ch, lowcut, highcut, harmonics_num,
             _dataInFile, classifierName):  # segment buffer is proc_buffer, with each get() we have one segment

	r, ground_truth = calculate_cca_corrs_all_segments(segment_buffer, chan_ind, fs, frames_ch, lowcut, highcut,
	                                                   harmonics_num, _dataInFile)

	# call the classifier
	clf_LDA = LinearDiscriminantAnalysis()

	# training
	clf_LDA.fit(r, np.ravel(ground_truth))  # np.ravel returns a contiguous flattened array

	joblib.dump(clf_LDA, classifierName)


def calculateAccuracy(segment_buffer, chan_ind, fs, frames_ch, lowcut, highcut, harmonics_num, _dataInFile,
                      classifierFileName):
	r, ground_truth = calculate_cca_corrs_all_segments(segment_buffer, chan_ind, fs, frames_ch, lowcut, highcut,
	                                                   harmonics_num, _dataInFile)

	# load classifier
	clf_LDA = joblib.load(classifierFileName)

	# predict
	predicted_labels_LDA = clf_LDA.predict(r)

	# arr_LDA = np.concatenate((predicted_labels_LDA.reshape(predicted_labels_LDA.shape[0],1),ground_truth),axis=1)
	acc_LDA = clf_LDA.score(r, np.ravel(ground_truth))  # np.ravel returns a contiguous flattened array

	return acc_LDA, predicted_labels_LDA, ground_truth


# ................................................................
# ................................................................
def classify(fileNames, enabledChannels, lowcut, highcut, fs, saveClassifier,subject=None):
	electroType = None
	allWinSignals= None
	for fileName in fileNames:
		with h5py.File(fileName, 'r') as fl:
			# get dataset's windowed data as winSignal
			winSignal = fl['packages'][:,:,0:9]
			# get dataset's streaming electrode's settings
			dtElectroType = fl['StreamSettings'][7,1].decode('UTF-8').split('.')[1]
			# check whether there is existing electrode type or not. If not init it with the first dataset's settings.
			# In order to classify, the electrode's type should be the same for each one of the streaming datasets
			if not electroType:
				electroType = dtElectroType
			elif electroType != dtElectroType:
				printError('Not the same electrodes in every session. No classifier created!')
				return
			
			# add the dataset's windowed signal data into the allWinSignals var
			if allWinSignals is None:
				allWinSignals = winSignal
			else:
				allWinSignals = np.concatenate((allWinSignals, winSignal))
	
	# split the data to train and test
	X_train, X_test = train_test_split(allWinSignals, test_size=0.35, random_state=42)
	isExist = os.path.exists(cnst.classifiersDirectory)

	if not isExist:
		# Create a new directory because it does not exist
		os.makedirs(cnst.classifiersDirectory)
	if saveClassifier:
		classifierFileName = asksaveasfilename(title="Choose a name for the classifier",
		                                       initialfile=getSessionFilename(classification=True),
		                                       defaultextension=".sav",
		                                       filetypes=[('SAV', '.sav')],
		                                       initialdir=cnst.classifiersDirectory,
		                                       confirmoverwrite=True)
	else:
		classifierFileName = 'rndName'

	if not classifierFileName:
		return
	training(X_train, enabledChannels, fs, frames_ch, lowcut, highcut, harmonics_num, _dataInFile,
	         classifierFileName)
	acc_LDA, predicted_labels_LDA, ground_truth = calculateAccuracy(X_test, enabledChannels, fs, frames_ch,
	                                                                lowcut,
	                                                                highcut, harmonics_num,
	                                                                _dataInFile, classifierFileName)

	print("")
	print("************ LDA accuracy is ************** : " + str(acc_LDA))

	
	# calculate total samples hit and accuracy for each one of the target classes
	gtArray = np.concatenate( ground_truth, axis=0 ).astype(int)
	prArray = predicted_labels_LDA.astype(int)
	commandsResult = targetsAccuracy(gtArray, prArray)

	# calculate hits
	stop = commandsResult['stop']['total']
	forward = commandsResult['forward']['total']
	back = commandsResult['back']['total']
	right = commandsResult['right']['total']
	left = commandsResult['left']['total']
	stopHit = commandsResult['stop']['hit']
	forwardHit = commandsResult['forward']['hit']
	backHit = commandsResult['back']['hit']
	rightHit = commandsResult['right']['hit']
	leftHit = commandsResult['left']['hit']
	stopAccuracy = commandsResult['stop']['accuracy']
	forwardAccuracy = commandsResult['forward']['accuracy']
	backAccuracy = commandsResult['back']['accuracy']
	rightAccuracy = commandsResult['right']['accuracy']
	leftAccuracy = commandsResult['left']['accuracy']
	print("In total: " + str(stop + forward + right + back + left) + " samples")
	print("Hit Stop: " + str(stopAccuracy) + " , " + str(stopHit) + "/" + str(stop))
	print("Hit Forward: " + str(forwardAccuracy) + " , " + str(forwardHit) + "/" + str(forward))
	print("Hit Right: " + str(rightAccuracy) + " , " + str(rightHit) + "/" + str(right))
	print("Hit Back: " + str(backAccuracy) + " , " + str(backHit) + "/" + str(back))
	print("Hit Left: " + str(leftAccuracy) + " , " + str(leftHit) + "/" + str(left))
	print("[Stop, Left, Right, Back, Forward]")
	print(confusion_matrix(ground_truth, predicted_labels_LDA, labels=[0, 1, 2, 3, 4]))
	if not saveClassifier:
		os.remove(classifierFileName)

	classificationResults = {
		'Subject': subject,
		'Electrodes': electroType,
		'channels': [x+1 for x in enabledChannels],
		'LDA Accuracy': str(acc_LDA),
		'Total samples': str(stop + forward + right + back + left),
		'Stop samples': str(stopHit) + " // " + str(stop),
		'Stop accuracy': str(stopAccuracy),
		'Forward samples': str(forwardHit) + " // " + str(forward),
		'Forward accuracy': str(forwardAccuracy),
		'Right samples': str(rightHit) + " // " + str(right),
		'Right accuracy': str(rightAccuracy),
		'Back samples': str(backHit) + " // " + str(back),
		'Back accuracy': str(backAccuracy),
		'Left samples': str(leftHit) + " // " + str(left),
		'Left accuracy': str(leftAccuracy)
	}	
	return classificationResults
		
		
def targetsAccuracy(ground_truth, predicted_labels_LDA):
	commandsResult = {}
	for cmd, class_ in cnst.targetClassCommands.items():
		gtIndexes = np.where(ground_truth == class_)[0]
		predIndexes = np.where(predicted_labels_LDA == class_)[0]
		commandsResult[cmd] = {
			'hit': len(np.intersect1d(gtIndexes,predIndexes)),
			'total': len(gtIndexes),
			'accuracy': 100 * len(np.intersect1d(gtIndexes,predIndexes)) / len(gtIndexes) 
		}
	return commandsResult
