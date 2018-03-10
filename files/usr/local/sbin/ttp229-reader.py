#!/usr/bin/python
# -----------------------------------------------------------------------------
# This script polls the TTP229 and writes key-events to the pipe
# /var/run/ttp229-keypad.fifo.
#
# Please configure the two pins used by the TTP229-keybad in /etc/ttp229-keypad.conf
#
# Author: Bernhard Bablok
# License: GPL3
#
# Website: https://github.com/bablokb/pi-ttp229-keypad
#
# -----------------------------------------------------------------------------

import os, sys, time, signal
import RPi.GPIO as GPIO
import ConfigParser

FIFO_NAME="/var/run/ttp229-keypad.fifo"

# --- read configuration   ----------------------------------------------------

def read_config(parser):
  global NUM_KEYS, SCL_PIN, SDO_PIN, KEY_DELAY, POLL_DELAY, BOUNCE_TIME
  
  NUM_KEYS = parser.getint("GLOBAL", "NUM_KEYS")
  
  SCL_PIN = parser.getint("PINS", "SCL_PIN")
  SDO_PIN = parser.getint("PINS", "SDO_PIN")

  KEY_DELAY   = parser.getfloat("TIMING", "KEY_DELAY")
  POLL_DELAY  = parser.getfloat("TIMING", "POLL_DELAY")
  BOUNCE_TIME = parser.getfloat("TIMING", "BOUNCE_TIME")

# --- setup pipe   ------------------------------------------------------------

def setup_fifo():
  """ setup pipe """

  global fifo

  if os.path.exists(FIFO_NAME):
    os.unlink(FIFO_NAME)
  os.mkfifo(FIFO_NAME,0644)
  fifo = open(FIFO_NAME,"rw+",0)

# --- setup signal handler   -----------------------------------------------

def signal_handler(_signo, _stack_frame):
  """ signal-handler to cleanup GPIOs """

  global fifo
  fifo.close()
  GPIO.cleanup()
  sys.exit(0)

# --- main loop   -------------------------------------------------------------

def read_keys():
  """ read key-presses in an infinite-loop """

  global fifo

  # setup pins
  GPIO.setmode(GPIO.BCM)
  GPIO.setup(SCL_PIN,GPIO.OUT)
  GPIO.setup(SDO_PIN,GPIO.IN)

  # set clock-pin to high
  GPIO.output(SCL_PIN,GPIO.HIGH)
  time.sleep(POLL_DELAY)

  ts_old = -10000
  while True:
    key = 0
    time.sleep(POLL_DELAY)
    ts_key = time.time()

    # poll-cycle: send NUM_KEYS LOW/HIGH on clock-pin and read data-pin
    #             for key n we expect n high values and NUM_KEYS-n lows
    for i in range(1,NUM_KEYS+1):
      GPIO.output(SCL_PIN,GPIO.LOW)
      time.sleep(KEY_DELAY)
      keyval=GPIO.input(SDO_PIN)
      if not keyval:
        key = i
      GPIO.output(SCL_PIN,GPIO.HIGH)
      time.sleep(KEY_DELAY)

    # check if a key was pressed and prevent bouncing
    if key and (ts_key - ts_old) > BOUNCE_TIME:
      # write to pipe
      fifo.write("%d\n" % key)
      ts_old = ts_key
  
# --- main program   ----------------------------------------------------------

# read configuration
parser = ConfigParser.RawConfigParser()
parser.read('/etc/ttp229-keypad.conf')
read_config(parser)

# setup signal-handler
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# setup pipe
setup_fifo()

# start polling
read_keys()

