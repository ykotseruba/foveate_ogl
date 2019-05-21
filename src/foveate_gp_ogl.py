import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
from PIL import Image
import sys
import time
import getopt
from os import listdir, makedirs
from os.path import join
import math

MAX_SIZE = 5000

#shaders below are adapted from BlurredMipmapDemo in PsychToolBox
#(C) 2012 Mario Kleiner - Licensed under MIT license.

vertex_shader = """
    #version 330
    in layout(location = 0) vec3 position;
    in layout(location = 1) vec3 color;
    in layout(location = 2) vec2 inTexCoords;
    uniform vec2 auxParameters; //gaze position

    out vec3 newColor;
    out vec2 outTexCoords;
    out vec2 gazePosition;

    void main()
    {
        gl_Position = vec4(position, 1.0f);
        newColor = color;
        outTexCoords = inTexCoords;
        gazePosition = vec2(auxParameters[0], auxParameters[1]);
    }
    """

fragment_shader = """
    #version 330
    in vec3 newColor;
    in vec2 outTexCoords;
    in vec2 gazePosition;

    out vec4 outColor;
    uniform sampler2D imageTex;
    uniform sampler2D lodTex; //precomputed pyramid levels for each pixel
    void main()
    {
        vec2 outpos = gl_FragCoord.xy;
        vec4 lod = texture(lodTex, outpos);      
        outColor = textureLod(imageTex, outTexCoords, lod[0]);
    }
    """

