import h5py
import numpy as np
import sys

sys.path.append('..')
from utils.constants import Constants as cnst
from constants import getSessionFilename
from tkinter import *
from tkinter import filedialog
from tkinter.filedialog import asksaveasfilename

readFromLine = 1000
readToLine = 20000
root = Tk()
root.withdraw()
name = filedialog.askopenfilename(title="Choose an openbci GUI streaming text filename",
                                  defaultextension=".txt",
                                  filetypes=[('Text Document', '*.txt')])

file1 = open(name, 'r')
Lines = file1.readlines()

count = 0
dd = []
# Strips the newline character
for line in Lines:
	count += 1
	if readFromLine <= count <= readToLine:
		sp = line.split(',')
		cp = [float(i) for i in sp[1:5]]
		dd.append(cp)
		print(cp)

filename = asksaveasfilename(title="Choose a name for the hdf5 file",
                             initialfile=getSessionFilename(openbciGUI=True),
                             defaultextension=".hdf5",
                             filetypes=[('HDF5', '.hdf5')],
                             initialdir=cnst.destinationFolder,
                             confirmoverwrite=True)

if not filename:
	exit()
print(filename)
hf = h5py.File(filename, 'w')
windowedSignal = np.array(dd).astype(float)
hf.create_dataset("signal", data=windowedSignal)
hf.close()
