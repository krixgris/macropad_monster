# code.py
from adafruit_macropad import MacroPad
from adafruit_midi.control_change import ControlChange
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.pitch_bend import PitchBend

import terminalio
from adafruit_display_text import label
from adafruit_seesaw import seesaw, rotaryio, digitalio, neopixel

import random

from rainbowio import colorwheel
import board
import displayio
import gc
# import neopixel

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

external_encoder = True

seesaw = seesaw.Seesaw(board.I2C(), addr=0x36)

seesaw_product = (seesaw.get_version() >> 16) & 0xFFFF
print("Found product {}".format(seesaw_product))
if seesaw_product != 4991:
	print("Wrong firmware loaded?  Expected 4991")
	external_encoder = False

seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
ext_encoder_button = digitalio.DigitalIO(seesaw, 24)
ext_encoder_button_held = False

ext_encoder = rotaryio.IncrementalEncoder(seesaw)
ext_last_position = None

ext_pixel = neopixel.NeoPixel(seesaw, 6, 1)
ext_pixel.brightness = 0.5



# def color_brightness(value):
# 	return rgb_multiply.rgb_mult(0xFF000F, value*1.0/127.0)

# all_reds = list(map(color_brightness, range(0,128)))

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
# def load_config(page=MACRO_PAD_DEFAULT_PAGE):
# 	"""depr mostly. remove and just call init page conf."""
# 	page_index = int(page)-1
# 	macrocontroller.init_page_config(page_index)

macropad = macrocontroller.macropad

#pixels = neopixel.NeoPixel()


# this needs to be done nicer..
macropad_mode = int(MACRO_PAD_DEFAULT_PAGE)

macrocontroller.init_page_config(0)

#read init position, for deltas
last_knob_pos = macropad.encoder  # store knob position state

loop_start_time = time.monotonic()
last_run_time = time.monotonic()
loop_last_action = time.monotonic()
prev_gfx_update = time.monotonic()

# init colors from setup
def init_key_colors():
	"""init key colors to their off_color"""
	pass
	# event_color = control.off_color if v == 0 else rgb_multiply.rgb_mult(control.on_color, v*1.0/127.0)
	# macropad.pixels[control_id] = event_color
	# for k in KEYS:
	# 	macropad.pixels[k] = macrocontroller.controls[k].off_color
def init_display_meters():
	"""init display meters to zero"""
	#for i in range(0,DISPLAY_METER_COUNT):
	for control in macrocontroller.controls:
		# momentary values reset to their min_values
		# need to handle prev values in values ?
		if(control.toggle == False):
			control.value = control.min_value
			# #control._prev_value = control.max_value
			control.prev_queued_value = control.min_value

			# control.send(0, EVENTS.KEY_PRESS)
			# control.send(0, EVENTS.KEY_PRESS)
			# print(control)
			# pass
			
		if(isinstance(control, KeyControl)):
			macropad.pixels[control.id] = control.off_color if control.value == 0 else rgb_multiply.rgb_mult(control.on_color, control.value*1.0/127.0)
		bitmap.blit(control.id*DISPLAY_METER_WIDTH_SPACE+DISPLAY_METER_SPACING,0,midi_meter.midi_value[control.value])
		macropad.pixels.show()
		macropad.display.refresh()
	pass
	# for control in macrocontroller.controls:
	# 	event_queue[control.id] = (control.value,EVENTS.INIT_MTR)

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

