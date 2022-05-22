# code.py
from adafruit_macropad import MacroPad
from rainbowio import colorwheel
from adafruit_midi.midi_message import note_parser
from adafruit_midi.control_change import ControlChange
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.pitch_bend import PitchBend
import time
import random
import grid_numbers
from colors import COLORS
from midi_notes import MIDI_NOTES
import json

class MidiConfig:
	def __init__(self, config):
		self.cc = config["cc"]
		self.key_no = config["key_no"]
		self.description = config["description"]
		self.on_color = COLORS.get(config["on_color"],int(config.get("on_color_hex",0xFF0000)))
		self.off_color = COLORS.get(config["off_color"],int(config.get("off_color_hex",0xFFFFFF)))

		##self.off_color = COLORS.get(config["off_color"],0x000000)
		self.max_value = config["max_value"]
		self.min_value = config["min_value"]
		self.toggle = config["toggle"]
		self.current_value = 0
	def __repr__(self):
		return (f"({self.description}: cc={self.cc}, max={self.max_value}, min={self.min_value})")
	def str(self):
			return (f"({self.description}: cc={self.cc}, max={self.max_value}, min={self.min_value})")
	def msg(self,value=None):
		if(value is None):
			value = self.current_value
		return_value = value
		if(self.toggle==1):
			return_value = 127 if value == 0 else 0
		return ControlChange(self.cc,return_value)

class MacroPadMidi:
	keys = list()
	def __init__(self):
		for k in range(0,12):
			self.keys.append(0)
		self.encoder = 0
		self.encoder_click = 0
	
	def __repr__(self):
		print(f"keys={self.keys}, encoder={self.encoder}, enc_click={self.encoder_click}")

midi_keys = list()
midi_encoder = None
midi_encoder_click = None

def load_midi_config(midi_list, config_list):
	for c in config_list:
		midi_list.append(MidiConfig(c))


pad_midi_values = MacroPadMidi()

MIDI_CONFIG_JSON = "midi_controller_config.json"
conf_file = open(MIDI_CONFIG_JSON)
conf = json.load(conf_file)
conf_file.close()

key_midi_config = list()
encoder_midi_config = list()

for k in range(0,12):
	key_midi_config.append(conf['controller']['1'][str(k+1)])
encoder_midi_config.append(conf['controller']['1']['enc'])
encoder_midi_config.append(conf['controller']['1']['enc_click'])
load_midi_config(midi_keys,key_midi_config)
midi_encoder = MidiConfig(conf['controller']['1']['enc'])
midi_encoder_click = MidiConfig(conf['controller']['1']['enc_click'])

midi_cc_lookup = dict()
for k in midi_keys:
	midi_cc_lookup[k.cc] = k.key_no

CC_NUM = 74  # select your CC number

start_time = time.monotonic()

tones = [196, 220, 246, 262, 294, 330, 349, 392, 440, 494, 523, 587]

macropad = MacroPad(rotation=0)  # create the macropad object, rotate orientation
macropad.display.auto_refresh = False  # avoid lag

# --- Pixel setup --- #
key_color = colorwheel(130)  # fill with cyan to start

macropad.pixels.brightness = 0.25

# --- MIDI variables ---
mode = 0
mode_text = ["Patch", ("CC #%s" % (CC_NUM)), "Pitch Bend"]
midi_values = [0, 16, 8]  # bank, cc value, pitch
# Chromatic scale starting with C3 as bottom left keyswitch (or use any notes you like)
midi_notes = [
            57, 58, 59,
            54, 55, 56,
            51, 52, 53,
            48, 49, 50
            ]
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

# --- Display text setup ---
text_lines = macropad.display_text("Macropad")
text_lines[1].text = ""
text_lines.show()

last_knob_pos = macropad.encoder  # store knob position state

sleep_time = 0.5

loop_start_time = time.monotonic()
last_run_time = time.monotonic()

def loop_numbers(iterations,reverse:bool = 0):
	for r in range(0,iterations):
		n = r%13
		grid_numbers.number(macropad,n,fg_color = random.randint(0,5), bg_color=120)
		time.sleep(0.2)

while True:
	loop_start_time = time.monotonic()
	#   Block for handling things asynchronous..kind of
	#
	# if(loop_start_time-last_run_time>sleep_time):
	# 	for k in key_numbers:
	# 		r = random.randint(1,4)
	# 		macropad.pixels[k] = colorwheel(key_colors[k])
	# 		key_colors[k] = (key_colors[k]+random.randint(1,10)%11+r)%555
	# 	last_run_time = time.monotonic()

	midi_event = macropad.midi.receive()
	if midi_event is not None:
		if isinstance(midi_event, NoteOn):
			macropad.stop_tone()
			if(midi_event.velocity>0):
				pitch = float(MIDI_NOTES[midi_event.note][2])
				macropad.start_tone(pitch)
				macropad.pixels.fill(colorwheel((midi_event.note+midi_event.velocity-40)%100))
		if isinstance(midi_event, NoteOff):
				macropad.stop_tone()
		if(isinstance(midi_event, ControlChange)):
			# Encoder
			if midi_event.control == midi_encoder.cc:
				pad_midi_values.encoder = midi_event.value
				last_knob_pos = macropad.encoder
			# Encoder click
			if midi_event.control == midi_encoder_click.cc:
				pad_midi_values.encoder_click = midi_event.value
			# Keys
			if midi_event.control in (k.cc for k in midi_keys ):
				key = midi_cc_lookup[midi_event.control]-1
				pad_midi_values.keys[key] = midi_event.value
				key_on = True if midi_event.value > 0 else False
				event_color = midi_keys[key].on_color
				event_color = event_color if key_on else midi_keys[key].off_color
				k_color = event_color
				macropad.pixels[key] = k_color


	while macropad.keys.events:  # check for key press or release
		key_event = macropad.keys.events.get()

		if key_event:
			if key_event.pressed:
				key = key_event.key_number
				macropad.midi.send(midi_keys[key].msg(pad_midi_values.keys[key]))
				text_lines[1].text = "NoteOn:{}".format(midi_notes[key])

			if key_event.released:
				key = key_event.key_number

	macropad.encoder_switch_debounced.update()  # check the knob switch for press or release
	if macropad.encoder_switch_debounced.pressed:
		macropad.midi.send(midi_encoder_click.msg(pad_midi_values.encoder_click))
		
		macropad.red_led = macropad.encoder_switch
		text_lines[1].text = " "  # clear the note line

	if macropad.encoder_switch_debounced.released:
		macropad.red_led = macropad.encoder_switch

	if last_knob_pos is not macropad.encoder:  # knob has been turned

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
				if(pad_midi_values.encoder>127):
					pad_midi_values.encoder = 127
				elif(pad_midi_values.encoder<0):
					pad_midi_values.encoder = 0
				macropad.midi.send(midi_encoder.msg(pad_midi_values.encoder))
		last_knob_pos = macropad.encoder

	macropad.display.refresh()