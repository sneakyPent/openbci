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


def calcalate_ITR(N,P):
	# T = getShuffledTargetsLength()*cnst.targetDuration
	T = 120
	B = log(N,2) + P*log(P,2) + ((1-P)*log(((1-P)/(N-1)),2))
	ITR = (60/T) * B
	print(B)
	return ITR
	
	
if __name__ == "__main__":
	ITR = calcalate_ITR(5,0.906)
	print(ITR)
	
