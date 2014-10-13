#!/usr/bin/python

import logging
import sys
import threading
import time

from SimpleCV import Camera, Color, JpegStreamCamera

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class Hover:
    """Uses vision tracking and PID-control to hover at a given altitude

    1. Run camera capture in it's own thread; update altitude
    2. Run hover loop in it's own thread; output altitude
    """

    def __init__(self):
        self.initControl()
        self.initCamera()
        self.initTracking()

    def initControl(self):
        """Setup control-flow variables"""
        self.exit = False

    def initCamera(self):
        """Setup camera variables

        Will prompt the user for feedback.  Capable of loading webcam or an
        ip-camera streaming JPEG
        """
        # TODO: Track last camera mode; use 'Enter' to repeat that
        camIp = raw_input("Specify camera; enter for webcam, " +
                          "or ip of network camera:\n")
        logger.info("Camera specified as '{camIp}'".format(camIp=camIp))

        if camIp is '':
            self.cam = Camera()
        elif '.' not in camIp:
            self.cam = JpegStreamCamera("http://192.168.1.{ip}:8080/video"
                                        .format(ip=camIp))
        else:
            self.cam = JpegStreamCamera("http://{ip}:8080/video"
                                                 .format(ip=camIp))

        self.camRes = (800,600)
        logging.info("Camera resolution={res}".format(res=self.camRes))

    """ setup tracking """
    def initTracking(self):
        self.trackingColor = Color.RED
        self.trackingBlobMin = 10
        self.trackingBlobMax = 5000
        self.y = -1
        logger.info("Tracking color={color}; blobMin={min}; blobMax={max}"
                    .format(color=self.trackingColor,
                            min=self.trackingBlobMin,
                            max=self.trackingBlobMax))

    def visionLoop(self):
        while not self.exit:
            # acquire image
            img = self.cam.getImage()
            
            # exit if we've got nothing
            if img is None:
                break

            # adjust image
            img = img.resize(self.camRes[0], self.camRes[1])
            img = img.rotate90()

            # blob search
            colorDiff = img - img.colorDistance(self.trackingColor)
            blobs = colorDiff.findBlobs(-1, self.trackingBlobMin, 
                                        self.trackingBlobMax)
            
            # blob find
            if blobs is not None:
                self.y = blobs[-1]
                print blobs[-1]

            # blob show
            """
            if show:
                if blobs is not None:
                    roiLayer = DrawingLayer((img.width, img.height))
                    for blob in blobs:
                        blob.draw(layer=roiLayer)
                    roiLayer.circle((self._img_pos.x,self._img_pos.y), 50, 
                                    Color.RED, 2)
                    img.addDrawingLayer(roiLayer)
                    blobs.draw(Color.GREEN, 1)
                img = img.applyLayers()
                img.show()
            """
            img.show()

            logger.debug("y = {y}".format(y=self.y))

    def start(self):
        threading.Thread(target=self.visionLoop).start()
        raw_input("Press any key to stop")
        self.exit = True

if __name__ == '__main__':
    hover = Hover()
    hover.start()
