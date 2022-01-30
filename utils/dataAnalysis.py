from operator import index
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
from utils.coloringPrint import printWarning

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

def calcalate_ITR(N,P):
	# T = getShuffledTargetsLength()*cnst.targetDuration
	T = 120
	B = log(N,2) + P*log(P,2) + ((1-P)*log(((1-P)/(N-1)),2))
	ITR = (60/T) * B
	print(B)
	return ITR
	
	
	

def getListOfFiles(dirName):
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
				allFiles = allFiles + getListOfFiles(fullPath)
			# check if the directory is wet results
			elif entry.lower() == 'wet':
				trainingFiles = []
				# get the first 4 files contain 'streaming' in their name, for the classification
				for trainingFile in os.listdir(fullPath):
					trainingFilePath = os.path.join(fullPath, trainingFile)
					if 'streaming' in trainingFile.lower():
						trainingFiles.append(trainingFilePath)
					if len(trainingFiles) == 4:
						channels = [0, 1, 2]
						print('Classifying...')
						subject = os.path.abspath(os.path.join(fullPath, os.pardir)).split('/')[-1]
						results = classify(fileNames=trainingFiles,
											enabledChannels=channels,
											lowcut=lowcut,
											highcut=highcut,
											fs=samplingRate,
											saveClassifier=False,
											subject=subject)
						writeClassificationInFile('dokimiRes', results)
			# check if the directory is dry results
			elif entry.lower() == 'dry':
				# print(entry)
				pass
			else:
				pass
		else:
			allFiles.append(fullPath)
				
	return allFiles


def writeClassificationInFile(filename=None, fieldsDict=None):
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


if __name__ == "__main__":
	ITR = calcalate_ITR(5,0.906)
	print(ITR)
	