#Geisler & Perry
class Foveate_GP_OGL:

    def __init__(self, dotPitch = -1, viewDist = -1, pix2deg = -1, gazePosition=(-1, -1), visualize = True):
        
        self.dotPitch = dotPitch
        self.viewDist = viewDist
        self.pix2deg = pix2deg
        self.gazePosition = gazePosition        

        self.CTO = 1/64 #constant from Geisler & Perry
        self.alpha = 0.106  #constant from Geisler & Perry
        self.epsilon2 = 2.3 #constant from Geisler & Perry

        self.visualize = visualize

        self.initGLFW()
        self.initBuffers()


        self.pyrlevelCones = None

    def initGLFW(self):
        if not glfw.init():
            print('ERROR: Failed to initialize GLFW!')
            return
        #creating the window
        if not self.visualize:
            glfw.window_hint(glfw.VISIBLE, glfw.FALSE) #we cannot create OpenGL context without some sort of window, so we just hide it if no visualization is needed
    
        self.window = glfw.create_window(1024, 980, "foveated", None, None)

        if not self.window:
            glfw.terminate()
            print('ERROR: Failed to create GLFW window!')
            return

        glfw.make_context_current(self.window)

    def initBuffers(self):
        # Below is the code with coordinates for textured quad, these are fixed
        #          positions        colors        texture coords
        quad = [   -1, -1, 0.0,  1.0, 0.0, 0.0,  0.0, 1.0,
                    1, -1, 0.0,  0.0, 1.0, 0.0,  1.0, 1.0,
                    1,  1, 0.0,  0.0, 0.0, 1.0,  1.0, 0.0,
                   -1,  1, 0.0,  1.0, 1.0, 1.0,  0.0, 0.0]

        quad = np.array(quad, dtype = np.float32)

        indices = [0, 1, 2,
                   2, 3, 0]
        indices = np.array(indices, dtype= np.uint32)


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

        self.imgTexture = glGenTextures(1)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.imgTexture)
        #texture wrapping params
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        #texture filtering params
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        self.lodTexture = glGenTextures(1)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.lodTexture)
        #texture wrapping params
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        #texture filtering params
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        if not self.visualize:
            self.FBO = glGenFramebuffers(1)
            glBindFramebuffer(GL_FRAMEBUFFER, self.FBO)
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.imgTexture, 0)

            self.RBO = glGenRenderbuffers(1)
            glBindRenderbuffer(GL_RENDERBUFFER, self.RBO)
            glRenderbufferStorage(GL_RENDERBUFFER, GL_RGBA, MAX_SIZE, MAX_SIZE)
            glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_RENDERBUFFER, self.RBO)

        glUseProgram(self.shader)

    #load image from array
    def loadImgFromArray(self, img = None):
        self.img = img.copy()
        self.img_width, self.img_height = self.img.size
        if self.visualize:
            glfw.set_window_size(self.window, self.img_width, self.img_height)
        #self.updateTexture()
        if self.gazePosition[0] < 0:
            self.gazePosition = (self.img_height/2, self.img_width/2)
            #self.updateGaze(gazePosition)

        x, step = np.linspace(0, self.img_height-1, num=self.img_height, retstep=True, dtype=np.float32)
        y, step = np.linspace(0, self.img_width-1, num=self.img_width, retstep=True, dtype=np.float32)

        self.ix, self.iy = np.meshgrid(y, x, sparse=False, indexing='xy')

        self.dotPitch = computeDotPitch(pix2deg=self.pix2deg, viewDist=self.viewDist, imgWidth=self.img_width)


        self.updateGaze(gazePosition)
        self.updateTexture()


    #load image from file
    def loadImgFromFile(self, imgFilename='images/Yarbus_scaled.jpg'):
        self.img = Image.open(imgFilename)
        self.img_width, self.img_height = self.img.size
        if self.visualize:
            glfw.set_window_size(self.window, self.img_width, self.img_height)

        if self.gazePosition[0] < 0:
            gazePosition = (self.img_height/2, self.img_width/2)
        else:
            gazePosition = self.gazePosition
        
        x, step = np.linspace(0, self.img_height-1, num=self.img_height, retstep=True, dtype=np.float32)
        y, step = np.linspace(0, self.img_width-1, num=self.img_width, retstep=True, dtype=np.float32)

        self.ix, self.iy = np.meshgrid(y, x, sparse=False, indexing='xy')

        self.dotPitch = computeDotPitch(pix2deg=self.pix2deg, viewDist=self.viewDist, imgWidth=self.img_width)

        self.updateGaze(gazePosition)
        self.updateTexture()


    def updateGaze(self, newGazePosition):
        self.gazePosition = newGazePosition
        glUniform2f(self.auxParametersLoc, float(self.gazePosition[1]), self.img_height - float(self.gazePosition[0]))
        self.preprocess()

    def updateTexture(self):
        self.img_width, self.img_height = self.img.size

        img_data = np.array(list(self.img.getdata()), np.uint8)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.imgTexture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.img_width, self.img_height, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
        glGenerateMipmap(GL_TEXTURE_2D);
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.lodTexture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, self.img_width, self.img_height, 0, GL_RED, GL_FLOAT, self.pyrlevelCones)


    #compute for each pixel the level of the pyramid to sample from
    def preprocess(self):
        #eradius is the radial distance between each point and the point of gaze in meters.
        distPx = np.sqrt(np.power(self.ix-self.gazePosition[1], 2) + np.power(self.iy-self.gazePosition[0], 2))

        eradius = distPx*self.dotPitch

        #ec - eccentricity from the fovea center for each pixel in degrees
        ec = 180*np.arctan(eradius/self.viewDist)/math.pi

        eyefreqCones = self.epsilon2/(self.alpha*(ec + self.epsilon2))*math.log(1/self.CTO)
        eyefreqCones = np.power(eyefreqCones, 0.3)

        maxVal = np.amax(eyefreqCones)
        minVal = np.amin(eyefreqCones)
        eyefreqCones = (eyefreqCones-minVal)/(maxVal-minVal)

        #pyrlevel is a fractional level of the pyramid which must be used at each pixel
        #in order to match the foveal resolution function defined above
        eyefreqCones = 1 - eyefreqCones
        numLevels = 1 + math.floor(math.log2(max(self.img_width, self.img_height)))
        self.pyrlevelCones = (numLevels-1)*eyefreqCones

        #constrain pyrlevel to conform to the levels of the pyramid which have been computed
        self.pyrlevelCones = np.maximum(0, np.minimum(numLevels, self.pyrlevelCones))
        print(self.pyrlevelCones)

    def saveImage(self, filename):
        if self.visualize: 
            glReadBuffer(GL_FRONT)
        else:
            glReadBuffer(GL_COLOR_ATTACHMENT0)

        pixels = glReadPixels(0,0,self.img_width,self.img_height,GL_RGB,GL_UNSIGNED_BYTE)
        image = Image.frombytes("RGB", (self.img_width,self.img_height), pixels)
        image = image.transpose( Image.FLIP_TOP_BOTTOM)
        image.save(filename)

    def run(self):

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.imgTexture)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.lodTexture)

        if not self.visualize:
            if not glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE:
                print('Error: Framebuffer binding failed!')
                exit()
                glBindFramebuffer(GL_FRAMEBUFFER, 0)

        glClear(GL_COLOR_BUFFER_BIT)

        glViewport(0, 0, self.img_width, self.img_height)

        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)

        glfw.swap_buffers(self.window)
        glfw.poll_events()      

        if self.visualize:
            time.sleep(0.5) 

