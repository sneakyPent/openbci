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

root = Tk()
root.withdraw()
# parameters
# ................................................................
chan_ind = [0, 1, 2, 3]

frames_ch = cnst.frames_ch
lowcut = 4
highcut = 40
harmonics_num = 2
fs = 250

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


def calculateAccuracy(segment_buffer, chan_ind, fs, frames_ch, lowcut, highcut, harmonics_num, _dataInFile):
	r, ground_truth = calculate_cca_corrs_all_segments(segment_buffer, chan_ind, fs, frames_ch, lowcut, highcut,
	                                                   harmonics_num, _dataInFile)

	# load classifier
	clf_LDA = joblib.load(cnst.classifierFilename)

	# predict
	predicted_labels_LDA = clf_LDA.predict(r)

	# arr_LDA = np.concatenate((predicted_labels_LDA.reshape(predicted_labels_LDA.shape[0],1),ground_truth),axis=1)
	acc_LDA = clf_LDA.score(r, np.ravel(ground_truth))  # np.ravel returns a contiguous flattened array

	return acc_LDA, predicted_labels_LDA, ground_truth


# ................................................................
# ................................................................
def classify(fileNames):
	if len(fileNames) != 4:
		print('Please choose exactly 4 training files!')
	else:
		file1 = fileNames[0]
		file2 = fileNames[1]
		file3 = fileNames[2]
		file4 = fileNames[3]

		# open the files
		with h5py.File(file1, 'r') as f1:
			with h5py.File(file2, 'r') as f2:
				with h5py.File(file3, 'r') as f3:
					with h5py.File(file4, 'r') as f4:

						dsignal_1 = f1['packages']
						dsignal_2 = f2['packages']
						dsignal_3 = f3['packages']
						dsignal_4 = f4['packages']

						# merge the different session data
						dset = np.concatenate((dsignal_1, dsignal_2, dsignal_3, dsignal_4))

						# split the data to train and test
						X_train, X_test = train_test_split(dset, test_size=0.35, random_state=42)
						isExist = os.path.exists(cnst.classifiersDirectory)

						if not isExist:
							# Create a new directory because it does not exist
							os.makedirs(cnst.classifiersDirectory)
						classifierFileName = asksaveasfilename(title="Choose a name for the classifier",
						                                       initialfile=getSessionFilename(classification=True),
						                                       defaultextension=".sav",
						                                       filetypes=[('SAV', '.sav')],
						                                       initialdir=cnst.classifiersDirectory,
						                                       confirmoverwrite=True)

						if not classifierFileName:
							return
						training(X_train, chan_ind, fs, frames_ch, lowcut, highcut, harmonics_num, _dataInFile,
						         classifierFileName)
						acc_LDA, predicted_labels_LDA, ground_truth = calculateAccuracy(X_test, chan_ind, fs, frames_ch,
						                                                                lowcut,
						                                                                highcut, harmonics_num,
						                                                                _dataInFile)

						print("")
						print("************ LDA accuracy is ************** : " + str(acc_LDA))

						stop = 0
						hitStop = 0
						forward = 0
						hitForward = 0
						right = 0
						hitRight = 0
						back = 0
						hitBack = 0
						left = 0
						hitLeft = 0

						i = 0

						while i < ground_truth.shape[0]:

							if ground_truth[i] == 0:
								stop = stop + 1
								if predicted_labels_LDA[i] == 0:
									hitStop = hitStop + 1
								i = i + 1

							elif ground_truth[i] == 4:
								forward = forward + 1
								if predicted_labels_LDA[i] == 4:
									hitForward = hitForward + 1
								i = i + 1

							elif ground_truth[i] == 2:
								right = right + 1
								if predicted_labels_LDA[i] == 2:
									hitRight = hitRight + 1
								i = i + 1

							elif ground_truth[i] == 3:
								back = back + 1
								if predicted_labels_LDA[i] == 3:
									hitBack = hitBack + 1
								i = i + 1

							elif ground_truth[i] == 1:
								left = left + 1
								if predicted_labels_LDA[i] == 1:
									hitLeft = hitLeft + 1
								i = i + 1

						# calculate hits
						print("In total: " + str(stop + forward + right + back + left) + " samples")
						print("Hit Stop: " + str(100 * hitStop / stop) + " , " + str(hitStop) + "/" + str(stop))
						print("Hit Forward: " + str(100 * hitForward / forward) + " , " + str(hitForward) + "/" + str(
							forward))
						print("Hit Right: " + str(100 * hitRight / right) + " , " + str(hitRight) + "/" + str(right))
						print("Hit Back: " + str(100 * hitBack / back) + " , " + str(hitBack) + "/" + str(back))
						print("Hit Left: " + str(100 * hitLeft / left) + " , " + str(hitLeft) + "/" + str(left))
						print("")
						print("[Stop, Left, Right, Back, Forward]")
						print(confusion_matrix(ground_truth, predicted_labels_LDA, labels=[0, 1, 2, 3, 4]))
