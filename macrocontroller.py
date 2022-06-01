# macrocontroller.py
from adafruit_midi.control_change import ControlChange

from colors import COLORS
from config_consts import *

class ValueMode:
	MOMENTARY = 0
	TOGGLE = 1
	REVERSE = 2
	ON_ONLY = 3


class Control:
	"""Generic Control"""
	_id:int
	_cc:int
	_min_value:int = 0
	_max_value:int = 127

	def __init__(self,id):
		self._id = id
		self._cc = id+1
	def __repr__(self):
		return f"id:{self.id},cc:{self.cc}"

	@property
	def id(self):
		return self._id
	@property
	def cc(self):
		return self._cc
	@cc.setter
	def cc(self,val):
		self._cc = val

	def send(self):
		"""Send action, performs tasks.\n
		Should this return something? Handle everything inside with referenced objects?
		"""
		return f"Generic Send id:{self.id}"
	def receive(self):
		"""Receive action, performs tasks.\n
		Should this return something? Handle everything inside with referenced objects?
		'"""
		return f"Generic Receive id:{self.id}"

class KeyControl(Control):
	def send(self):
		return f"Key midi for id:{self.id}"

class EncoderClickControl(Control):
	def send(self):
		return f"EncoderClick midi for id:{self.id}"

class EncoderControl(Control):
	def send(self):
		return f"Encoder midi for id:{self.id}"

class MeterControl(Control):
	def send(self):
		return f"Meter midi for id:{self.id}"
	def receive(self):
		return f"Meter midi for id:{self.id}"

class MacroController:
	"""Controller containing list of control objects. \n
	Inits with a config json.\n
	Keys, encoders, encoder clicks and meters

	"""
	controls = list()
	_config = None
	_cc_to_control = dict()
	_events_queued = False
	def __init__(self,config):
		self._config = config
		pass
		for k in KEYS:
			self.controls.append(KeyControl(k))
			self._cc_to_control[self.controls[k].cc] = k
		self.controls.append(EncoderControl(ENCODER_ID))
		self._cc_to_control[self.controls[ENCODER_ID].cc] = ENCODER_ID
		self.controls.append(EncoderClickControl(ENCODER_CLICK_ID))
		self._cc_to_control[self.controls[ENCODER_CLICK_ID].cc] = ENCODER_CLICK_ID

	def control(self,cc:int)->int:
		return self._cc_to_control.get(cc,None)
		# self.cc = config["cc"]
		# self.key_no = config["key_no"]
		# self.key = config["key_no"]-1
		# self.description = config["description"]
		# self.on_color = COLORS.get(config["on_color"],int(config.get("on_color_hex",0xFF0000)))
		# self.off_color = COLORS.get(config["off_color"],int(config.get("off_color_hex",0xFFFFFF)))
		# self.max_value = config["max_value"]
		# self.min_value = config["min_value"]
		# self.toggle = config["toggle"]
		# self.current_value = config["max_value"] if int(config["toggle"]) in [1,2] else config["min_value"]
		# self.prev_value = config["min_value"] if int(config["toggle"]) == 2 else config["max_value"]
		# self.prev_time = 0