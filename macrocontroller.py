# macrocontroller.py
from adafruit_macropad import MacroPad
from adafruit_midi.control_change import ControlChange

from colors import COLORS
from config_consts import *

class ControlMessage():
	def __init__(self, control, value, event_type, target_control=None, target_event_type=None):
		self.control = control
		self.value = value
		self.event_type = event_type
	def __repr__(self):
		return f"control: {self.control}, value: {self.value}, event_type: {EVENTS.event_type(self.event_type)}"

class Events:
	"""Faux-enum.\n
	First char can NOT be _ and name must be all caps and/or numbers.\n
	Extend this with more enums as needed.\n
	\n
	Following phrases are reserved and used for event sets:\n\n
	If name contains:\n
		KEY_ it is grouped as a KEY_EVENTS\n
		ENCODER_ - ENCODER_EVENTS\n
		ENCLICK_ - ENCODER_CLICK_EVENTS\n
		METER_ - METER_EVENTS\n
		MIDI_ - MIDI_EVENTS\n
		NOT MIDI_ - INTERNAL_EVENTS\n
		INIT_ - INIT_EVENTS\n
	
	Be considerate of names to ensure events are grouped correctly if this is important for logic anywhere.
	"""
	DEFAULT = -1
	KEY_PRESS = 0
	KEY_RELEASE = 1
	ENCLICK_PRESS = 2
	ENCLICK_RELEASE = 3
	ENCODER_TURN = 4
	MIDI_CC = 5
	MIDI_NOTE_ON = 6
	MIDI_NOTE_OFF = 7
	MIDI_KEY_PRESS = 8
	MIDI_KEY_RELEASE = 9
	MIDI_ENCODER_TURN = 10
	MIDI_ENCLICK = 11
	MIDI_ENCLICK_RELEASE = 12
	MIDI_METER_UPDATE = 13
	INTERNAL_METER_UPDATE = 14
	METER_UPDATE = 15
	INIT_MTR = 16

	_lookup = dict()

	def __init__(self):
		for k,v in Events.__dict__.items():
			if k[0] != '_' and k.isupper() and type(v) is int:
				self._lookup[v] = k
	def event_type(self,event_type):
		"""Returns name of event type. Undefined event returns _Undefined_."""
		return self._lookup.get(event_type,"_Undefined_")
	def __repr__(self):
		return self._lookup

EVENTS = Events()
"""Enum for events. EVENT.event_type() returns name of event if needed."""

KEY_EVENTS = {event for event in EVENTS._lookup.keys() if 'KEY_' in EVENTS.event_type(event)}
ENCODER_CLICK_EVENTS = {event for event in EVENTS._lookup.keys() if 'ENCLICK_' in EVENTS.event_type(event)}
ENCODER_EVENTS = {event for event in EVENTS._lookup.keys() if 'ENCODER_' in EVENTS.event_type(event)}
METER_EVENTS = {event for event in EVENTS._lookup.keys() if 'METER_' in EVENTS.event_type(event)}
INIT_EVENTS = {event for event in EVENTS._lookup.keys() if 'INIT_' in EVENTS.event_type(event)}
MIDI_EVENTS = {event for event in EVENTS._lookup.keys() if 'MIDI_' in EVENTS.event_type(event)}
ALL_EVENTS = {event for event in EVENTS._lookup.keys()}
INTERNAL_EVENTS = ALL_EVENTS-MIDI_EVENTS

print(f"{MIDI_EVENTS=}")
print(f"{INTERNAL_EVENTS=}")
print(f"{KEY_EVENTS=}")
print(f"{ENCODER_CLICK_EVENTS=}")
print(f"{ENCODER_EVENTS=}")
print(f"{METER_EVENTS=}")
print(f"{INIT_EVENTS=}")


class ControlConfiguration:
	control:int
	cc:int
	toggle:bool
	on_color:int
	off_color:int
	min_value:int
	max_value:int
	description:str
	current_value:int
	prev_value:int

	def __init__(self, control, config:dict()):
		self.control = control
		self.cc = config.get("cc")
		self.toggle = True if config.get("toggle",False) == 1 else False
		self.on_color = COLORS.get(config["on_color"],int(config.get("on_color_hex",0xFF0000)))
		self.off_color = COLORS.get(config["off_color"],int(config.get("off_color_hex",0xFFFFFF)))
		self.min_value = config.get("min_value",0)
		self.max_value = config.get("max_value",127)
		self.description = config.get("description","")

	def __repr__(self):
		return (self.control,self.cc,self.toggle,self.on_color, self.description)

		# self.current_value = config["max_value"] if int(config["toggle"]) in [1,2] else config["min_value"]
		# self.prev_value = config["min_value"] if int(config["toggle"]) == 2 else config["max_value"]
		# self.prev_time = 0




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


