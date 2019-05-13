
import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy
from PIL import Image
import sys

def main(argv):

	if len(argv) == 3:
		gazeRadius = float(argv[0])
		gazePosition = (float(argv[1]), float(argv[2]))
	else:
		gazeRadius = 25
		gazePosition = (512, 512)

	# initialize glfw
	if not glfw.init():
		return
	
	#creating the window
	window = glfw.create_window(1024, 980, "My OpenGL window", None, None)

	if not window:
		glfw.terminate()
		return

	glfw.make_context_current(window)


	#		   positions		colors		  texture coords
	quad = [   -1, -1, 0.0,  1.0, 0.0, 0.0,  0.0, 1.0,
				1, -1, 0.0,  0.0, 1.0, 0.0,  1.0, 1.0,
				1,  1, 0.0,  0.0, 0.0, 1.0,  1.0, 0.0,
			   -1,  1, 0.0,  1.0, 1.0, 1.0,  0.0, 0.0]

	quad = numpy.array(quad, dtype = numpy.float32)

	indices = [0, 1, 2,
			   2, 3, 0]

	indices = numpy.array(indices, dtype= numpy.uint32)

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
	shader = OpenGL.GL.shaders.compileProgram(OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER),
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

	auxParametersLoc = glGetUniformLocation(shader, 'auxParameters')

	texture = glGenTextures(1)
	glBindTexture(GL_TEXTURE_2D, texture)
	#texture wrapping params
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
	#texture filtering params
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

	image = Image.open("images/Yarbus_scaled.jpg")
	height, width = image.size

	img_data = numpy.array(list(image.getdata()), numpy.uint8)
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, height, width, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
	glGenerateMipmap(GL_TEXTURE_2D);

	glUseProgram(shader)

	glUniform3f(auxParametersLoc, float(gazeRadius), float(gazePosition[0]), float(gazePosition[1]))

	glClearColor(1, 1, 1, 1.0)

	while not glfw.window_should_close(window):
		glfw.poll_events()

		glClear(GL_COLOR_BUFFER_BIT)

		glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)

		glfw.swap_buffers(window)

	glfw.terminate()

if __name__ == "__main__":
	main(sys.argv[1:])
