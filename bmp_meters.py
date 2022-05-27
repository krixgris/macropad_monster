# bmp_meters.py
import displayio

class MidiMeterBmp:
	midi_value = list()
	def __init__(self, width=10, height=40, colors= 2):
		self.width = width
		self.height = height
		self.colors = colors

		MIDI_MAX_VALUE = 127
		BMP_FULL_METER_1 = displayio.Bitmap(width,height,colors)
		BMP_FULL_METER_0 = displayio.Bitmap(width,height,colors)
		BMP_FULL_METER_0.fill(0)
		BMP_FULL_METER_1.fill(1)


		for v in range(0,128):
			# fill list of bitmaps with each midi value
			self.midi_value.append(displayio.Bitmap(width,height,colors))
			my = height/MIDI_MAX_VALUE*v
			max_y = int(height-my)
			max_y = max(min(max_y,height),0)

			self.midi_value[v].blit(0,max_y,BMP_FULL_METER_1,x1 = 0,y1 = max_y,x2 = width, y2 = height)
			self.midi_value[v].blit(0,0,BMP_FULL_METER_0,x1 = 0,y1 = 0,x2 = width, y2 = max_y)


