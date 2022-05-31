# grid_numbers.py
# 
from adafruit_macropad import MacroPad
from rainbowio import colorwheel

GRID_NUMBER_BLANK = [0,0,0,
					0,0,0,
					0,0,0,
					0,0,0]
GRID_NUMBER_0 = [0,1,0,
				 1,0,1,
				 1,0,1,
				 0,1,0]
GRID_NUMBER_1 = [0,1,0,
				 1,1,0,
				 0,1,0,
				 1,1,1]
GRID_NUMBER_2 = [1,1,0,
				 0,0,1,
				 1,0,0,
				 1,1,1]
GRID_NUMBER_3 = [1,1,1,
				 0,0,1,
				 0,1,1,
				 1,1,1]
GRID_NUMBER_4 = [1,0,1,
				 1,0,1,
				 1,1,1,
				 0,0,1]
GRID_NUMBER_5 = [1,1,1,
				 1,0,0,
				 0,0,1,
				 1,1,0]
GRID_NUMBER_6 = [0,1,1,
				 1,0,0,
				 1,0,1,
				 0,1,1]
GRID_NUMBER_7 = [1,1,1,
				 0,0,1,
				 0,1,0,
				 0,1,0]
GRID_NUMBER_8 = [1,1,1,
				 1,0,1,
				 1,1,1,
				 1,1,1]
GRID_NUMBER_9 = [0,1,0,
				 1,0,1,
				 0,0,1,
				 0,1,0]
GRID_NUMBER_10 = [1,1,1,
				 1,1,1,
				 1,1,1,
				 1,1,1]
GRID_NUMBER_11 = [1,0,1,
				 1,0,1,
				 1,0,1,
				 1,0,1]
GRID_NUMBER_12 = [1,1,1,
				 1,0,1,
				 1,1,0,
				 1,1,1]


GRID_NUMBERS = [GRID_NUMBER_0,GRID_NUMBER_1,GRID_NUMBER_2,
				GRID_NUMBER_3,GRID_NUMBER_4,GRID_NUMBER_5,
				GRID_NUMBER_6,GRID_NUMBER_7,GRID_NUMBER_8,
				GRID_NUMBER_9,GRID_NUMBER_10,GRID_NUMBER_11,
				GRID_NUMBER_12]
AUDIO_DIR = "./audio_files/"

audio_files = ["00.mp3", "01.mp3", "02.mp3", 
				"03.mp3", "04.mp3", "05.mp3",
				"06.mp3", "07.mp3", "08.mp3",
				"09.mp3", "10.mp3", "11.mp3",
				"12.mp3"]

def number(macropad:MacroPad, i:int = 0,  fg_color=0,bg_color=120, sound=True):
	r = (x for x in range(0,12) if i in range(0,13))
	for k in r:
		tmp_fg_color = fg_color
		if(i in [10,11,12] and k in [0,3,6,9]):
			tmp_fg_color = fg_color + 70%255
		macropad.pixels[k] = colorwheel(tmp_fg_color) if GRID_NUMBERS[i][k] == 1 else colorwheel(bg_color)
	if(sound):
		macropad.play_file(AUDIO_DIR + audio_files[i])