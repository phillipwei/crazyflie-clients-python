#!/usr/bin/python

import logging

from SimpleCv import Camera, JpegStreamCamera

logger = logging.getLogger()

class VisionTracking:
    def __init__(self):
        logger.info("{name} init()".format(name=self.__class__.__name__))
        self.initCamera()

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
        logger.info("Camera resolution={res}".format(res=self.camRes))
