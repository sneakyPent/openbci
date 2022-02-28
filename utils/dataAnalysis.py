import ast
import datetime
import itertools
from operator import index
import os
import numpy
import sys

sys.path.append('..')
from cmath import log
from math import * 
import h5py
import numpy as np
from statistics import mean
from utils.constants import Constants as cnst, getShuffledTargetsLength
from classification.classificationOpenBCI import classify
from csv import DictWriter
from utils.coloringPrint import printError, printWarning

channel_1_Index = 0
channel_2_Index = 1
channel_3_Index = 2
channel_4_Index = 3
channel_5_Index = 4
channel_6_Index = 5
channel_7_Index = 6
channel_8_Index = 7
predictedClass_Index = 8
groundTruth_index = 9
timer_index = 10


lowcut = 4
highcut =40
samplingRate = cnst.SAMPLE_RATE_250
# The number of targets for testing session
ITR_numberOfTargets = 5
# The total number of classifications during the testing session.
ITR_Cn = 219
# The testing session duration in seconds
ITR_T = getShuffledTargetsLength() * cnst.targetDuration

def calcalate_ITR(N,P,Cn,T):
	if 1-P == 0:
		B = log(N,2) + P*log(P,2)
	else:
		B = log(N,2) + P*log(P,2) + ((1-P)*log(((1-P)/(N-1)),2))
	ITR = (60/T) * Cn * B
	return ITR
	
	
	

