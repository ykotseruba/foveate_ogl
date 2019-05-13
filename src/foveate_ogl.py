
import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy
from PIL import Image
import sys
import time
import getopt
from os import listdir
from os.path import join


vertex_shader = """
	#version 330
	in layout(location = 0) vec3 position;
	in layout(location = 1) vec3 color;
	in layout(location = 2) vec2 inTexCoords;
	uniform vec3 auxParameters;

	out vec3 newColor;
	out vec2 outTexCoords;
	out float gazeRadius;
	out vec2 gazePosition;

	void main()
	{
		gl_Position = vec4(position, 1.0f);
		newColor = color;
		outTexCoords = inTexCoords;
		gazeRadius = auxParameters[0];
		gazePosition = vec2(auxParameters[1], auxParameters[2]);
	}
	"""

fragment_shader = """
	#version 330
	in vec3 newColor;
	in vec2 outTexCoords;
	in float gazeRadius;
	in vec2 gazePosition;

	out vec4 outColor;
	uniform sampler2D samplerTex;
	void main()
	{
		vec2 outpos = gl_FragCoord.xy;
		float lod = log2(distance(outpos, gazePosition) / gazeRadius);		
		outColor = textureLod(samplerTex, outTexCoords, lod);
	}
	"""


class Foveate_OGL:
	def __init__(self, gazeRadius=25, gazePosition=(-1, -1), visualize = True):
		self.gazeRadius = gazeRadius
		self.gazePosition = gazePosition

		self.visualize = visualize

		self.initGLFW()
		self.initBuffers()


	def initGLFW(self):
		if not glfw.init():
			print('ERROR: Failed to initialize GLFW!')
			return
		#creating the window
		if not self.visualize:
			glfw.window_hint(glfw.VISIBLE, glfw.FALSE) #we cannot create OpenGL context without some sort of window, so we just hide it if no visualization is needed
	
		self.window = glfw.create_window(1024, 980, "My OpenGL window", None, None)

		if not self.window:
			glfw.terminate()
			print('ERROR: Failed to create GLFW window!')
			return

		glfw.make_context_current(self.window)

	def initBuffers(self):
		# Below is the code with coordinates for textured quad, these are fixed
		#		   positions		colors		  texture coords
		quad = [   -1, -1, 0.0,  1.0, 0.0, 0.0,  0.0, 1.0,
					1, -1, 0.0,  0.0, 1.0, 0.0,  1.0, 1.0,
					1,  1, 0.0,  0.0, 0.0, 1.0,  1.0, 0.0,
				   -1,  1, 0.0,  1.0, 1.0, 1.0,  0.0, 0.0]

		quad = numpy.array(quad, dtype = numpy.float32)

		indices = [0, 1, 2,
				   2, 3, 0]
		indices = numpy.array(indices, dtype= numpy.uint32)


		self.shader = OpenGL.GL.shaders.compileProgram(OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER),
												  OpenGL.GL.shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER))

		VBO = glGenBuffers(1)
		glBindBuffer(GL_ARRAY_BUFFER, VBO)
		glBufferData(GL_ARRAY_BUFFER, 128, quad, GL_STATIC_DRAW)

		EBO = glGenBuffers(1)
		glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, EBO)
		glBufferData(GL_ELEMENT_ARRAY_BUFFER, 24, indices, GL_STATIC_DRAW)

		#position = glGetAttribLocation(shader, "position")
		glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 32, ctypes.c_void_p(0))
		glEnableVertexAttribArray(0)

		#color = glGetAttribLocation(shader, "color")
		glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 32, ctypes.c_void_p(12))
		glEnableVertexAttribArray(1)

		#texCoords = glGetAttribLocation(shader, "inTexCoords")
		glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 32, ctypes.c_void_p(24))
		glEnableVertexAttribArray(2)

		self.auxParametersLoc = glGetUniformLocation(self.shader, 'auxParameters')

		texture = glGenTextures(1)
		glBindTexture(GL_TEXTURE_2D, texture)
		#texture wrapping params
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
		#texture filtering params
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

		glUseProgram(self.shader)

	#load image from array
	def loadImgFromArray(self, img = None):
		self.img = img.copy()
		self.img_height, self.img_width = self.img.size
		if self.visualize:
			glfw.set_window_size(self.window, self.img_height, self.img_width)
		self.updateTexture()
		if gazePosition[0] < 0:
			gazePosition[0] = self.img_height//2
			gazePosition[1] = self.img_width//2
			self.updateGaze(gazeRadius, gazePosition)

	#load image from file
	def loadImgFromFile(self, imgFilename='images/Yarbus_scaled.jpg'):
		self.img = Image.open(imgFilename)
		self.img_height, self.img_width = self.img.size
		if self.visualize:
			glfw.set_window_size(self.window, self.img_height, self.img_width)
		self.updateTexture()
		if self.gazePosition[0] < 0:
			self.gazePosition = (self.img_height//2, self.img_width//2)
			self.updateGaze(self.gazeRadius, self.gazePosition)

	def updateGaze(self, newGazeRadius, newGazePosition):
		self.gazePosition = newGazePosition
		self.gazeRadius = newGazeRadius
		glUniform3f(self.auxParametersLoc, float(self.gazeRadius), float(self.gazePosition[0]), float(self.gazePosition[1]))

	def updateTexture(self):
		self.img_height, self.img_width = self.img.size

		img_data = numpy.array(list(self.img.getdata()), numpy.uint8)
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.img_height, self.img_width, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
		glGenerateMipmap(GL_TEXTURE_2D);

	def run(self):

		glClearColor(1, 1, 1, 1.0)

		#while not glfw.window_should_close(window):
		glfw.poll_events()

		glClear(GL_COLOR_BUFFER_BIT)

		glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)

		glfw.swap_buffers(self.window)

		time.sleep(1)		


