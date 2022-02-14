# openBCI
## Summary

There has been an increase in the number of studies lately focusing on Brain
Computer Interface (BCI) systems and non-invasive scalp Electroencephalogram
(EEG) measurement, with Steady State Visual Evoked Potential (SSVEP)
playing a significant role due to its higher Information Transfer Rate (ITR)
and signal-to-noise ratio, as well as minimal training requirements. The main
disadvantage of SSVEP is that it relies on a visual stimulus of specific 
frequency for the system to recognize this and its harmonics. Therefore, there
is a limit on the number of stimulus frequencies and henceforth targets, using
a monitor as a stimulus. The SSVEPs can be acquired in the occipital and
parietal lobes, but choosing different EEG channels and adapting data length
to each subject promises better results.
The present research aims to replace an existing system, which relies on
visual navigation systems, with an equally eﬀicient and accurate one that is
more economical thus offering a solution to a serious problem for those facing
mobility disabilities or are quadriplegic and are not yet visually impaired. One
of the objectives therefore, is to offer the opportunity to those with limited
mobilities or none to become mobile and self-reliant in their daily life and the
way they navigate themselves. For the simplicity of the experiment, a robotic
car and receiving video feedback were used, but shortly it may be replaced
with a wheelchair instead.
In this study, data was collected from two types of electrodes, wet and dry,
with the latter being more sensitive to signal. Nonetheless, using Canonical
Correlation Analysis (CCA) can increase accuracy for SSVEP detection. Finally,
the main target of this study is to design a practical BCI system focusing
on low-cost hardware and software, ease of use, and robustness of system performance.

## Overview
###  1.1 Goals and contributions
This thesis based on an existing research which uses a BCI system based on
the SSVEP method. When the subject focuses their gaze on a light
source that is flickering with a steady frequency, the very same frequency
can be detected on the EEG signals of the occipital lobe. In that system,
four targets/checkerboards reverse their pattern on a computer screen, each
one using a different frequency. An EEG recorder captures the user’s brain
signals constantly. When the user focuses on a specific target, the target’s
frequency can be easily detected in the captured EEG, in real-time, using
specific algorithms. Each target is linked with a specific movement of a robot,
therefore, if for example, the user focuses their gaze on the upper target, the
algorithm will recognize the corresponding frequency and send wirelessly the
FORWARD command to the robot.

The correspondence of the remaining targets is:
* lower target – MOVE BACKWARDS
* right target – TURN RIGHT
* left target – TURN LEFT

If no target is recognized (when the user focuses on the center of the
screen), then the robot stops moving. The software of the system is developed
using Python. An LDA classifier is trained to recognize each one of the five
classes (4 targets + center of the screen → forward, right, backward, left, stop
commands), through a short training session. After the training, the user can
run the system in real-time, in order to navigate the corresponding vehicle.
The EEG signal recording is performed using a commercial EEG recorder, the
g.MOBILab of the g.tec company, which includes 8 monopolar wet electrodes,
with a gold-plated 10mm diameter cup.

This study focuses on the below modifications:

1. Use of the open-source [openBCI](https://openbci.com/ "openBCI") board as an EEG recorder. The board
should be incorporated in the pre-existing system and run with the
python software.

2. Explore the usability of the new dry electrodes g.SAHARA and compare
them with the wet, already used. Dry electrodes are very convenient and
easy to wear, as they do not require any conductive gel compared to wet,
but they present a lower Signal to Noise Ratio (SNR).To maximize the
SNR as much as possible, the training sessions’ duration increased, a
higher window size was used and more filtering was added to reduce the
Alternating Current (AC) frequency during preprocessing.
