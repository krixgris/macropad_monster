# code.py
from adafruit_macropad import MacroPad
from adafruit_midi.control_change import ControlChange
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.pitch_bend import PitchBend

import terminalio
from adafruit_display_text import label

import random

from rainbowio import colorwheel
import board
import displayio
import gc

import json
import time

# imports consts for configuration
from config_consts import *

from macrocontroller import EVENT_TYPES, EncoderClickControl, EncoderControl, KeyControl, MacroController, ControlMessage
from macrocontroller import EVENTS
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

macrocontroller = MacroController(macrocontroller_config)

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


#
# page setup, should be read from config and be entirely dynamic based on config
#
MACRO_PAD_DEFAULT_PAGE = "1"
# MODES = ["Transport","Volume"]

# def load_config(conf, midi_keys,midi_cc_lookup, page=MACRO_PAD_DEFAULT_PAGE):
def load_config(page=MACRO_PAD_DEFAULT_PAGE):
	"""depr mostly. remove and just call init page conf."""
	page_index = int(page)-1
	macrocontroller.init_page_config(page_index)

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
	for k in KEYS:
		macropad.pixels[k] = macrocontroller.controls[k].off_color
def init_display_meters():
	"""init display meters to zero"""
	for i in range(0,DISPLAY_METER_COUNT):
		event_queue[i] = (0,EVENTS.INIT_MTR)

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
		if(isinstance(midi_event, ControlChange) and midi_event.control in macrocontroller.defined_cc):
			control = macrocontroller.controls[macrocontroller.control(midi_event.control)]
			msg = None
			event_type = EVENTS.DEFAULT

			# Encoder CC 
			if(isinstance(control, EncoderControl)):
				event_type = EVENTS.MIDI_ENCODER_TURN
				msg = control.receive(midi_event.value, event_type=event_type)
			# Encoder click CC
			if(isinstance(control, EncoderClickControl)):
				event_type = EVENTS.MIDI_ENCLICK
			# Keys CC
			
			if(isinstance(control, KeyControl)):
				event_type = EVENTS.MIDI_KEY_PRESS
				msg = control.receive(midi_event.value, event_type=event_type)
			#print(control.delta_time_prev_queued)
			# performance testing by throttling here instead of in queue
			if(msg is not None and control.delta_time_prev_queued>MACROPAD_FRAME_TIME*4):
				event_queue[control.id] = (msg.value,msg.event_type)

	################################################################
	# END OF MIDI RECEIVE
	################################################################

	################################################################
	# START KEYPAD EVENT HANDLER
	################################################################
	while macropad.keys.events:  # check for key press or release
		key_event = macropad.keys.events.get()
		if key_event:
			key = key_event.key_number
			control = macrocontroller.controls[key]
			event_type = EVENTS.DEFAULT
			if key_event.pressed:
				event_type = EVENTS.KEY_PRESS
			if key_event.released:
				event_type = EVENTS.KEY_RELEASE
			msg = control.send(event_type=event_type)
			if(msg is not None):
				event_queue[control.id] = (msg.value,msg.event_type)
				macropad.midi.send(ControlChange(msg.control, msg.value))
	################################################################
	# END KEYPAD EVENT HANDLER
	################################################################

	################################################################
	# START ENCODER EVENT HANDLER
	################################################################
	macropad.encoder_switch_debounced.update()  # check the knob switch for press or release
	event_type = EVENTS.DEFAULT
	enc_click_event = False
	if macropad.encoder_switch_debounced.pressed:
		enc_click_event = True
		event_type = EVENTS.ENCLICK_PRESS
		macropad_mode = macropad_mode%macrocontroller.page_count+1

		macropad.red_led = macropad.encoder_switch
		macrocontroller.init_page_config(macropad_mode-1)
		init_key_colors()
		init_display_meters()

	if macropad.encoder_switch_debounced.released:
		enc_click_event = True
		event_type = EVENTS.ENCLICK_RELEASE
		macropad.red_led = macropad.encoder_switch
	if(enc_click_event):
		control = macrocontroller.controls[ENCODER_CLICK_ID]
		msg = control.send(event_type=event_type)
		if(msg is not None):
			event_queue[control.id] = (msg.value,msg.event_type)
			macropad.midi.send(ControlChange(msg.control, msg.value))


	if last_knob_pos is not macropad.encoder:  # knob has been turned
		macro_encoder = macrocontroller.controls[ENCODER_ID]
		control = macrocontroller.controls[ENCODER_ID]
		prev_midi = macro_encoder.value
		knob_pos = macropad.encoder  # read encoder
		knob_delta = knob_pos - last_knob_pos  # compute knob_delta since last read
		last_knob_pos = knob_pos  # save new reading

		if(macro_encoder.value + knob_delta == macro_encoder.value):
			pass
		else:
			macro_encoder.value += knob_delta
			if(macro_encoder.value != prev_midi):
				pass
		last_knob_pos = macropad.encoder
		msg = macro_encoder.send(value = macro_encoder.value, event_type=EVENTS.ENCODER_TURN)
		if(msg is not None):
			event_queue[control.id] = (msg.value,msg.event_type)
			macropad.midi.send(ControlChange(msg.control, msg.value))

	################################################################
	# END ENCODER EVENT HANDLER
	################################################################

	# draw screen and update key colors
	if(event_queue and time.monotonic()-prev_gfx_update > MACROPAD_FRAME_TIME and MACROPAD_DISPLAY_METERS):
		# draw queued messages
		loop_last_action = time.monotonic()
		event_keys = [k for k in event_queue.keys()]
		# if MAX_EVENT_QUEUE>len(event_keys) do the random logic, otherwise don't
		double_list = event_keys + event_keys
		rpos = random.randint(0,len(event_keys)-1)
		event_keys = double_list[rpos:rpos+len(event_keys)]
		meter_update = True

		for i in range(0,min(MAX_EVENT_QUEUE,len(event_keys))):
			control_id = event_keys.pop()
			tuple_ = event_queue.pop(control_id)
			v,source = tuple_
			# refactor this to unify common elements
			# performance: ensure value of meters is changed before blitting unnecessarily
			control = macrocontroller.controls[control_id]
			if(midi_meter.meter_value[v] == midi_meter.meter_value[control.prev_queued_value]):
				meter_update = False
			# keypad event, midi key event
			if(source in EVENT_TYPES.KEY_EVENTS):
				if(meter_update):
					bitmap.blit(control_id*DISPLAY_METER_WIDTH_SPACE+DISPLAY_METER_SPACING,0,midi_meter.midi_value[v])
					event_color = control.off_color if v == 0 else rgb_multiply.rgb_mult(control.on_color, v*1.0/127.0)
					macropad.pixels[control_id] = event_color

			# encoder event, midi encoder event
			elif(source in EVENT_TYPES.ENCODER_EVENTS):
				if(meter_update):
					bitmap.blit(control_id*DISPLAY_METER_WIDTH_SPACE+DISPLAY_METER_SPACING,0,midi_meter.midi_value[v])
			# enc click event, midi enc click event
			elif(source in EVENT_TYPES.ENCODER_CLICK_EVENTS):
				if(meter_update):
					bitmap.blit(control_id*DISPLAY_METER_WIDTH_SPACE+DISPLAY_METER_SPACING,0,midi_meter.midi_value[v])
			# reset meters
			elif(source in [EVENTS.INIT_MTR]):
				for i in range(0,DISPLAY_METER_COUNT):
					# if(meter_update):
					bitmap.blit(i*DISPLAY_METER_WIDTH_SPACE+DISPLAY_METER_SPACING,0,midi_meter.midi_value[v])
		# clear queue 
		prev_gfx_update = time.monotonic()
		# this can update all blitting since they are now all the same..
		if(meter_update):
			control.prev_queued_value = control.value
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