def getListOfFiles(dirName,drivenTime=False, classification=False, calcEveryClassCombination=False):
	# create a list of file and sub directories 
	# names in the given directory 
	listOfFile = os.listdir(dirName)
	allFiles = list()
	# Iterate over all the entries
	for entry in listOfFile:
		# Create full path
		# print(entry)
		fullPath = os.path.join(dirName, entry)
		# If entry is a directory then get the list of files in this directory 
		if os.path.isdir(fullPath):
			# check if the directory is numeric, in other words subject data
			if entry.isnumeric():
				# print(entry)
				getListOfFiles(fullPath,drivenTime, classification, calcEveryClassCombination)
			# check if the directory is wet results
			elif entry.lower() == 'wet':
				usedChannels = None 
				trainingFiles = []
				# get the first 4 files contain 'streaming' in their name, for the classification
				for trainingFile in os.listdir(fullPath):
					trainingFilePath = os.path.join(fullPath, trainingFile)
					if classification:
						if 'streaming' in trainingFile.lower():
							# check if the used channels in this trials are the same as the previous ones
							with h5py.File(trainingFilePath, 'r') as fl:
								fileUsedChannels = fl['StreamSettings'][5,1].decode('UTF-8')
							# Converting string to list
							fileUsedChannels = fileUsedChannels.strip('][').split(', ')
							fileUsedChannels = list(map(int, fileUsedChannels)) 
							if usedChannels is None:
								usedChannels = fileUsedChannels
							elif usedChannels != fileUsedChannels:
								printError('Not the same number of electrodes in every session. No classifier created!')
								return
							trainingFiles.append(trainingFilePath)
						if len(trainingFiles) == 4:
							if calcEveryClassCombination:
								classificationCombinations = dataInListCombinations(trainingFiles)
								for classificationCombination in classificationCombinations:
									for cntr, channelCombination in enumerate(dataInListCombinations(usedChannels)):
										print('Classifying...' + cntr.__str__())
										subject = os.path.abspath(os.path.join(fullPath, os.pardir)).split('/')[-1]
										results = classify(fileNames=classificationCombination,
															enabledChannels=channelCombination,
															lowcut=lowcut,
															highcut=highcut,
															fs=samplingRate,
															saveClassifier=False,
															subject=subject)
										ITR = calcalate_ITR(ITR_numberOfTargets,
															float(results['LDA Accuracy']),
															ITR_Cn,
															ITR_T)
										results['ITR'] = ITR
										writeDictInFile('wetResults2', results)
							else:
								for cntr, channelCombination in enumerate(dataInListCombinations(usedChannels)):
									print('Classifying...' + cntr.__str__())
									subject = os.path.abspath(os.path.join(fullPath, os.pardir)).split('/')[-1]
									results = classify(fileNames=trainingFiles,
														enabledChannels=channelCombination,
														lowcut=lowcut,
														highcut=highcut,
														fs=samplingRate,
														saveClassifier=False,
														subject=subject)
									ITR = calcalate_ITR(ITR_numberOfTargets,
														float(results['LDA Accuracy']),
														ITR_Cn,
														ITR_T)
									results['ITR'] = ITR
									writeDictInFile('wetResults2', results)
								
							break
					
					if trainingFile.lower() == 'driving.hdf5' and drivenTime:
						print(trainingFilePath)
						totalTime = calculateDrivingTime(trainingFilePath)
						with h5py.File(trainingFilePath, 'r') as fl:
							dtElectroType = fl['StreamSettings'][7,1].decode('UTF-8').split('.')[1]
						subject = os.path.abspath(os.path.join(fullPath, os.pardir)).split('/')[-1]
						durationResults = {
							'Subject': subject,
							'Electrodes': dtElectroType,
							'Total time': totalTime
						}
						writeDictInFile('onlineDuration', durationResults)
			# check if the directory is dry results
			elif entry.lower() == 'dry':
				usedChannels = None    
				trainingFiles = []
				# get the first 4 files contain 'streaming' in their name, for the classification
				for trainingFile in os.listdir(fullPath):
					trainingFilePath = os.path.join(fullPath, trainingFile)
					if classification:
						if 'streaming' in trainingFile.lower():
							# check if the used channels in this trials are the same as the previous ones
							with h5py.File(trainingFilePath, 'r') as fl:
								fileUsedChannels = fl['StreamSettings'][5,1].decode('UTF-8')
							# Converting string to list
							fileUsedChannels = fileUsedChannels.strip('][').split(', ')
							fileUsedChannels = list(map(int, fileUsedChannels)) 
							if usedChannels is None:
								usedChannels = fileUsedChannels
							elif usedChannels != fileUsedChannels:
								printError('Not the same electrodes in every session. No classifier created!')
								return
							trainingFiles.append(trainingFilePath)
						if len(trainingFiles) == 4:
							if calcEveryClassCombination:
								classificationCombinations = dataInListCombinations(trainingFiles)
								for classificationCombination in classificationCombinations:
									for cntr, channelCombination in enumerate(dataInListCombinations(usedChannels)):
										print('Classifying...' + cntr.__str__())
										subject = os.path.abspath(os.path.join(fullPath, os.pardir)).split('/')[-1]
										results = classify(fileNames=classificationCombination,
															enabledChannels=channelCombination,
															lowcut=lowcut,
															highcut=highcut,
															fs=samplingRate,
															saveClassifier=False,
															subject=subject)
										ITR = calcalate_ITR(ITR_numberOfTargets,
															float(results['LDA Accuracy']),
															ITR_Cn,
															ITR_T)
										results['ITR'] = ITR					
										writeDictInFile('dryResuts', results)
							else: 
								for channelCombination in dataInListCombinations(usedChannels):
									print('Classifying...')
									subject = os.path.abspath(os.path.join(fullPath, os.pardir)).split('/')[-1]
									results = classify(fileNames=trainingFiles,
														enabledChannels=channelCombination,
														lowcut=lowcut,
														highcut=highcut,
														fs=samplingRate,
														saveClassifier=False,
														subject=subject)
									ITR = calcalate_ITR(ITR_numberOfTargets,
														float(results['LDA Accuracy']),
														ITR_Cn,
														ITR_T)
									results['ITR'] = ITR					
									writeDictInFile('dryResuts', results)
							break
					if trainingFile.lower() == 'driving.hdf5' and drivenTime:
						print(trainingFilePath)
						totalTime = calculateDrivingTime(trainingFilePath)
						with h5py.File(trainingFilePath, 'r') as fl:
							dtElectroType = fl['StreamSettings'][7,1].decode('UTF-8').split('.')[1]
						subject = os.path.abspath(os.path.join(fullPath, os.pardir)).split('/')[-1]
						durationResults = {
							'Subject': subject,
							'Electrodes': dtElectroType,
							'Total time': totalTime
						}
						writeDictInFile('onlineDuration', durationResults)			


