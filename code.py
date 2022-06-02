# code.py
from adafruit_macropad import MacroPad
from adafruit_midi.control_change import ControlChange
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.pitch_bend import PitchBend

import terminalio
from adafruit_display_text import label

from rainbowio import colorwheel
import board
import displayio
import gc

import json
import time

# imports consts for configuration
from config_consts import *
from macrocontroller import MacroControlConfiguration, MacroController, Event, EventSource
#import grid_numbers
from colors import COLORS
from midi_notes import MIDI_NOTES
import rgb_multiply
from bmp_meters import MidiMeterBmp
print(f"Booting: {gc.mem_free()=}")

# const in config file
MIDI_CONFIG_JSON = "midi_controller_config.json"
with open(MIDI_CONFIG_JSON) as conf_file:
	conf = json.load(conf_file)
	macrocontroller_config = conf['controller']

control_config = MacroControlConfiguration(macrocontroller_config)

print(control_config.page)
# for conf in control_config.page:
# 	for control,cfg in conf:
# 		print(control)

macrocontroller = MacroController(macrocontroller_config)
# for c in macrocontroller.controls:
# 	print(f"{c=}, {c.send()=}")
# print(len(macrocontroller.event_queue))
# print(macrocontroller.events_in_queue)
event_queue = macrocontroller.event_queue

display = board.DISPLAY

MACROPAD_FRAME_TIME = 1.0/MACROPAD_DISPLAY_FPS
# hard capped at 40 for memory limitations, and it's too ridiculous to go wider
MAX_METER_WIDTH = min(int((display.width-(DISPLAY_METER_COUNT*DISPLAY_METER_SPACING))/DISPLAY_METER_COUNT), 40)
# let's not go too overboard
DISPLAY_METER_WIDTH = DISPLAY_METER_WIDTH if DISPLAY_METER_WIDTH < MAX_METER_WIDTH else MAX_METER_WIDTH
DISPLAY_METER_WIDTH_SPACE = DISPLAY_METER_WIDTH+DISPLAY_METER_SPACING
DISPLAY_METER_HEIGHT = min(DISPLAY_METER_HEIGHT, display.height)
#
# end display meter configuration
#


macropad_sleep_keys = False

# all of these could easily be part of a MacroPad-object
# need better name for said class, and consideration of name to describe it, but not be "MacroPad"
# controls need to identify type (keys, encoder, display and have keys and possibly positions
# decouple screen cc from key cc?

# these consts are used to place meters for these as they lack a 'key'
ENC_CLICK_METER_POSITION = 12
ENCODER_METER_POSITION = 13
midi_keys = list()
midi_encoder = None
midi_encoder_click = None
# create lookup dictionary for looking up associated key with cc, mainly for lighting keys
# can probably be done smarter, but this is convenient
midi_cc_lookup = dict()

#
# page setup, should be read from config and be entirely dynamic based on config
#
MACRO_PAD_DEFAULT_PAGE = "1"
MODES = ["Transport","Volume"]

# bunch of loose ideas on how to handle..stuff
MACROPAD_CONTROLS = ["Key 1", "Key 2", "Key 3",
					"Key 4", "Key 5", "Key 6",
					"Key 7", "Key 8", "Key 9",
					"Key 10", "Key 11", "Key 12",
					"Enc_Click", "Encoder"]



class MidiConfig:
	"""Will be deprecated after MacroController is done, as it replaces this entirely"""
	def __init__(self, config):
		self.cc = config["cc"]
		self.key_no = config["key_no"]
		self.key = config["key_no"]-1
		self.description = config["description"]
		self.on_color = COLORS.get(config["on_color"],int(config.get("on_color_hex",0xFF0000)))
		self.off_color = COLORS.get(config["off_color"],int(config.get("off_color_hex",0xFFFFFF)))
		self.max_value = config["max_value"]
		self.min_value = config["min_value"]
		self.toggle = config["toggle"]
		self.current_value = config["max_value"] if int(config["toggle"]) in [1,2] else config["min_value"]
		self.prev_value = config["min_value"] if int(config["toggle"]) == 2 else config["max_value"]
		self.prev_time = 0
	def __repr__(self):
		return (f"({self.description}: cc={self.cc}, value={self.current_value}, prev_value={self.prev_value}, toggle={self.toggle})")
	def __str__(self):
			return (f"({self.description}: cc={self.cc}, value={self.current_value}, prev_value={self.prev_value}, toggle={self.toggle})")
	def msg(self,value=None, cc_offset=0):
		if(value is None):
			value = self.current_value
		else:
			self.current_value = value

		if(self.current_value>self.max_value):
			self.current_value = self.max_value
		if(self.current_value<self.min_value):
			self.current_value = self.min_value
		return_value = self.current_value

		return ControlChange(self.cc+cc_offset,return_value)


