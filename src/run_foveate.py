import getopt
import sys
from OpenGL.GL import *
from OpenGL.arrays import vbo
from OpenGLContext.arrays import *
from OpenGL.GL import shaders

def usage():
	print('Usage: python3 foveate.py [options]')
	print('Foveate-OGL v0.1')
	print('Add foveation transform to static images.')
	print('-h, --help\t\t', 'Displays this help')
	print('-r, --gaze_radius\t\t', 'gaze radius (default=25)')
	print('-i\t\t\t', 'input file or directory')
	print('-o\t\t\t', 'output directory')


def main(argv):

	gaze_radius = 25
	input_path = 'images/Yarbus_scaled.jpg'

	try:
		opts, args = getopt.getopt(argv, 'hr:i:', ['help', 'gaze_radius'])
	except getopt.GetoptError as err:
		print(str(err))
		usage()
		sys.exit(2)

	for o, a in opts:
		if o in ['-h', '--help']:
			usage()
			sys.exit(2)
		if o in ['-r', '--gaze_radius']:
			gaze_radius = int(a)
		if o == '-i':
			input_path = a


	fovOGL = Foveate_OGL()
	fovOGL.loadImg(input_path)
	


if  __name__=="__main__":
	main(sys.argv[1:])