def usage():
	print('Usage: python3 src/foveate_ogl.py [options]')
	print('Application for efficient foveation transform over static images using OpenGL shaders')
	print('Options:')
	print('-h, --help\t\t', 'Displays this help')
	print('-p, --gazePosition\t', "Gaze position coordinates (e.g. '--gazePosition (512, 512)'), default: center of the image")
	print('-r, --gazeRadius\t', 'Radius of the circle around gaze position where the resolution of the image is the highest, default: 25')
	print('-v, --visualize\t\t', 'Show foveated images')
	print('-d, --inputDir\t\t', 'Input directory, default: images')
	print('-i, --inputImg\t\t', 'Input image')

def main(argv):
	try:
		opts, args = getopt.getopt(sys.argv[1:], 'hp:r:d:i:v', ['help','gazePosition', 'gazeRadius', 'inputDir', 'inputImg', 'visualize'])
	except getopt.GetoptError as err:
		print(str(err))
		usage()
		sys.exit(2)

	visualize = False
	gazePosition = (-1, -1)
	gazeRadius = 25
	inputDir = 'images'
	inputImg = None

	#TODO: add error checking for the arguments
	for o, a in opts:
		if o in ['-h', '--help']:
			usage()
			sys.exit(2)
		if o in ['-v', '--visualize']:
			visualize = True
		if o in ['-p', '--gazePosition']:
			gazePosition = tuple([float(x) for x in a.split(',')])
		if o in ['-r', '--gazeRadius']:
			gazeRadius = float(a)
		if o in ['-d', '--inputDir']:
			inputDir = a
		if o in ['-i', '--inputImg']:
			inputImg = a

	fov_ogl = Foveate_OGL(gazeRadius=gazeRadius, gazePosition=gazePosition, visualize=visualize)

	imageList = [f for f in listdir(inputDir) if any(f.endswith(ext) for ext in ['jpg', 'jpeg', 'bmp', 'png', 'gif']) ]
	
	

	for imgName in imageList:
		fov_ogl.loadImgFromFile(imgFilename=join(inputDir, imgName))
		fov_ogl.updateGaze(gazeRadius, gazePosition)
		fov_ogl.run()

	glfw.terminate() #close all windows, delete OGL context

if __name__ == "__main__":
	main(sys.argv[1:])
