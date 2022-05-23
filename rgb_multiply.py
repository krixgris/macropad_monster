# rgb_mult
def byte_mult(b:int,multiplier:float)->int:
	return max(min(int(b*multiplier),255),0)

def rgb_mult(color_rgb:int,intensity_factor:float=1.0):
	# filter
	r = 0xFF0000
	g = 0x00FF00
	b = 0x0000FF

	# bitwise & filters out correct bytes
	r_byte = color_rgb&r
	g_byte = color_rgb&g
	b_byte = color_rgb&b

	# shift bits to split out 1 byte
	r_byte = r_byte>>16
	g_byte = g_byte>>8
	b_byte = b_byte

	# multiply and shift bits back to the correct position
	r_byte = byte_mult(r_byte,intensity_factor)<<16
	g_byte = byte_mult(g_byte,intensity_factor)<<8
	b_byte = byte_mult(b_byte,intensity_factor)

	#return sum
	return_color = r_byte+g_byte+b_byte

	return return_color