def load_config(conf, midi_keys,midi_cc_lookup, page=MACRO_PAD_DEFAULT_PAGE):
	"""load json-configuration into appropriate objects"""
	midi_keys.clear()
	midi_cc_lookup.clear()
	for k in range(0,12):
		midi_keys.append(MidiConfig(conf['controller'][str(page)][str(k+1)]))
	for k in midi_keys:
		midi_cc_lookup[k.cc] = k.key
	if(DEBUG_OUTPUT):
		for k in midi_keys:
			print(k)

midi_encoder = MidiConfig(conf['controller'][MACRO_PAD_DEFAULT_PAGE]['enc'])
midi_encoder_click = MidiConfig(conf['controller'][MACRO_PAD_DEFAULT_PAGE]['enc_click'])

load_config(conf,midi_keys,midi_cc_lookup,MACRO_PAD_DEFAULT_PAGE)

macropad = macrocontroller.macropad



macropad_mode = int(MACRO_PAD_DEFAULT_PAGE)

#read init position, for deltas
last_knob_pos = macropad.encoder  # store knob position state

loop_start_time = time.monotonic()
last_run_time = time.monotonic()
loop_last_action = time.monotonic()
prev_gfx_update = time.monotonic()

# init colors from setup
def init_key_colors():
	"""init key colors to their off_color"""
	for k in midi_keys:
		macropad.pixels[k.key] = k.off_color
def init_display_meters():
	"""init display meters to zero"""
	for i in range(0,DISPLAY_METER_COUNT):
		event_queue[i] = (0,EventSource.INIT_METERS_EVENT)

bitmap = displayio.Bitmap(display.width, display.height,2)
palette = displayio.Palette(2)
palette[0] = 0x000000
palette[1] = 0xFFFFFF

# midi_meter contains a meter containing 128 bmps with various levels
midi_meter = MidiMeterBmp(DISPLAY_METER_WIDTH,DISPLAY_METER_HEIGHT,2)


# palette swap possible? 
black_palette = displayio.Palette(2)
black_palette[0] = 0x000000
black_palette[1] = 0x000000

tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
group = displayio.Group()
group.append(tile_grid)
display.show(group)

print(f"{display.width=},{display.height=}")
display.rotation = 0

#clear midi buffer before starting
while (macropad.midi.receive() is not None):
	pass

init_key_colors()


# # Set text, font, and color
# text = "HELLO WORLD"
# font = terminalio.FONT
# color = 0x0000FF

# # Create the text label
# text_area = label.Label(font, text=text, color=color)

# # Set the location
# text_area.x = 100
# text_area.y = 80

# # Show it
# #display.show(text_area)
# print(type(text_area))

macropad.display.refresh()

gc.collect()

print(f"Starting loop: {gc.mem_free()=}")

