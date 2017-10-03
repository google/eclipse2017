# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Class to render images of total solar eclipses from various
locations at various times.

The rendering draws a images using either OpenGL or Qt Painter and
composites them together to make a semi-realistic image of the sun,
moon, and solar corona.
"""

import json
import cv2
import numpy as np
from coords import horizontal_to_cartesian, scale_vector
import math
deg = math.degrees
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtOpenGL import *
from render_constants import *

def qimage_to_numpy(image):
    # Convert a QImage to a numpy array
    image = image.convertToFormat(QtGui.QImage.Format_ARGB32)
    width = image.width()
    height = image.height()
    ptr = image.constBits()

    return np.frombuffer(ptr.asstring(image.byteCount()), dtype=np.uint8).reshape(height, width, 4)

class EclipseRenderer:
    def __init__(self, fov=2, pan=(0,0), generate=False, load_file=None, save_file=None):
        # fov defines the Field of View of the resulting image
        # at fov=0.5 degrees, the sun will completley fill the image
        self.fov = fov
        # (x,y) pixels to pan the rendered image
        self.pan = pan
        self.surfaceFormat = QtGui.QSurfaceFormat()

        self.openGLContext = QtGui.QOpenGLContext()
        self.openGLContext.setFormat(self.surfaceFormat)
        self.openGLContext.create()
        if not self.openGLContext.isValid():
            sys.exit(1)

        self.surface = QtGui.QOffscreenSurface()
        self.surface.setFormat(self.surfaceFormat)
        self.surface.create()
        if not self.surface.isValid():
            sys.exit(2)

        self.openGLContext.makeCurrent(self.surface)

        # Create a framebuffer object to hold offscreen image renders.
        format = QtGui.QOpenGLFramebufferObjectFormat()
        format.setAttachment(QtGui.QOpenGLFramebufferObject.CombinedDepthStencil)
        format.setSamples(16)
        self.fbo = QtGui.QOpenGLFramebufferObject(RES_X, RES_Y, format)

        if generate:
            self.setupRandom()
            self.writeRandom(save_file)
        else:
            self.setRandomAsJSON(open(load_file).read())

        self.initializeGL()

    def setupRandom(self):
        # Create a collection of "polar coronal angles" which are used to
        # generate the fine, curved, "polar" coronal streams.
        self.n_polar_coronal_angles = 10
        self.polar_coronal_angles = np.hstack([
            np.random.random_sample(self.n_polar_coronal_angles) * (NORTHERN_MAX - NORTHERN_MIN) + NORTHERN_MIN,
            np.random.random_sample(self.n_polar_coronal_angles) * (SOUTHERN_MAX - SOUTHERN_MIN) + SOUTHERN_MIN
        ])
        # Create a series of sub-angles that define collection of substreams off the main polar angle,
        self.polar_coronal_ellipse_params = np.random.random_sample(self.n_polar_coronal_angles*2)
        self.polar_coronal_subangles = []
        self.n_coronal_subangles_per_angle = 5
        for i in range(self.n_polar_coronal_angles*2):
            self.polar_coronal_subangles.append(np.random.normal(0, 5, self.n_coronal_subangles_per_angle))

        # Create a series of "equatorial corona angles" which are used to generate large, triangle-shaped "equatorial" coronal streams
        self.n_equatorial_coronal_angles = 3
        self.equatorial_coronal_angles = np.hstack([
            np.random.random_sample(self.n_equatorial_coronal_angles) * (WESTERN_MAX - WESTERN_MIN) + WESTERN_MIN,
            np.random.random_sample(self.n_equatorial_coronal_angles) * (EASTERN_MAX - EASTERN_MIN) + EASTERN_MIN,
        ])

    def writeRandom(self, fname):
        w = open(fname, "w")
        w.write(self.getRandomAsJSON())
        w.close()

    def getRandomAsJSON(self):
        d = {
            'n_polar_corona_angles': self.n_polar_coronal_angles,
            'polar_coronal_angles': list(self.polar_coronal_angles),
            'polar_coronal_subangles': map(list, self.polar_coronal_subangles),
            'polar_coronal_ellipse_params': list(self.polar_coronal_ellipse_params),
            'n_coronal_subangles_per_angle': self.n_coronal_subangles_per_angle,
            'n_equatorial_coronal_angles': self.n_equatorial_coronal_angles,
            'equatorial_coronal_angles': list(self.equatorial_coronal_angles)
        }

        return json.dumps(d)

    def setRandomAsJSON(self, j):
        d = json.loads(j)
        self.n_polar_corona_angles = d['n_polar_corona_angles']
        self.polar_coronal_angles = d['polar_coronal_angles']
        self.polar_coronal_subangles = d['polar_coronal_subangles']
        self.polar_coronal_ellipse_params = d['polar_coronal_ellipse_params']
        self.n_coronal_subangles_per_angle = d['n_coronal_subangles_per_angle']
        self.n_equatorial_coronal_angles = d['n_equatorial_coronal_angles']
        self.equatorial_coronal_angles = d['equatorial_coronal_angles']

        self.initializeGL()

    def initializeGL(self):
        self.fbo.bind()
        glViewport(0, 0, RES_X, RES_Y)
        self.setupGL()

        self.sun_quadric=gluNewQuadric()
        gluQuadricNormals(self.sun_quadric, GLU_SMOOTH)
        gluQuadricTexture(self.sun_quadric, GL_TRUE)
        gluQuadricDrawStyle(self.sun_quadric, GLU_FILL)
        self.moon_quadric=gluNewQuadric()
        gluQuadricNormals(self.moon_quadric, GLU_SMOOTH)
        gluQuadricTexture(self.moon_quadric, GL_TRUE)
        gluQuadricDrawStyle(self.moon_quadric, GLU_FILL)
        self.fbo.release()

    def setupGL(self):
        glClearColor(0., 0., 0., 0.)
        glClearDepth(1.0)
        glDepthFunc(GL_LESS)
        glShadeModel(GL_SMOOTH)
        # If polygon smoothing is enabled, OpenGL renders after
        # QPainter renders are messed up.
        # glEnable(GL_POLYGON_SMOOTH)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)

    def setupProjection(self, sun_x, sun_y, sun_z):
        self.fbo.bind()
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = RES_X/float(RES_Y)
        # Set a perspective view (farther objects appear smaller)
        gluPerspective(self.fov, aspect, EARTH_MOON_DISTANCE, SUN_EARTH_DISTANCE)
        # # Point the camera at the sun with the appropriate rotation
        gluLookAt(0, 0, 0, sun_x+self.pan[0], sun_y+self.pan[1], sun_z, 0, 1, 0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        self.fbo.release()

    def paint(self, p):
        # Get the potion and time parameters for this frame of rendering
        dt, sun_alt, sun_az, moon_alt, moon_az, sun_r, moon_r, sep, parallactic_angle, lat, lon = p
        sun_coords = horizontal_to_cartesian(deg(sun_alt), deg(sun_az))
        sun_x, sun_y, sun_z = scale_vector(sun_coords, SUN_EARTH_DISTANCE)
        moon_coords = horizontal_to_cartesian(deg(moon_alt), deg(moon_az))
        moon_x, moon_y, moon_z = scale_vector(moon_coords, EARTH_MOON_DISTANCE)
        # Set up the appropriate viewing projection
        self.setupProjection(sun_x, sun_y, sun_z)

        self.clear_background()

        # Draw the corona first as a background layer
        self.draw_corona(p)

        # Draw the sun and moon on top of the corona
        self.paintGL(sun_x, sun_y, sun_z, moon_x, moon_y, moon_z)

        image = self.fbo.toImage()

        return image

    def clear_background(self):
        self.fbo.bind()
        device = QtGui.QOpenGLPaintDevice(RES_X, RES_Y)
        painter = QtGui.QPainter()
        painter.begin(device)
        rect = QtCore.QRect(0, 0, RES_X, RES_Y)
        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.HighQualityAntialiasing)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtCore.Qt.black)
        painter.drawRect(rect)
        painter.end()
        self.fbo.release()

    def getSunSizeProj(self, p):
        """Get the size of the sun in screen pixels.

        Warning: this function doesn't work correctly, unless the sun
        is positioned appropriately.  Use getSunSize instead.
        """
        dt, sun_alt, sun_az, moon_alt, moon_az, sun_r, moon_r, sep, parallactic_angle = p
        sun_coords = horizontal_to_cartesian(deg(sun_alt), deg(sun_az))
        sun_x, sun_y, sun_z = scale_vector(sun_coords, SUN_EARTH_DISTANCE)

        self.setupProjection(sun_x, sun_y, sun_z)
        x0= gluProject(sun_x, sun_y, sun_z)
        x1= gluProject(sun_x-SUN_RADIUS, sun_y, sun_z)

        # Return the distance between two suns spaced by solar radius,
        # in screen pixels
        x = abs(x1[0] - x0[0])
        return x

    def getSunMoonCenter(self, p):
        # Get the center of the sun and the moon in screen pixels
        dt, sun_alt, sun_az, moon_alt, moon_az, sun_r, moon_r, sep, parallactic_angle, lat, lon = p
        sun_coords = horizontal_to_cartesian(deg(sun_alt), deg(sun_az))
        sun_x, sun_y, sun_z = scale_vector(sun_coords, SUN_EARTH_DISTANCE)
        moon_coords = horizontal_to_cartesian(deg(moon_alt), deg(moon_az))
        moon_x, moon_y, moon_z = scale_vector(moon_coords, EARTH_MOON_DISTANCE)

        self.setupProjection(sun_x, sun_y, sun_z)
        sun_center = gluProject(sun_x, sun_y, sun_z)
        moon_center = gluProject(moon_x, moon_y, moon_z)

        return sun_center, moon_center

    def getSunSize(self, p):
        """Get the size of the sun in screen pixels.

        This is a hack: it renders the sun, then finds the contour
        surrounding the sun and computes the center/radius of that.
        """
        self.fbo.bind()
        self.clear_background()
        self.fbo.release()
        dt, sun_alt, sun_az, moon_alt, moon_az, sun_r, moon_r, sep, parallactic_angle, lat, lon = p
        sun_coords = horizontal_to_cartesian(deg(sun_alt), deg(sun_az))
        sun_x, sun_y, sun_z = scale_vector(sun_coords, SUN_EARTH_DISTANCE)
        self.fbo.bind()
        self.draw_sun(sun_x, sun_y, sun_z)
        glFlush()
        self.fbo.release()
        image = self.fbo.toImage()
        # Find the contours of the sun in the image
        contours = self.find_contours(image)
        # Make a poly that fits the contour
        poly = cv2.approxPolyDP( np.array(contours[0]), 3, True )
        # Find the minimum enclosing circle of the polygon
        c = cv2.minEnclosingCircle(poly)
        self.fbo.bind()
        self.clear_background()
        self.fbo.release()
        return c

    def paintGL(self, sun_x, sun_y, sun_z, moon_x, moon_y, moon_z):
        # Draw the sun
        self.fbo.bind()
        self.draw_sun(sun_x, sun_y, sun_z)
        glFlush()
        self.fbo.release()
        image = self.fbo.toImage()

        # Produce blurred image of sun
        npimage = qimage_to_numpy(image)
        h, w, b = npimage.shape
        blur = cv2.GaussianBlur(npimage, (75, 75), 0, 0)
        cv2.convertScaleAbs(blur, blur, 2, 1)
        # Combine the blurred with the sun
        combo = cv2.addWeighted(blur, 0.5, npimage, 0.5, -1)
        h, w, b = combo.shape
        qimage = QtGui.QImage(combo.data,w,h,QtGui.QImage.Format_ARGB32).rgbSwapped()
        self.fbo.bind()
        device = QtGui.QOpenGLPaintDevice(RES_X, RES_Y)
        painter = QtGui.QPainter()
        painter.begin(device)
        rect = QtCore.QRect(0, 0, RES_X, RES_Y)
        # Draw the blurred sun/sun combo image on the screen
        painter.drawImage(rect, qimage, rect)
        painter.end()
        self.fbo.release()

        # Draw the moon
        self.fbo.bind()
        self.draw_moon(moon_x, moon_y, moon_z)
        glFlush()
        self.fbo.release()

    def find_contours(self, image):
        image = qimage_to_numpy(image)
        gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        #_,thresh = cv2.threshold(gray,150,255,cv2.THRESH_BINARY_INV)
        # kernel = cv2.getStructuringElement(cv2.MORPH_CROSS,(3,3))
        # dilated = cv2.dilate(gray,kernel,iterations = 13)
        contours, hierarchy = cv2.findContours(gray,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
        return contours

    def draw_sun(self, sun_x, sun_y, sun_z):
        glLoadIdentity()
        glTranslatef(sun_x, sun_y, sun_z)
        glColor4f( 1.0, 1.0, 1.0, 1.0 );
        glPolygonMode(GL_FRONT, GL_FILL);
        gluSphere(self.sun_quadric,SUN_RADIUS,SEGMENTS,RING_COUNT)
        glFlush()

    def draw_moon(self, moon_x, moon_y, moon_z):
        glLoadIdentity()
        glTranslatef(moon_x, moon_y, moon_z)
        glColor4f( 0.0, 0.0, 0.0, 1)
        glPolygonMode(GL_FRONT, GL_FILL);
        gluSphere(self.moon_quadric,MOON_RADIUS,SEGMENTS,RING_COUNT)
        glFlush()

    def draw_corona(self, p):
        im_polar = np.zeros((RES_Y, RES_X, 4), np.uint8)
        dt, sun_alt, sun_az, moon_alt, moon_az, sun_r, moon_r, sep, parallactic_angle, lat, lon = p
        sun_coords = horizontal_to_cartesian(deg(sun_alt), deg(sun_az))
        sun_x, sun_y, sun_z = scale_vector(sun_coords, SUN_EARTH_DISTANCE)
        sun_center, sun_size = self.getSunSize(p)

        circle_center = (int(sun_center[0]), int(sun_center[1]))
        circle_size = int(sun_size)
        circle_color = (255, 255, 255, 255)

        # Draw coronal polar angle lines as bundles of truncated ellipses.
        # The ellipses start at the sun surface and project outward
        # towards the poles, then curve away
        # TODO(dek): better curving, especially angle-dependent curves
        for i, angle in enumerate(self.polar_coronal_angles):
            for j in self.polar_coronal_subangles[i]:
                x = int(circle_center[0] + math.cos(angle)*circle_size)
                y = int(circle_center[1] + math.sin(angle)*circle_size)
                cv2.ellipse(im_polar, (x,y), (int(circle_size*8), int(circle_size/8.)), deg(angle)+j,  0, 90, (255, 255, 255, 127))
        blur_polar = cv2.blur(im_polar, (5, 5))

        # Draw the coronal equatorial regions as polygons that get
        # skinnier as they get further from the sun's surface
        im_equitorial = np.zeros((RES_Y, RES_X, 4), np.uint8)
        for i, angle in enumerate(self.equatorial_coronal_angles):
            min_ = angle - math.radians(15)
            min_2 = angle - math.radians(5)
            max_2 = angle + math.radians(5)
            max_ = angle + math.radians(15)

            x1 = int(circle_center[0] + math.cos(min_)*circle_size)
            y1 = int(circle_center[1] + math.sin(min_)*circle_size)
            x1_2 = int((circle_center[0] + math.cos(min_)*circle_size*2))
            y1_2 = int((circle_center[1] + math.sin(min_)*circle_size*2))

            x2 = int((circle_center[0] + math.cos(min_2)*circle_size*4))
            y2 = int((circle_center[1] + math.sin(min_2)*circle_size*4))

            x3 = int((circle_center[0] + math.cos(angle)*circle_size*6))
            y3 = int((circle_center[1] + math.sin(angle)*circle_size*6))

            x4 = int((circle_center[0] + math.cos(max_2)*circle_size*4))
            y4 = int((circle_center[1] + math.sin(max_2)*circle_size*4))

            x5_2 = int((circle_center[0] + math.cos(max_)*circle_size*2))
            y5_2 = int((circle_center[1] + math.sin(max_)*circle_size*2))
            x5 = int(circle_center[0] + math.cos(max_)*circle_size)
            y5 = int(circle_center[1] + math.sin(max_)*circle_size)

            pts = np.array([ [x1,y1], [x1_2, y1_2], [x2,y2], [x3,y3], [x4,y4], [x5_2, y5_2], [x5,y5] ])

            cv2.fillConvexPoly(im_equitorial, pts, (255, 255, 255, 127))

        # Blur the equatorial corona
        blur_equitorial = cv2.blur(im_equitorial, (100, 100))

        # Create a blurred sun to simulate glare
        im_corona_positive = np.zeros((RES_Y, RES_X, 4), np.uint8)
        cv2.circle(im_corona_positive, circle_center, int(circle_size*3), [255, 255, 255, 127], -1)
        blur_corona_positive = cv2.blur(im_corona_positive, (int(circle_size*1.5), int(circle_size*1.5)))
        blur_corona_positive = cv2.blur(blur_corona_positive, (int(circle_size*1.25), int(circle_size*1.25)))
        # Subtract out the center of the glare
        cv2.circle(blur_corona_positive, circle_center, circle_size, [0,0,0, 255], -1)

        alpha = 1
        beta = 0.15
        # Combine the blurred polar corona with the glare
        result = cv2.addWeighted( blur_polar, alpha, blur_corona_positive, beta, 0.0)
        # Combine that with the equitorial blur
        result2 = cv2.addWeighted( result, 1, blur_equitorial, 1, 0.0)

        # Render the solar corona to the screen
        self.fbo.bind()
        device = QtGui.QOpenGLPaintDevice(RES_X, RES_Y)
        painter = QtGui.QPainter()
        h, w, b = result2.shape
        painter.begin(device)
        # Apply parallactic rotation to the corona
        painter.translate(w/2, h/2)
        painter.rotate(math.degrees(parallactic_angle))
        painter.translate(-w/2, -h/2)
        image = QtGui.QImage(result2.data,w,h,QtGui.QImage.Format_ARGB32)
        image = image.rgbSwapped()
        rect = QtCore.QRect(0, 0, RES_X, RES_Y)
        painter.drawImage(rect, image, rect)
        painter.end()
        self.fbo.release()
