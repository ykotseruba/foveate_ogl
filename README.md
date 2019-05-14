# Foveate_OGL
Implementation of foveation transform for static images in Python and PyOpenGL
The basis for this code is the (BlurredMipmapDemo from Psychtoolbox-3)[https://github.com/Psychtoolbox-3/Psychtoolbox-3/blob/master/Psychtoolbox/PsychDemos/BlurredMipmapDemo.m].

# Install

This code uses OpenGL 3.3 and GLSL 3.30, make sure your video card supports these and proper drivers are installed.

Install requirements using pip3, these include numpy, glfw, PyOpenGL and Pillow.
```
pip3 install -r requirements.txt
```

# Run

To run a demo:
```
python3 src/foveate_ogl.py -v
```

This will compute foveation transform over two images in the ```images``` directory and display them in a window.