def computeDotPitch(pix2deg=32, viewDist=0.6, imgWidth=1024):
    inputSizeDeg = imgWidth/pix2deg
    imgWidth_m = 2*viewDist*math.tan((inputSizeDeg*math.pi/180)/2)
    dotPitch = imgWidth_m/imgWidth
    return dotPitch


def usage():
    print('Usage: python3 src/foveate_ogl.py [options]')
    print('Application for efficient foveation transform over static images using OpenGL shaders')
    print('Options:')
    print('-h, --help\t\t', 'Displays this help')
    print('-p, --gazePosition\t', "Gaze position coordinates (e.g. '--gazePosition 512,512'), default: center of the image")
    print('-d, --viewDist\t', 'Radius of the circle around gaze position where the resolution of the image is the highest, default: 25')
    print('-x, --pix2deg\t', 'Number of pixels per deg vis angle')
    print('-v, --visualize\t\t', 'Show foveated images')
    print('-i, --inputDir\t\t', 'Input directory, default: images')
    print('-o, --outputDir\t\t', 'Output directory, default: output')

def main():

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hp:d:i:o:x:v', ['help','gazePosition', 'viewDist', 'pix2deg', 'inputDir', 'outputDir', 'visualize'])
    except getopt.GetoptError as err:
        print(str(err))
        usage()
        sys.exit(2)

    visualize = False
    gazePosition = (-1, -1)
    gazeRadius = 25
    inputDir = 'images'
    outputDir = ''
    saveOutput = False

    #TODO: add error checking for the arguments
    for o, a in opts:
        if o in ['-h', '--help']:
            usage()
            sys.exit(2)
        if o in ['-v', '--visualize']:
            visualize = True
        if o in ['-p', '--gazePosition']:
            gazePosition = tuple([float(x) for x in a.split(',')])
        if o in ['-d', '--viewDist']:
            viewDist = float(a)
        if o in ['-x', '--pix2deg']:
            pix2deg = float(a)
        if o in ['-i', '--inputDir']:
            inputDir = a
        if o in ['-o', '--outputDir']:
            outputDir = a
            saveOutput = True

    fov_ogl = Foveate_GP_OGL(viewDist=viewDist, gazePosition=gazePosition, pix2deg=pix2deg, visualize=visualize)

    imageList = [f for f in listdir(inputDir) if any(f.endswith(ext) for ext in ['jpg', 'jpeg', 'bmp', 'png', 'gif']) ]
    
    if saveOutput:
        makedirs(outputDir, exist_ok=True)

    for imgName in imageList:
        fov_ogl.loadImgFromFile(imgFilename=join(inputDir, imgName))
        fov_ogl.run()

        if saveOutput:
            fov_ogl.saveImage(join(outputDir, imgName))

    glfw.terminate()

if __name__ == "__main__":
    main()