def writeDictInFile(filename=None, fieldsDict=None):
	filename = filename + '.csv'
	if filename is None:
		filename = 'unknown.csv'
	if fieldsDict is None:
		printWarning('No data for writting were given...')
		return
	# csv header
	fieldnames = fieldsDict.keys()
	if not os.path.exists(filename):
	
		with open(filename, 'w', encoding='UTF8', newline='') as f:
			writer = DictWriter(f, fieldnames=fieldnames)
			writer.writeheader()
			writer.writerow(fieldsDict)
			f.close()
	else:
		
		# Open our existing CSV file in append mode
		# Create a file object for this file
		with open(filename, 'a') as f_object:
		  
			# Pass this file object to csv.writer()
			# and get a writer object
			writer = DictWriter(f_object, fieldnames=fieldnames)
		  
			# Pass the list as an argument into
			# the writerow()
			writer.writerow(fieldsDict)
			#Close the file object
			f_object.close()


def dataInListCombinations(data):
	allCombinations =  itertools.chain.from_iterable(itertools.combinations(data, r) for r in range(1, len(data)+1))
	return list(map(list, list(allCombinations)))


def calculateDrivingTime(fileName):
	with h5py.File(fileName, 'r') as fl:
		signalPredicted = fl['signal'][:,8]
		signalTotalTime = fl['signal'][:,10]
		curPrediction = -1
		prevPrediction = -2
		for index in range(len(signalPredicted)):
			curPrediction = signalPredicted[index]
			if curPrediction != prevPrediction:
				prevPrediction = curPrediction
				terminationTimeIndex = index
		if curPrediction != 300:
			printError('Fix time duration!!')
			print(curPrediction ,terminationTimeIndex)	
			
		timeInMinutes = datetime.timedelta(seconds=signalTotalTime[terminationTimeIndex]).__str__().split(':',1)[1]
	return timeInMinutes
					
					
def checkWindowedDataLength(fileName):
	with h5py.File(fileName, 'r') as fl:
		totalWindowedData = fl['packages'][:,:,0:9].shape[0]
		if totalWindowedData != 219:
			printError('windowedDataLength is not 219!')
			print(fileName ,totalWindowedData)	
			
	return totalWindowedData
	

def getCorrelationFiles(dirName):
	# create a list of file and sub directories 
	# names in the given directory 
	dryFileName = None
	wetFileName = None
	listOfFile = os.listdir(dirName)
	for entry in listOfFile:
		# Create full path
		# print(entry)
		fullPath = os.path.join(dirName, entry)
		# If entry is a directory then get the list of files in this directory 
		if os.path.isdir(fullPath):
			# check if the directory is numeric, in other words subject data
			if entry.isnumeric():
				# print(entry)
				getCorrelationFiles(fullPath)
			elif entry.lower() == 'wet':
				for trainingFile in os.listdir(fullPath):
					trainingFilePath = os.path.join(fullPath, trainingFile)
					if 'streaming' in trainingFile.lower():
						wetFileName = trainingFilePath
						break
			elif entry.lower() == 'dry':
				for trainingFile in os.listdir(fullPath):
					trainingFilePath = os.path.join(fullPath, trainingFile)
					if 'streaming' in trainingFile.lower():
						dryFileName = trainingFilePath
						break		
				
	return dryFileName, wetFileName		
	

