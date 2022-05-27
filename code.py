# code.py
from adafruit_macropad import MacroPad
from adafruit_midi.midi_message import note_parser
from adafruit_midi.control_change import ControlChange
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.pitch_bend import PitchBend
from rainbowio import colorwheel
import board
import displayio

import json
import time
import random

import grid_numbers
from colors import COLORS
from midi_notes import MIDI_NOTES
import rgb_multiply

#import bmp_meters



MACROPAD_BRIGHTNESS = 0.15
MACROPAD_SLEEP_KEYS = 60.0

MACROPAD_DISPLAY_FPS = 30.0
MACROPAD_FRAME_TIME = 1.0/MACROPAD_DISPLAY_FPS

macropad_sleep_keys = False

MACRO_PAD_DEFAULT_PAGE = "1"
MODES = ["Transport","Volume"]

class Display:
	def __init__(self):
		self.rows = ["",
					"",
					"",
					""]

#
# Name change + move it out to separate py-file + rethink some functionality to be more general and also use for normal keypresses?
# Should be able to be a generic handler of the macropad perhaps..
class MidiConfig:
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
		self.current_value = 0
	def __repr__(self):
		return (f"({self.description}: cc={self.cc}, max={self.max_value}, min={self.min_value})")
	def str(self):
			return (f"({self.description}: cc={self.cc}, max={self.max_value}, min={self.min_value})")
	def msg(self,value=None, cc_offset=0):
		if(value is None):
			value = self.current_value
		else:
			self.current_value = value
		if(self.toggle==1):
			self.current_value = 127 if value == 0 else 0
		if(self.current_value>self.max_value):
			self.current_value = self.max_value
		if(self.current_value<self.min_value):
			self.current_value = self.min_value
		return_value = self.current_value
		return ControlChange(self.cc+cc_offset,return_value)

# depr. all of this should exist in the class containing all midi config
class MacroPadMidi:
	keys = list()
	def __init__(self):
		for k in range(0,12):
			self.keys.append(127)
		self.encoder = 0
		self.encoder_click = 127
	
	def __repr__(self):
		return f"keys={self.keys}, encoder={self.encoder}, enc_click={self.encoder_click}"

midi_keys = list()
midi_encoder = None
midi_encoder_click = None

#midi_key_pages = dict()

# depr
def load_midi_config(midi_list, config_list):
	for c in config_list:
		midi_list.append(MidiConfig(c))

def load_config(conf, midi_keys,midi_cc_lookup, page=MACRO_PAD_DEFAULT_PAGE):
	# load json-configuration into appropriate objects
	#midi_key_pages[page] = midi_keys
	midi_keys.clear()
	midi_cc_lookup.clear()
	for k in range(0,12):
		midi_keys.append(MidiConfig(conf['controller'][str(page)][str(k+1)]))
	for k in midi_keys:
		midi_cc_lookup[k.cc] = k.key
	# print(f"{midi_keys=}")
	# print(f"{midi_cc_lookup=}")

def set_screen(macropad,text_lines,display_rows):
	text_lines = macropad.display_text(display_rows.rows[0])
	macropad.display_text(display_rows.rows[0])
	for l in range(0,3):
		text_lines[l].text = display_rows.rows[l+1]
	text_lines.show()



# these can and should all be replaced by the midi_keys, midi_encoder, midi_encoder_click
pad_midi_values = MacroPadMidi()

MIDI_CONFIG_JSON = "midi_controller_config.json"
conf_file = open(MIDI_CONFIG_JSON)
conf = json.load(conf_file)
conf_file.close()



midi_encoder = MidiConfig(conf['controller'][MACRO_PAD_DEFAULT_PAGE]['enc'])
midi_encoder_click = MidiConfig(conf['controller'][MACRO_PAD_DEFAULT_PAGE]['enc_click'])

# create lookup dictionary for looking up associated key with cc, mainly for lighting keys
# can probably be done smarter, but this is convenient

midi_cc_lookup = dict()

load_config(conf,midi_keys,midi_cc_lookup,MACRO_PAD_DEFAULT_PAGE)

# depr. used to keep track of how long time things take, initial idea was to build a task list to run asynchronous
start_time = time.monotonic()

macropad = MacroPad(rotation=0)  # create the macropad object, rotate orientation
macropad.display.auto_refresh = False

# --- Pixel setup --- #
#depr
key_color = colorwheel(130)  # fill with cyan to start