class MacroControlConfiguration:
	"""Configuration for colors, behaviours etc for all controls
	"""
	page = dict()
	page_count:int = 0
	def __init__(self,config):
		self.page_count = 0
		for page,conf in config.items():
			page_conf = dict()
			for k,v in conf.items():
				if(k == 'enc_click'):
					k = ENCODER_CLICK_ID
				elif(k == 'enc'):
					k = ENCODER_ID
				elif(k):
					k = int(k)-1
				page_conf[k] = ControlConfiguration(k,v)
			self.page[self.page_count] = page_conf
			self.page_count += 1

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
	_value:int = 0
	_prev_value:int = 0
	_toggle:bool = False
	_default_event = EVENTS.DEFAULT

	_on_color = 0xFFFFFF#COLORS.get(config["on_color"],int(config.get("on_color_hex",0xFF0000)))
	_off_color =  0x000000#COLORS.get(config["off_color"],int(config.get("off_color_hex",0xFFFFFF)))

	def __init__(self,id,cc = None, cc_offset = 0, config:ControlConfiguration=None):
		self._id = id
		if(config is None):
			self._cc = (cc if cc is not None else id + 1) + cc_offset
		else:
			self._cc = config.cc + cc_offset
			self._min_value = config.min_value
			self._max_value = config.max_value
			self._value = config.max_value
			self._prev_value = config.min_value
			self._toggle = config.toggle
			self._on_color = config.on_color
			self._off_color = config.off_color

	def __repr__(self):
		return f"id:{self.id},cc:{self.cc},max_value:{self.max_value}"

	@property
	def id(self):
		return self._id
	@property
	def cc(self):
		return self._cc
	@cc.setter
	def cc(self,val):
		self._cc = val

	@property
	def min_value(self):
		return self._min_value
	@property
	def max_value(self):
		return self._max_value

	def send(self, value = None, event_type=EVENTS.DEFAULT)->ControlMessage:
		"""Returns ControlMessage object
		"""
		return f"Generic Send id:{self.id}"
	def receive(self, value = None, event_type=EVENTS.DEFAULT)->ControlMessage:
		"""Returns ControlMessage object
		'"""
		return f"Generic Receive id:{self.id}"

class KeyControl(Control):
	_default_event = EVENTS.KEY_PRESS

	def send(self, value = None, event_type=EVENTS.DEFAULT)->ControlMessage:
		if(event_type == EVENTS.DEFAULT):
			event_type = self._default_event

		if(value is None):
			if(event_type == EVENTS.KEY_PRESS):
				value = self.max_value
			elif(event_type == EVENTS.KEY_RELEASE):
				value = self.min_value
			elif(event_type == EVENTS.MIDI_KEY_PRESS):
				value = self.max_value
			elif(event_type == EVENTS.MIDI_KEY_RELEASE):
				value = self.min_value

		# return f"Key midi for id:{self.id}, value:{value}, event:{EVENTS.event_type(event_type)}"
		return ControlMessage(self.cc, value, event_type)

class EncoderClickControl(Control):
	_default_event = EVENTS.ENCLICK_PRESS
	
	def send(self, value = None, event_type=EVENTS.DEFAULT)->ControlMessage:
		if(event_type == EVENTS.DEFAULT):
			event_type = self._default_event
		if(value is None):
			if(event_type == EVENTS.ENCLICK_PRESS):
				value = self.max_value
			elif(event_type == EVENTS.ENCLICK_RELEASE):
				value = self.min_value
			elif(event_type == EVENTS.MIDI_ENCLICK):
				value = self.max_value
			elif(event_type == EVENTS.MIDI_ENCLICK_RELEASE):
				value = self.min_value
		# return f"EncoderClick midi for id:{self.id}, event:{EVENTS.event_type(event_type)}"
		return ControlMessage(self.cc, value, event_type)

