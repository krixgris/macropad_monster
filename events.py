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