def calcCorrelation(directory, subj):
	
	fileNameDry,fileNameWet = getCorrelationFiles(directory + "{:02d}".format(subj))
	with h5py.File(fileNameDry, 'r') as fl:    
		signalDry = fl['signal'][:,:]
		
	with h5py.File(fileNameWet, 'r') as fl:    
		signalWet = fl['signal'][:,:]

	a12 = np.cov(signalDry, signalWet)[0][1]
	a11 = np.cov(signalDry, signalWet)[0][0]
	a22 = np.cov(signalDry, signalWet)[1][1]
	cor = (a12/sqrt(a11*a22))
	print('Subject = ' + "{:02d}".format(subj) + ', ' + 'correlation = ' + cor.__str__())

	

def variousClassifications(dirName):
	# create a list of file and sub directories 
	# names in the given directory 
	listOfFile = os.listdir(dirName)
	allFiles = list()
	# Iterate over all the entries
	for entry in listOfFile:
		# Create full path
		# print(entry)
		fullPath = os.path.join(dirName, entry)
		# If entry is a directory then get the list of files in this directory 
		if os.path.isdir(fullPath):
			# check if the directory is numeric, in other words subject data
			if entry.isnumeric():
				# print(entry)
				variousClassifications(fullPath)
			# check if the directory is wet results
			elif entry.lower() == 'wet':
				trainingFiles = []
				# get the first 4 files contain 'streaming' in their name, for the classification
				for trainingFile in os.listdir(fullPath):
					trainingFilePath = os.path.join(fullPath, trainingFile)
					if len(trainingFiles) == 4:
						break
					if 'streaming' in trainingFile.lower():
						trainingFiles.append(trainingFilePath)
						print('Classifying...' + len(trainingFiles).__str__())
						subject = os.path.abspath(os.path.join(fullPath, os.pardir)).split('/')[-1]
						results = classify(fileNames=trainingFiles,
											enabledChannels=[0,1,2],
											lowcut=lowcut,
											highcut=highcut,
											fs=samplingRate,
											saveClassifier=False,
											subject=subject)
						ITR = calcalate_ITR(ITR_numberOfTargets,
											float(results['LDA Accuracy']),
											ITR_Cn,
											ITR_T)
						results['ITR'] = ITR
						writeDictInFile('wetResults2', results)
					
				
			# check if the directory is dry results
			elif entry.lower() == 'dry':
				usedChannels = None    
				trainingFiles = []
				# get the first 4 files contain 'streaming' in their name, for the classification
				for trainingFile in os.listdir(fullPath):
					trainingFilePath = os.path.join(fullPath, trainingFile)
					if len(trainingFiles) == 4:
						break
					if 'streaming' in trainingFile.lower():
						trainingFiles.append(trainingFilePath)
						print('Classifying...' + len(trainingFiles).__str__())
						subject = os.path.abspath(os.path.join(fullPath, os.pardir)).split('/')[-1]
						results = classify(fileNames=trainingFiles,
											enabledChannels=[0,1,2],
											lowcut=lowcut,
											highcut=highcut,
											fs=samplingRate,
											saveClassifier=False,
											subject=subject)
						ITR = calcalate_ITR(ITR_numberOfTargets,
											float(results['LDA Accuracy']),
											ITR_Cn,
											ITR_T)
						results['ITR'] = ITR					
						writeDictInFile('dryResuts2', results)
						



if __name__ == "__main__":
	# files = getListOfFiles("/home/zn/Desktop/Subjects/", drivenTime=True, classification=True, calcEveryClassCombination=False)
	files = variousClassifications("/home/zn/Desktop/Subjects/")
	# for subj in range(10):
	# 	calcCorrelation("/home/zn/Desktop/Subjects/", subj+1)
	# timeInMinutes = datetime.timedelta(seconds=150.53757)
	# print('Manually driven total time: ', timeInMinutes)
	