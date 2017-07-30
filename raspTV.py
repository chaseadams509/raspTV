#!/usr/bin/env python
from devicehub.devicehub import Sensor, Actuator, Device, Project

import threading
from time import sleep
from subprocess import call
#import RPi.GPIO as GPIO
import json

PROJECT_ID = '' #project_id
DEVICE_UUID = '' #device_id
API_KEY = '' #API_key
ACTUATOR_HDMI = 'hdmi_port'
ACTUATOR_STATE = 'tv_state'
ACTUATOR_VOLUP = 'tv_volume_increase'
ACTUATOR_VOLDOWN = 'tv_volume_decrease'

rasp_state = 0
rasp_hdmi = 2
rasp_hdmi_world = ['bad', 'HDMI1', 'HDMI2', 'HDMI3', 'bad', 'bad']
rasp_hdmi_probs = [0.01, 0.32, 0.32, 0.33, 0.01, 0.01]
p_announce = 0.99
p_exact = 0.90
p_under = 0.09
p_over  = 0.01
rasp_volume = 30

def hdmi_sense(Z, p):
	global rasp_hdmi_world
	global p_announce
	q = []
	for i in range(len(p)):
		hit = Z in rasp_hdmi_world[i]
		q.append(p[i] * (hit * p_announce) + (1-hit) * (1 - p_announce))
	s = sum(q)
	for i in range(len(q)):
		q[i] = q[i] / s
	return q

def hdmi_move(p):
	global p_exact
	global p_under
	global p_over
	q = []
	U = 1 # Can only move one at a time
	for i in range(len(p)):
		s = p_exact * p[(i-U) % len(p)]
		s = s + p_under * p[(i-U+1) % len(p)]
		s = s + p_over  * p[(i-U-1) % len(p)]
		q.append(s)
	return q

def func_status():
	global rasp_state
	rasp_state = not rasp_state
	print "Changing TV to ", rasp_state
	call(["irsend", "SEND_ONCE", "sanyo-tv01", 
		"KEY_POWER"])
	sleep(1)
	return

def func_volume(state, decrease):
	global rasp_volume
	while state > 0:
		if decrease:
			call(["irsend", "SEND_ONCE", "sanyo-tv01", 
				"KEY_VOLUMEDOWN"])
			rasp_volume -= 1
		else:
			call(["irsend", "SEND_ONCE", "sanyo-tv01", 
				"KEY_VOLUMEUP"])
			rasp_volume += 1
		state -= 1
		sleep(0.01)
	print "Rasp_volume is now", rasp_volume
	sleep(1)
	return

def func_hdmi(state):
	global rasp_hdmi
	global rasp_hdmi_probs
	if state < 10:
		print "Increasing hdmi by", state
		state_adjusted = state
		call(["irsend", "SEND_ONCE", "sanyo-tv01", 
			"KEY_VIDEO"])
		while state_adjusted > 0:
			rasp_hdmi_probs = hdmi_move(rasp_hdmi_probs)
			call(["irsend", "SEND_ONCE", "sanyo-tv01", 
				"KEY_VIDEO"])
			state_adjusted -= 1
		rasp_hdmi_probs = hdmi_sense('HDMI', rasp_hdmi_probs)
	elif state < 50:
		state_adjusted = state - 10
		print "Setting hdmi to", state_adjusted
		movement = (6 + state_adjusted - rasp_hdmi) % 6
		call(["irsend", "SEND_ONCE", "sanyo-tv01", 
			"KEY_VIDEO"])
		while movement > 0:
			rasp_hdmi_probs = hdmi_move(rasp_hdmi_probs)
			call(["irsend", "SEND_ONCE", "sanyo-tv01", 
				"KEY_VIDEO"])
			movement -= 1
	else:
		state_adjusted = state - 50
		print "Announcing hdmi as", state_adjusted
		rasp_hdmi_probs = hdmi_sense(str(state_adjusted), rasp_hdmi_probs)
	m_prob = max(rasp_hdmi_probs)
	rasp_hdmi = rasp_hdmi_probs.index(m_prob)
	print "rasp_hdmi is now", rasp_hdmi
	print "hdmi probabilities are:", rasp_hdmi_probs
	sleep(0.5)
	return

def callback_status(payload):
	msg = str(payload)
	status_state = Act_Status.state
	if status_state == 0:
		return
	func_status()
	Act_Status.set(0)
	return

def callback_increase(payload):
	msg = str(payload)
	increase_state = int(Act_Increase.state)
	if increase_state == 0:
		return
	func_volume(increase_state, False)
	Act_Increase.set(0)
	return

def callback_decrease(payload):
	msg = str(payload)
	decrease_state = int(Act_Decrease.state)
	if decrease_state == 0:
		return
	func_volume(decrease_state, True)
	Act_Decrease.set(0)
	return

def callback_hdmi(payload):
	msg = str(payload)
	hdmi_state = int(Act_HDMI.state)
	if hdmi_state == 0:
		return
	func_hdmi(hdmi_state)
	Act_HDMI.set(0)
	return

if __name__ == "__main__":
	project = Project(PROJECT_ID)
	device = Device(project, DEVICE_UUID, API_KEY)
	Act_Status = Actuator(Actuator.DIGITAL, ACTUATOR_STATE)
	Act_Increase = Actuator(Actuator.ANALOG, ACTUATOR_VOLUP)
	Act_Decrease = Actuator(Actuator.ANALOG, ACTUATOR_VOLDOWN)
	Act_HDMI = Actuator(Actuator.ANALOG, ACTUATOR_HDMI)
	device.addActuator(Act_Status, callback_status)
	device.addActuator(Act_Increase, callback_increase)
	device.addActuator(Act_Decrease, callback_decrease)
	device.addActuator(Act_HDMI, callback_hdmi)
	failed_start = (call(["sudo", "/etc/init.d/lirc", "stop"]) or
			call(["sudo", "/etc/init.d/lirc", "start"]) or
			call(["sudo", "lircd", "-d", "/dev/lirc0"]) or
			call(["irsend", "LIST", "sanyo-tv01", ""]))
	if failed_start:
		print "Could not initialize"

	
	keep_going = True
	while keep_going:
		try:
			while True:
				pass
		except KeyboardInterrupt:
			print "Ending raspTV"
			keep_going = False

