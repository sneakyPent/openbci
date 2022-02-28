vversion v3.1.2

* Basic info
  * Bluetooth cannot be used for eeg, only dongle or WI-FI shield
  * Can be used for EEG ECG EMG simultaneously if needed
  * 11 pins
      * 8 data channel pins
      * 1 SRB pin   (reference channel for the eeg)
      * 1 AGND pin  (reference channel for the emg)
      * 1 Bias pin  (Noise-cancelling for eeg & reference channel for the ecg)
  * For EEG, we use only the bottom pins for every connection
  * Daisy Module can be used if more channels needed
  * useful infos for cyton board sdk: https://docs.openbci.com/docs/02Cyton/CytonSDK
  * With USB Dongle cannot and will not stream data over 250SPS. Plug in the WI-FI Shield to get speeds over 250SPS
    streaming.
  * channel values are 24-bit signed, MSB first
  * accelerometer data (x,y,z) can be used to detect which way the board is oriented in 3D space.
  * if autoproxy error for manager_owned=True -> https://bugs.python.org/issue30256
  * zero array in channel data  [0, 0, 0, 0, 0, 0, 0, 0] returns after stop - start in openbci gui too
  * 
    * board sends wrong stop byte which leads to skip read bytes and lose data, when batteries are not charges enough
    * with full charged board streaming (30 minutes) did not received any skipped byte error message 
