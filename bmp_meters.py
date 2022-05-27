# bmp_meters.py
import board
import displayio


class BmpMeter:
	def __init__(self, width, height, colors= 2):
		self.width = width
		self.height = height
		self.colors = colors

display = board.DISPLAY
bitmap = displayio.Bitmap(display.width, display.height,2)
bg_bmp = displayio.Bitmap(display.width, display.height,2)
blank_bmp = displayio.Bitmap(display.width, display.height,2)

bmp_meter = displayio.Bitmap(display.width, display.height,2)

bmp_meter.fill(0)