################################################################
# START OF MAIN LOOP
################################################################
while True:
	# keep track of time when loop started
	loop_start_time = time.monotonic()
	################################################################
	# START OF MIDI RECEIVE
	################################################################
	# read whatever the next midi message is
	midi_event = macropad.midi.receive()
	# returns None when buffer is empty
	if midi_event is not None:
		#loop_last_action = time.monotonic()
		# handle NoteOn
		if isinstance(midi_event, NoteOn):
			macropad.stop_tone()
			if(midi_event.velocity>0):
				pitch = float(MIDI_NOTES[midi_event.note][2])
				macropad.start_tone(pitch)
				macropad.pixels.fill(colorwheel((midi_event.note+midi_event.velocity-40)%100))
		# handle NoteOff
		if isinstance(midi_event, NoteOff):
				macropad.stop_tone()
		# handle CC
		if(isinstance(midi_event, ControlChange)):
			# Using sets to keep track of our cc's will be safer/faster (here)
			# Similarly sets for key 'list'?

			# Encoder CC 
			if midi_event.control == midi_encoder.cc:
				event_queue[ENCODER_METER_POSITION+1000] = (midi_event.value,EventSource.ENC_MIDI_EVENT)
				#midi_encoder.current_value = midi_event.value
			# Encoder click CC
			if midi_event.control == midi_encoder_click.cc:
				event_queue[ENC_CLICK_METER_POSITION+1000] = (midi_event.value,EventSource.ENC_CLICK_MIDI_EVENT)
				#midi_encoder_click.current_value = midi_event.value
			# Keys CC
			if midi_event.control in (k.cc for k in midi_keys ):
				event_queue[midi_event.control] = (midi_event.value,EventSource.MIDI_KEY_EVENT)
			control = macrocontroller.control(midi_event.control)
			if(control is not None):
				print(macrocontroller.controls[control].receive())
	################################################################
	# END OF MIDI RECEIVE
	################################################################

	################################################################
	# START KEYPAD EVENT HANDLER
	################################################################
	while macropad.keys.events:  # check for key press or release
		#loop_last_action = time.monotonic()
		key_event = macropad.keys.events.get()
		if key_event:
			key = key_event.key_number
			if key_event.pressed:
				#key = key_event.key_number
				if(midi_keys[key].toggle == 1):
					event_queue[midi_keys[key].cc] = (midi_keys[key].max_value if midi_keys[key].current_value == midi_keys[key].min_value else midi_keys[key].min_value,EventSource.KEY_EVENT)
					macropad.midi.send(midi_keys[key].msg())
				else:
					event_queue[midi_keys[key].cc] = (midi_keys[key].max_value,EventSource.KEY_EVENT)
					macropad.midi.send(midi_keys[key].msg(midi_keys[key].max_value))
			if key_event.released:
				#key = key_event.key_number
				if(midi_keys[key].toggle == 2):
					macropad.midi.send(midi_keys[key].msg(midi_keys[key].min_value))
					event_queue[midi_keys[key].cc] = (midi_keys[key].min_value,EventSource.KEY_EVENT)
			print(macrocontroller.controls[key].send())
			
	################################################################
	# END KEYPAD EVENT HANDLER
	################################################################

	################################################################
	# START ENCODER EVENT HANDLER
	################################################################
	macropad.encoder_switch_debounced.update()  # check the knob switch for press or release
	if macropad.encoder_switch_debounced.pressed:
		print(macrocontroller.controls[ENCODER_CLICK_ID].send())
		macropad.midi.send(midi_encoder_click.msg(midi_encoder_click.current_value,cc_offset=macropad_mode-1))
		macropad_mode = macropad_mode%len(MODES)+1

		macropad.red_led = macropad.encoder_switch
		
		load_config(conf,midi_keys,midi_cc_lookup,macropad_mode)
		init_key_colors()
		init_display_meters()
		event_queue[ENC_CLICK_METER_POSITION+1000] = (127,EventSource.ENC_CLICK_EVENT)

	if macropad.encoder_switch_debounced.released:
		print(macrocontroller.controls[ENCODER_CLICK_ID].send())
		macropad.red_led = macropad.encoder_switch
		event_queue[ENC_CLICK_METER_POSITION+1000] = (0,EventSource.ENC_CLICK_EVENT)

	if last_knob_pos is not macropad.encoder:  # knob has been turned
		prev_midi = midi_encoder.current_value
		knob_pos = macropad.encoder  # read encoder
		knob_delta = knob_pos - last_knob_pos  # compute knob_delta since last read
		last_knob_pos = knob_pos  # save new reading

		if(midi_encoder.current_value + knob_delta == midi_encoder.current_value):
			pass
		else:
			midi_encoder.current_value += knob_delta
			if(midi_encoder.current_value>127):
				midi_encoder.current_value = 127
			elif(midi_encoder.current_value<0):
				midi_encoder.current_value = 0
			# only send midi if current value is changed
			if(midi_encoder.current_value != prev_midi):
				macropad.midi.send(midi_encoder.msg(midi_encoder.current_value))
		last_knob_pos = macropad.encoder
		print(macrocontroller.controls[ENCODER_ID].send())
		#print(prev_midi,midi_encoder.current_value,midi_meter.meter_value[prev_midi],midi_meter.meter_value[midi_encoder.current_value])
		if(prev_midi == midi_encoder.current_value or midi_meter.meter_value[prev_midi] == midi_meter.meter_value[midi_encoder.current_value]):
			#print("skip draw")
			pass
		else:
			#print("draw")
			event_queue[ENCODER_METER_POSITION+1000] = (midi_encoder.current_value,EventSource.ENC_EVENT)
	################################################################
	# END ENCODER EVENT HANDLER
	################################################################

	# draw screen and update key colors
	if(time.monotonic()-prev_gfx_update > MACROPAD_FRAME_TIME and MACROPAD_DISPLAY_METERS and macrocontroller.events_in_queue):
		# draw queued messages
		loop_last_action = time.monotonic()

		for k,t in event_queue.items():
			v,source = t
			# refactor this to unify common elements

			# keypad event, midi key event
			if(source in [EventSource.KEY_EVENT,EventSource.MIDI_KEY_EVENT]):
				key = midi_cc_lookup[k]
				midi_keys[key].current_value = v
				if(midi_keys[key].toggle == 1 and source == EventSource.KEY_EVENT):
					v = midi_keys[key].max_value if midi_keys[key].current_value == midi_keys[key].min_value else midi_keys[key].min_value
				if(midi_keys[key].toggle == 1 and source == EventSource.MIDI_KEY_EVENT):
					midi_keys[key].current_value = midi_keys[key].max_value if midi_keys[key].current_value == midi_keys[key].min_value else midi_keys[key].min_value

				bitmap.blit(key*DISPLAY_METER_WIDTH_SPACE+DISPLAY_METER_SPACING,0,midi_meter.midi_value[v])
				event_color = midi_keys[key].off_color if v == 0 else rgb_multiply.rgb_mult(midi_keys[key].on_color, v*1.0/127.0)
				macropad.pixels[key] = event_color

			# encoder event, midi encoder event
			elif(source in [EventSource.ENC_EVENT,EventSource.ENC_MIDI_EVENT]):
				midi_encoder.current_value = v
				bitmap.blit(ENCODER_METER_POSITION*DISPLAY_METER_WIDTH_SPACE+DISPLAY_METER_SPACING,0,midi_meter.midi_value[v])
			# enc click event, midi enc click event
			elif(source in [EventSource.ENC_CLICK_EVENT,EventSource.ENC_CLICK_MIDI_EVENT]):
				midi_encoder_click.current_value = v
				bitmap.blit(ENC_CLICK_METER_POSITION*DISPLAY_METER_WIDTH_SPACE+DISPLAY_METER_SPACING,0,midi_meter.midi_value[v])
			# reset meters
			elif(source in [EventSource.INIT_METERS_EVENT]):
				for i in range(0,DISPLAY_METER_COUNT):
					bitmap.blit(i*DISPLAY_METER_WIDTH_SPACE+DISPLAY_METER_SPACING,0,midi_meter.midi_value[v])
		# clear queue 
		prev_gfx_update = time.monotonic()
		event_queue.clear()
		macropad.display.refresh()

	# screen saver
	if(loop_start_time-loop_last_action>MACROPAD_SLEEP_KEYS):
		macropad.pixels.brightness = 0
		macropad_sleep_keys = True
		group.hidden = 1
		macropad.display.refresh()

	elif(macropad_sleep_keys and loop_start_time-loop_last_action<MACROPAD_SLEEP_KEYS):
		macropad.pixels.brightness = MACROPAD_BRIGHTNESS
		macropad_sleep_keys = False
		group.hidden = 0
		macropad.display.refresh()
################################################################
# END MAIN LOOP
################################################################