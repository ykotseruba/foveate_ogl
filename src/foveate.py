# -----------------------------------------------------------------------------
# Copyright (c) 2009-2016 Nicolas P. Rougier. All rights reserved.
# Distributed under the (new) BSD License.
# -----------------------------------------------------------------------------
from glumpy import app, gloo, gl, glm, data
from glumpy.ext import png
import numpy as np

# vertex = """
#     attribute vec2 position;
#     attribute vec2 texcoord;
#     varying vec2 v_texcoord;
#     void main()
#     {
#         gl_Position = vec4(position, 0.0, 1.0);
#         v_texcoord = texcoord;
#     }
# """


# fragment = """
#     uniform sampler2D texture;
#     varying vec2 v_texcoord;
#     void main()
#     {
#         gl_FragColor = texture2D(texture, v_texcoord);
#     }
# """

vertex = """
/* Input from Screen('DrawTexture'): */
attribute vec4 auxParameters0;

attribute vec2 position;
attribute vec2 texcoord;
varying vec2 v_texcoord;

/* Passed to fragment shader: */
varying vec2  gazePosition;
varying float gazeRadius;
varying vec4  baseColor;

void main(void)
{
    /* Apply standard geometric transformations: */
    gl_Position = vec4(position, 0.0, 1.0);

    /* Pass standard texture coordinates: */
    //gl_TexCoord[0] = gl_MultiTexCoord0;
    v_texcoord = texcoord;

    /* Pass 'gazePosition' from first two auxParameters: */
    gazePosition.xy = auxParameters0.xy;

    /* Pass 'gazeRadius' from third auxParameters element: */
    gazeRadius = auxParameters0[2];

    /* Base color: */
    baseColor = vec4(1, 1, 1, 1); //baseColor

    return;
} """


fragment = """
/* Image is the mip-mapped texture with the image resolution pyramid: */
uniform sampler2D texture;
#extension GL_ARB_texture_query_levels : enable
/* Passed from vertex shader: */
varying vec4  baseColor;
varying vec2  gazePosition;
varying float gazeRadius;
varying vec2 v_texcoord;

void main(void)
{
    /* Output pixel position in absolute window coordinates: */
    vec2 outpos = gl_FragCoord.xy;

    /* Compute distance to center of gaze, normalized to units of gazeRadius: */
    /* We take log2 of it, because lod selects mip-level, which selects for a */
    /* 2^lod decrease in resolution: */
    float lod = log2(distance(outpos, gazePosition) / gazeRadius);

    /* Lookup texel color in image pyramid at input texture coordinate and
     * specific mip-map level 'lod': */
    vec4 texel = texture2DLod(texture, v_texcoord, lod);

    /* Apply modulation baseColor and write to framebuffer: */
    gl_FragColor = texel;
    //gl_FragColor = vec4(lod, lod, lod, 1);
} """



window = app.Window(width=980, height=1024, aspect=1)
framebuffer = np.zeros((window.height, window.width * 3), dtype=np.uint8)


@window.event
def on_draw(dt):
    window.clear()
    quad.draw(gl.GL_TRIANGLE_STRIP)
    gl.glReadPixels(0, 0, window.width, window.height,
                   gl.GL_RGB, gl.GL_UNSIGNED_BYTE, framebuffer)
    png.from_array(framebuffer, 'RGB').save('screenshot.png')


quad = gloo.Program(vertex, fragment, count=4)
quad['position'] = [(-1,-1), (-1,+1), (+1,-1), (+1,+1)]
quad['texcoord'] = [( 0, 0), ( 0, 1), ( 1, 0), ( 1, 1)]
quad['texture'] = data.load("images/Yarbus_scaled.jpg")
quad['auxParameters0'] = [(512, 512, 100, 0)]

app.run(framecount=1)

