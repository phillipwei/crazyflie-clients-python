#!/usr/bin/python

"""
simple program to test that all the wiring is correct;
* run camera capture in it's own thread; update altitude
* run hover loop in it's own thread; output altitude
"""

""" core imports """
import logging, sys, time, threading

""" library imports """
import SimpleCV

""" setup logging; also define logger for this file """
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class Hover:    
    def __init__(self):
        self.initControl()
        self.initCamera()
        self.initTracking()

    """ setup control variables """
    def initControl(self):
        self.exit = False

    """ setup camera """
    def initCamera(self):
        # todo: should keep track of last entry and enter should do that, not webcam
        camIp = raw_input("Specify camera; enter for webcam, or ip of network camera:\n")
        logger.info("Camera specified as '{camIp}'".format(camIp=camIp))

        if camIp is '':
            self.cam = SimpleCV.Camera()
        elif '.' not in camIp:
            self.cam = SimpleCV.JpegStreamCamera("http://192.168.1." + camIp + ":8080/video")
        else:
            self.cam = SimpleCV.JpegStreamCamera("http://" + camIp + ":8080/video")

        self.camRes = (800,600)
        logging.info("Camera resolution={res}".format(res=self.camRes))

    """ setup tracking """
    def initTracking(self):
        self.trackingColor = SimpleCV.Color.RED
        self.trackingBlobMin = 10
        self.trackingBlobMax = 5000
        self.y = -1
        logger.info("Tracking color={trackingColor}; blobMin={blobMin}; blobMax={blobMax}"\
                .format(trackingColor=self.trackingColor, blobMin=self.trackingBlobMin, blobMax=self.trackingBlobMax))

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
            blobs = colorDiff.findBlobs(-1, self.trackingBlobMin, self.trackingBlobMax)
            
            # blob find
            if blobs is not None:
                self.y = blobs[-1]
                print blobs[-1]

            # blob show
            """
            if show:
                if blobs is not None:
                    roiLayer = SimpleCV.DrawingLayer((img.width, img.height))
                    for blob in blobs:
                        blob.draw(layer=roiLayer)
                    roiLayer.circle((self._img_pos.x,self._img_pos.y), 50, SimpleCV.Color.RED, 2)
                    img.addDrawingLayer(roiLayer)
                    blobs.draw(SimpleCV.Color.GREEN, 1)
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
