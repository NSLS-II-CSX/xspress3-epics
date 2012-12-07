#!/bin/env dls-python2.6

# Library version specification required for dls libraris
from pkg_resources import require
import sys
require('cothread==2.8')

#print sys.path

import cothread
from cothread.catools import *

base_pv = "mp49:xsp3"
hdf_pv = "mp49:xsp3:hdf5"
timeout_ = 100

num_channels = 4
config_path = "/home/mp49/xspress3_settings/"
trigger_mode = 3
nd_attributes_file = "/home/mp49/xsp3.xml"
run_flags = 1 #0=normal, 1=playback
file_path = "/tmp/"
file_name = "xsp"
file_template = "%s%s%d.hdf5"
file_write_mode = 2

num_frames = 10


def connect():
   print "Connecting..."
   connected = caget(base_pv + ":CONNECTED")
   if (not connected): 
      caput(base_pv + ":NUM_CHANNELS", num_channels, wait=True)
      caput(base_pv + ":CONFIG_PATH", config_path, wait=True, datatype=cothread.catools.DBR_CHAR_STR)
      caput(base_pv + ":RUN_FLAGS", run_flags, wait=True)
      caput(base_pv + ":CONNECT", 1, wait=True, timeout=timeout_)

def file_setup():
   print "Setting up file parameters..."
   caput(hdf_pv + ":FilePath", file_path, wait=True, datatype=cothread.catools.DBR_CHAR_STR)
   path_exists = caget(hdf_pv + ":FilePathExists_RBV")
   if (not path_exists):
      print "ERROR: file path doesn't exist"
      sys.exit(1)
   caput(hdf_pv + ":FileName", file_name, wait=True, datatype=cothread.catools.DBR_CHAR_STR)
   caput(hdf_pv + ":FileTemplate", file_template, wait=True, datatype=cothread.catools.DBR_CHAR_STR)
   caput(hdf_pv + ":FileWriteMode", "Stream", wait=True)
   caput(base_pv + ":NDAttributesFile", nd_attributes_file, wait=True, datatype=cothread.catools.DBR_CHAR_STR)

def acquire():
   print "Acquire..."
   #Acquire, but don't wait (this only returns when acqusition is complete).
   caput(base_pv + ":Acquire", 1, wait=False)
   cothread.Sleep(1.0)
   #Now generate the triggers
   cothread.Sleep(1.0) #Or, wait on an event from a different thread

def acquireAndCapture():
   print "Acquire and capture..."
   caput(hdf_pv + ":Capture", 1, wait=False) #Don't wait, this blocks until capture finished.
   #Wait until Capture_RBV is set
   capture_rbv = 0
   while (not capture_rbv):
      capture_rbv = caget(hdf_pv + ":Capture_RBV")
      cothread.Sleep(0.1)
   acquire()
   

def setNumFrames(num_frames):
   print "Set number of frames to " + str(num_frames)
   #Set the number of frames to collect
   caput(base_pv + ":NumImages", num_frames, wait=True)
   caput(hdf_pv + ":NumCapture", num_frames, wait=True)


def main():
   print "Testing Xspress3..."

   #Connect to the Xspress3 (if the IOC has been restarted)  
   connect()

   print "Set up trigger mode..."
   caput(base_pv + ":TriggerMode", trigger_mode, wait=True)

   #Enable array callbacks to the areaDetector plugins
   caput(base_pv + ":ArrayCallbacks", 1, wait=True)
   #Enable HDF plugin
   caput(hdf_pv + ":EnableCallbacks", 1, wait=True)

   #Set up file saving plugin
   file_setup()

   #Do we need to set up the plugins by taking a single frame?
   hdf_dims = caget(hdf_pv + ":NDimensions_RBV")
   if (hdf_dims == 0):
      #Take a single frame to set up the plugins
      setNumFrames(1)
      acquire()

   #Now do the real data collection
   setNumFrames(num_frames)
   acquireAndCapture()

   #Generate num_frames triggers now

   #Wait on event here, or poll the Acquire_RBV PV
   acquire_rbv = 1
   while(acquire_rbv):
      print "acquire " + str(acquire_rbv)
      acquire_rbv = caget(base_pv + ":Acquire_RBV")
      cothread.Sleep(0.1)

   #Acqusition is finished, although file saving might still be progressing in the file saving plugin.

   #Check detector status here
   ad_status = caget(base_pv + ":DetectorState_RBV")
   if (ad_status != 0):
      print "ERROR: data collected failed"
      ad_string = caget(base_pv + ":StatusMessage_RBV")
      print ad_string
      sys.exit(1)

   #Check number of frames read out
   num_frames_readout = caget(base_pv + ":ArrayCounter_RBV")
   print "Num frames read out: " + str(num_frames_readout)

   #Check file saving here
   #Wait for file saving to end
   saving = 1
   while (saving):
      print "saving " + str(saving)
      saving = caget(hdf_pv + ":Capture_RBV")
      cothread.Sleep(0.1)
   #Check status
   num_captured = caget(hdf_pv + ":NumCaptured_RBV")
   if (num_captured != num_frames):
      print "ERROR: we did not collect all the frames."
      print "num_captured: " + str(num_captured)
   write_status = caget(hdf_pv + ":WriteStatus")
   if (write_status):
      print "ERROR: problem writing file."
      hdf_string = caget(hdf_pv + ":WriteMessage")
      print hdf_string
      sys.exit(1)

   print "Finshed"
   print "Saved " + str(num_captured) + " frames."

if __name__ == "__main__":
        main()