macropad.pixels.brightness = MACROPAD_BRIGHTNESS


macropad_mode = int(MACRO_PAD_DEFAULT_PAGE)

#depr
# --- MIDI variables ---
mode = 0
midi_values = [0, 16, 8]  # bank, cc value, pitch

#depr..
# Chromatic scale starting with C3 as bottom left keyswitch (or use any notes you like)
midi_notes = [
            57, 58, 59,
            54, 55, 56,
            51, 52, 53,
            48, 49, 50
            ]
#depr
key_colors = [
            20, 30, 40,
            50, 60, 70,
            80, 90, 100,
            110, 120, 130
            ]

key_numbers = [
            0, 1, 2,
            3, 4, 5,
            6, 7, 8,
            9, 10, 11
            ]

blank_display = Display()
display_rows = Display()
display_rows.rows[0] = "Macropad Cubase"
display_rows.rows[1] = f"{MODES[macropad_mode-1]}"
display_rows.rows[2] = ""
display_rows.rows[3] = "Last Row"

# --- Display text setup ---
#text_lines = macropad.display_text(display_rows.rows[0])
text_lines = macropad.display_text("")
# macropad.display_text(display_rows.rows[0])
# for l in range(0,3):
# 	text_lines[l].text = display_rows.rows[l+1]
text_lines.show()

set_screen(macropad, text_lines, display_rows)

#read init position, for deltas
last_knob_pos = macropad.encoder  # store knob position state

# variable used for nothing right now
sleep_time = 0.5

# variables set up with the idea to build task list
loop_start_time = time.monotonic()
last_run_time = time.monotonic()
loop_last_action = time.monotonic()
prev_gfx_update = time.monotonic()

# for fun, loops through numbers showing on the display and playing audio
def loop_numbers(iterations,reverse:bool = 0):
	for r in range(0,iterations):
		n = r%13
		grid_numbers.number(macropad,n,fg_color = random.randint(0,5), bg_color=120)
		time.sleep(0.2)

# init colors from setup
# separate file

def init_colors():
	for k in midi_keys:
		macropad.pixels[k.key] = k.off_color 

init_colors()


display = board.DISPLAY
bitmap = displayio.Bitmap(display.width, display.height,2)
bg_bmp = displayio.Bitmap(display.width, display.height,2)
blank_bmp = displayio.Bitmap(display.width, display.height,2)
palette = displayio.Palette(2)
palette[0] = 0x000000
palette[1] = 0xFFFFFF

meter_bmp = displayio.Bitmap(display.width, display.height,2)

black_palette = displayio.Palette(2)
black_palette[0] = 0x000000
black_palette[1] = 0x000000

tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)

group = displayio.Group()

group.append(tile_grid)

BMP_FULL_METER_1 = displayio.Bitmap(10,40,2)
BMP_FULL_METER_0 = displayio.Bitmap(10,40,2)

BMP_FULL_METER_0.fill(0)
BMP_FULL_METER_1.fill(1)

midi_counter = 0
direction = 1

# for x in range(0,10):
# 	for y in range(0,40):
# 		BMP_FULL_METER_0[x,y] = 0
# 		BMP_FULL_METER_1[x,y] = 1
		
#bitmap.blit(0,0,BMP_FULL_METER_1)

display.show(group)

print(f"{display.width=},{display.height=}")
display.rotation = 0