class EncoderControl(Control):
	_default_event = EVENTS.ENCODER_TURN
	
	def send(self, value = None, event_type=EVENTS.DEFAULT)->ControlMessage:
		if(event_type == EVENTS.DEFAULT):
			event_type = self._default_event
		if(value is None):
			value = self.max_value
		#return f"Encoder midi for id:{self.id}, value:{value}, event:{EVENTS.event_type(event_type)}"
		return ControlMessage(self.cc, value, event_type)

class MeterControl(Control):
	_default_event = EVENTS.METER_UPDATE
	
	def send(self, value = None, event_type=EVENTS.DEFAULT)->ControlMessage:
		if(event_type == EVENTS.DEFAULT):
			event_type = self._default_event
		# return f"Meter midi for id:{self.id}, event:{EVENTS.event_type(event_type)}"
		return ControlMessage(self.cc, value, event_type)
	def receive(self, value = None, event_type=EVENTS.DEFAULT)->ControlMessage:
		return f"Meter midi for id:{self.id}, event:{EVENTS.event_type(event_type)}"

class MacroController:
	"""Controller containing list of control objects. \n
	Inits with a config json.\n
	Keys, encoders, encoder clicks and meters

	"""
	control_pages = dict()
	controls = list()
	_config = None
	_cc_to_control = dict()
	# _events_queued = False
	event_queue = dict()
	defined_cc = set()
	"""Implement cc_set to check for existance"""
	macropad = MacroPad()
	def __init__(self,macrocontroller_config):
		self._config = MacroControlConfiguration(macrocontroller_config)

		self.macropad.display.auto_refresh = False
		self.macropad.pixels.brightness = MACROPAD_BRIGHTNESS

		# self.init_page_config()
		for page_key,page in self._config.page.items():
			self.control_pages[page_key] = list()

			for k in KEYS:
				self.control_pages[page_key].append(KeyControl(k, config=page.get(k,None)))
				self._cc_to_control[self.control_pages[page_key][k].cc] = k
			print(page_key)
			# self.control_pages[page_key].append(EncoderControl(ENCODER_ID, config=page.get(ENCODER_ID)))
			self.control_pages[page_key].append(EncoderControl(ENCODER_ID, config=self._config.page[0].get(ENCODER_ID)))
			
			self._cc_to_control[self.control_pages[page_key][ENCODER_ID].cc] = ENCODER_ID
			# self.control_pages[page_key].append(EncoderClickControl(ENCODER_CLICK_ID, config=page.get(ENCODER_CLICK_ID)))
			self.control_pages[page_key].append(EncoderClickControl(ENCODER_CLICK_ID, cc_offset=page_key, config=self._config.page[0].get(ENCODER_CLICK_ID)))
			
			self._cc_to_control[self.control_pages[page_key][ENCODER_CLICK_ID].cc] = ENCODER_CLICK_ID
		self.init_defined_cc()
		# free memory once config is loaded
		del self._config
		# init controls from first page
		self.controls = self.control_pages[0]
	
	def init_page_config(self, page = 0):
		self.controls = self.control_pages[page]
		# self.controls.clear()
		for k in KEYS:
		# 	self.controls.append(KeyControl(k, config=self._config.page[page].get(k,None)))
			self._cc_to_control[self.controls[k].cc] = k
		# 	#print(config["1"][str(k+1)].get("on_color",0xFFFFFF))
		# self.controls.append(EncoderControl(ENCODER_ID, config=self._config.page[0][ENCODER_ID]))
		self._cc_to_control[self.controls[ENCODER_ID].cc] = ENCODER_ID
		# self.controls.append(EncoderClickControl(ENCODER_CLICK_ID, config=self._config.page[0][ENCODER_CLICK_ID]))
		self._cc_to_control[self.controls[ENCODER_CLICK_ID].cc] = ENCODER_CLICK_ID
		self.init_defined_cc()

	def control(self,cc:int)->int:
		return self._cc_to_control.get(cc,None)

	def queue(self, targs):
		"""Add tuple (id,value,event_type) to event_queue
		"""
		pass

	def page():
		pass

	def init_defined_cc(self):
		"""Init set defined_cc for lookup in midi in"""
		self.defined_cc = {control.cc for control in self.controls}


		
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