#init_key_colors()
init_display_meters()

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
				# print(control.id, control.value, control.prev_value, control.prev_queued_value)
				msg = control.receive(midi_event.value, event_type=event_type)
				# print(control.id, control.value, control.prev_value, control.prev_queued_value)
			#print(control.delta_time_prev_queued)
			# performance testing by throttling here instead of in queue
			# this needs an 'are we in sync?' thing, or a pageswap=True (easier)
			if(msg is not None and (True or control.delta_time_prev_queued>MACROPAD_FRAME_TIME*4)):
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
		for control in macrocontroller.controls:
			if(control.momentary):
				if(isinstance(control,KeyControl)):
					release_event = EVENTS.KEY_RELEASE
					release_msg = control.send(event_type=release_event)
					if(release_msg is not None):
						macropad.midi.send(ControlChange(release_msg.control, release_msg.value))
		macrocontroller.init_page_config(macropad_mode-1)
		#init_key_colors()
		
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
		if(0.100<control.delta_time_pre_change<=0.200):
			# print("speed 2")
			knob_delta = knob_delta * 2
		elif(0.0500<control.delta_time_pre_change<=0.100):
			# print("speed 3")
			knob_delta = knob_delta * 3
		elif(0.0250<control.delta_time_pre_change<=0.0500):
			# print("speed 4")
			knob_delta = knob_delta * 4
		elif(control.delta_time_pre_change<=0.0250):
			# print("speed 5")
			knob_delta = knob_delta * 5

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

	################################################################
	# EXTERNAL ENCODER EVENT HANDLER
	################################################################
	ext_position = ext_encoder.position

	if ext_position != ext_last_position:
		ext_last_position = ext_position
		ext_color = rgb_multiply.rgb_mult(COLORS["purple"], abs(ext_position)%255/255.0)
		ext_pixel.fill(ext_color)
		print("Position: {}".format(abs(ext_position)%255))


	if not ext_encoder_button.value and not ext_encoder_button_held:
		ext_encoder_button_held = True
		print("Button pressed")

	if ext_encoder_button.value and ext_encoder_button_held:
		ext_encoder_button_held = False
		print("Button released")

	################################################################
	# END EXTERNAL ENCODER EVENT HANDLER
	################################################################


	# draw screen and update key colors
	if(event_queue and time.monotonic()-prev_gfx_update > MACROPAD_FRAME_TIME):
		#print(event_queue)
		# draw queued messages
		loop_last_action = time.monotonic()
		event_keys = [k for k in event_queue.keys()]
		# if MAX_EVENT_QUEUE>len(event_keys) do the random logic, otherwise don't
		double_list = event_keys + event_keys
		rpos = random.randint(0,len(event_keys)-1)
		event_keys = double_list[rpos:rpos+len(event_keys)]
		meter_update = True
		
		for i in range(0,min(MAX_EVENT_QUEUE,len(event_keys))):
			meter_update = True
			control_id = event_keys.pop()
			tuple_ = event_queue.pop(control_id)
			v,source = tuple_
			# refactor this to unify common elements
			# performance: ensure value of meters is changed before blitting unnecessarily
			control = macrocontroller.controls[control_id]
			# print(control.cc, control.value, control.prev_value, control.prev_queued_value)
			# print(f"{midi_meter.meter_value[v]=} {midi_meter.meter_value[control.prev_queued_value]=}")
			if(midi_meter.meter_value[v] == midi_meter.meter_value[control.prev_queued_value]):
				#print("no need to update meter")
				meter_update = False

			# keypad event, midi key event
			if(source in EVENT_TYPES.KEY_EVENTS):
				if(meter_update):
					bitmap.blit(control_id*DISPLAY_METER_WIDTH_SPACE+DISPLAY_METER_SPACING,0,midi_meter.midi_value[v])
					event_color = control.off_color if v == 0 else rgb_multiply.rgb_mult(control.on_color, v*1.0/127.0)
					# event_color = control.off_color if v == 0 else control.on_colors[v]
					# event_color = control.off_color if v == 0 else all_reds[v]
					
					# event_color = control.off_color if v < 60 else control.on_color
					# event_color = 0x0FF00C
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
					# bitmap.blit(i*DISPLAY_METER_WIDTH_SPACE+DISPLAY_METER_SPACING,0,midi_meter.midi_value[v])
					bitmap.blit(control_id*DISPLAY_METER_WIDTH_SPACE+DISPLAY_METER_SPACING,0,midi_meter.midi_value[v])
			if(meter_update):
				control.prev_queued_value = control.value
		# clear queue 
		prev_gfx_update = time.monotonic()
		# this can update all blitting since they are now all the same..
		macropad.display.refresh()
		macropad.pixels.show()

	# screen saver
	if(loop_start_time-loop_last_action>MACROPAD_SLEEP_KEYS):
		macropad.pixels.brightness = 0
		macropad_sleep_keys = True
		group.hidden = 1
		macropad.display.refresh()
		macropad.pixels.show()

	elif(macropad_sleep_keys and loop_start_time-loop_last_action<MACROPAD_SLEEP_KEYS):
		macropad.pixels.brightness = MACROPAD_BRIGHTNESS
		macropad_sleep_keys = False
		group.hidden = 0
		macropad.display.refresh()
		macropad.pixels.show()
################################################################
# END MAIN LOOP
################################################################