while True:
	# keep track of time when loop started
	loop_start_time = time.monotonic()
	
	#   Block for handling things asynchronous..kind of
	#
	# # condition to execute code if enough time has passed to simulate async instead of time.sleep
	# if(loop_start_time-last_run_time>sleep_time):
	# 	for k in key_numbers:
	# 		r = random.randint(1,4)
	# 		macropad.pixels[k] = colorwheel(key_colors[k])
	# 		key_colors[k] = (key_colors[k]+random.randint(1,10)%11+r)%555
	#   # must be set to keep track of the last time we ran task
	# 	last_run_time = time.monotonic()

	################################################################
	# START OF MIDI RECEIVE
	################################################################
	# read whatever the next midi message is
	midi_event = macropad.midi.receive()
	# if nothing is in the buffer, midi_event is always None
	if midi_event is not None:
		loop_last_action = time.monotonic()
		#macropad_sleep_keys = False
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
			# Encoder CC 
			if midi_event.control == midi_encoder.cc:
				pad_midi_values.encoder = midi_event.value
				midi_encoder.current_value = midi_event.value
				#print(midi_encoder.current_value)
				#
				# too slow code
				# needs a "drawing function, or whatever to queue up stuff"
				# meter_max = 40.0
				# midi_max = 127
				# my = meter_max/midi_max*midi_encoder.current_value
				# max_y = int(BMP_FULL_METER_1.height-my)
				# max_y = max(min(max_y,BMP_FULL_METER_1.height),0)
				# #print(max_y)
				# #
				# # no need to blit both, and only needed to blip the bitmap
				# meter_bmp.blit(0,max_y,BMP_FULL_METER_1,x1 = 0,y1 = max_y,x2 = BMP_FULL_METER_0.width, y2 = BMP_FULL_METER_1.height)
				# meter_bmp.blit(0,0,BMP_FULL_METER_0,x1 = 0,y1 = 0,x2 = BMP_FULL_METER_0.width, y2 = max_y)
				# bitmap.blit(0,0,meter_bmp)#,x1=0,y1=0, x2=20, y2=max_y)


				#last_knob_pos = macropad.encoder
				#macropad.pixels[0] = rgb_multiply.rgb_mult(0xFF00CF,midi_event.value*1.0/127.0)
				
			# Encoder click CC
			if midi_event.control == midi_encoder_click.cc:
				pad_midi_values.encoder_click = midi_event.value
				midi_encoder_click.current_value = midi_event.value
			# Keys CC
			if midi_event.control in (k.cc for k in midi_keys ):
				key = midi_cc_lookup[midi_event.control]
				pad_midi_values.keys[key] = midi_event.value
				midi_keys[key].current_value = midi_event.value
				key_on = True if midi_event.value > 0 else False
				event_color = rgb_multiply.rgb_mult(midi_keys[key].on_color, midi_event.value*1.0/127.0)
				event_color = event_color if key_on else midi_keys[key].off_color
				k_color = event_color
				macropad.pixels[key] = k_color
				#print(f"{midi_keys[key].cc=},{midi_keys[key].current_value=}")
	################################################################
	# END OF MIDI RECEIVE
	################################################################

	################################################################
	# START KEYPAD EVENT HANDLER
	################################################################
	while macropad.keys.events:  # check for key press or release
		loop_last_action = time.monotonic()
		#macropad_sleep_keys = False
		key_event = macropad.keys.events.get()

		if key_event:
			if key_event.pressed:
				key = key_event.key_number

				x = int(key*80/12.0%80)
				y = int(key*40/12.0%40)

				#bitmap.blit(0,0,bg_bmp)
				# bitmap[x,y] = 1
				# bg_bmp.blit(0,0,bitmap)
				# group.hidden = 0
				
				# print(f"{midi_keys=}")
				# macropad.midi.send(midi_keys[key].msg(pad_midi_values.keys[key]))
				if(midi_keys[key].toggle == 0):
					macropad.midi.send(midi_keys[key].msg(127))
				else:
					macropad.midi.send(midi_keys[key].msg())
				macropad.pixels[key] = midi_keys[key].on_color 
				#text_lines[1].text = "NoteOn:{}".format(midi_notes[key])

			if key_event.released:
				key = key_event.key_number

				# group.scale = 2
				# # group.hidden = 1
				# #bg_bmp = bitmap
				
				# bitmap.blit(0,0,blank_bmp)
				
				#black_palette

				if(midi_keys[key].toggle == 0):
					macropad.midi.send(midi_keys[key].msg(0))
					macropad.pixels[key] = midi_keys[key].off_color 
	################################################################
	# END KEYPAD EVENT HANDLER
	################################################################

	################################################################
	# START ENCODER EVENT HANDLER
	################################################################
	macropad.encoder_switch_debounced.update()  # check the knob switch for press or release
	if macropad.encoder_switch_debounced.pressed:
		loop_last_action = time.monotonic()
		#macropad_sleep_keys = False
		
		macropad.midi.send(midi_encoder_click.msg(midi_encoder_click.current_value,cc_offset=macropad_mode-1))
		macropad_mode = macropad_mode%len(MODES)+1

		macropad.red_led = macropad.encoder_switch
		#macropad_mode = 1 if macropad_mode == 2 else 2
		
		#text_lines[1].text = f"{MODES[macropad_mode-1]}"
		#text_lines.show()
		display_rows.rows[1] = f"{MODES[macropad_mode-1]}"
		set_screen(macropad,text_lines,display_rows)
		load_config(conf,midi_keys,midi_cc_lookup,macropad_mode)
		init_colors()

	if macropad.encoder_switch_debounced.released:
		loop_last_action = time.monotonic()
		#macropad_sleep_keys = False
		macropad.red_led = macropad.encoder_switch

	if last_knob_pos is not macropad.encoder:  # knob has been turned
		loop_last_action = time.monotonic()
		#macropad_sleep_keys = False

		knob_pos = macropad.encoder  # read encoder
		knob_delta = knob_pos - last_knob_pos  # compute knob_delta since last read
		last_knob_pos = knob_pos  # save new reading

		midi_value = last_knob_pos%128
		if(pad_midi_values.encoder == 0 and knob_delta<0):
			midi_value = 0
		elif(pad_midi_values.encoder == 127 and knob_delta>0):
			midi_value = 127
		else:
			if(pad_midi_values.encoder + knob_delta == pad_midi_values.encoder):
				pass
			else:
				pad_midi_values.encoder += knob_delta
				midi_encoder.current_value += knob_delta
				if(pad_midi_values.encoder>127):
					pad_midi_values.encoder = 127
					midi_encoder.current_value = 127
				elif(pad_midi_values.encoder<0):
					pad_midi_values.encoder = 0
					midi_encoder.current_value = 0
				macropad.midi.send(midi_encoder.msg(pad_midi_values.encoder))
		last_knob_pos = macropad.encoder

		#print(midi_encoder.current_value)
		#meter_bmp.blit(0,0,BMP_FULL_METER_0,0,0,0,midi_encoder.current_value)

		# midi_encoder.current_value holds current midi/controller value

		meter_max = 40.0
		midi_max = 127
		my = meter_max/midi_max*midi_encoder.current_value
		max_y = int(BMP_FULL_METER_1.height-my)
		max_y = max(min(max_y,BMP_FULL_METER_1.height),0)
		#print(max_y)
		#
		# no need to blit both, and only needed to blip the bitmap
		meter_bmp.blit(0,max_y,BMP_FULL_METER_1,x1 = 0,y1 = max_y,x2 = BMP_FULL_METER_0.width, y2 = BMP_FULL_METER_1.height)
		meter_bmp.blit(0,0,BMP_FULL_METER_0,x1 = 0,y1 = 0,x2 = BMP_FULL_METER_0.width, y2 = max_y)
		bitmap.blit(0,0,meter_bmp)#,x1=0,y1=0, x2=20, y2=max_y)
		#bitmap[20,max_y] = 1


	################################################################
	# END ENCODER EVENT HANDLER
	################################################################
	
	# time.sleep(0.0001)
	
	# if(midi_counter <= 0):
	# 	direction = 2
	# if(midi_counter >=126):
	# 	direction = -2
	# midi_counter = (midi_counter+direction)%127
	# # #if(midi_counter  120):
	# # 	midi_counter = (midi_counter-4)%127

	# my = 40.0/127.0*midi_counter
	# max_y = int(BMP_FULL_METER_1.height-my)
	# max_y = max(min(max_y,BMP_FULL_METER_1.height),0)
	# #print(max_y)

	# # 127 = 0
	# #
	# # 0 = 40
	# #
	# #
	# # 40.0/127.0

	# meter_bmp.blit(0,max_y,BMP_FULL_METER_1,x1 = 0,y1 = max_y,x2 = BMP_FULL_METER_0.width, y2 = BMP_FULL_METER_1.height)
	# meter_bmp.blit(0,0,BMP_FULL_METER_0,x1 = 0,y1 = 0,x2 = BMP_FULL_METER_0.width, y2 = max_y)
	# bitmap.blit(0,0,meter_bmp)#,x1=0,y1=0, x2=20, y2=max_y)

	if(time.monotonic()-MACROPAD_FRAME_TIME):
		macropad.display.refresh()

	# screen saver
	if(loop_start_time-loop_last_action>MACROPAD_SLEEP_KEYS):
		macropad.pixels.brightness = 0
		macropad_sleep_keys = True
	#	set_screen(macropad, text_lines, blank_display)
	elif(macropad_sleep_keys and loop_start_time-loop_last_action<MACROPAD_SLEEP_KEYS):
		macropad.pixels.brightness = MACROPAD_BRIGHTNESS
		macropad_sleep_keys = False
	#	set_screen(macropad, text_lines, display_rows)

	
################################################################
# END MAIN LOOP
################################################################