# events.py

class EventType():
	_name:str
	_int_value:int

	def __init__(self,value):
		
		self._name = ""
		self._int_value = value

	def __int__(self):
		return int(self._int_value)
	def __str__(self):
		return self._name
	def __repr__(self):
		return int(self._int_value)#f"{self._name}: {self._int_value}"

	@property
	def name(self):
		return self._name
	@property
	def value(self):
		return self._int_value


class Events:
	"""Faux-enum. Extend this with more enums as needed"""
	KEY_PRESS = 0
	KEY_RELEASE = 1
	ENC_PRESSED = 2
	ENC_RELEASED = 3
	ENC_TURN = 4
	MIDI_CC = 5
	MIDI_NOTE_ON = 6
	MIDI_NOTE_OFF = 7

	_lookup = dict()

	def __init__(self):
		for k,v in Events.__dict__.items():
			if k[0] != '_' and type(v) is int:
				self._lookup[v] = k
	def event_type(self,event_type):
		return self._lookup.get(event_type,"_Undefined_")
	def __repr__(self):
		return self._lookup

EVENTS = Events()
"""Enum for events. EVENT.event_type() returns name of event if needed."""
