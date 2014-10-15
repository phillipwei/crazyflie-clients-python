#!/usr/bin/python

from datetime import datetime
import inspect
import logging
import shelve
import sys
import threading
from time import sleep
from Queue import Queue

from SimpleCV import Camera, Color, DrawingLayer, JpegStreamCamera

from cflib.crazyflie import Crazyflie
from cflib.crtp import init_drivers as InitDrivers
from cflib.crtp import scan_interfaces as Scan

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

""" File handler for everything """
fh = logging.FileHandler('/tmp/hover.log')
fh.setLevel(logging.DEBUG)

""" Console handler for info+ """
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

""" Format w/ timestamp """
formatter = logging.Formatter("%(asctime)s::%(name)s::%(levelname)s::" +
                              "%(message)s")
fh.setFormatter(formatter)
ch.setFormatter(formatter)

""" Wire up logging """
logger.addHandler(ch)
logger.addHandler(fh)

class Hover:
    """Uses vision tracking and PID-control to hover at a given altitude

    1. Run camera capture in it's own thread; update altitude
    2. Run hover loop in it's own thread; output altitude
    """

    def __init__(self):
        logger.info("{name} init()".format(name=self.__class__.__name__))
        self.initControl()
        self.initCamera()
        self.initTracking()
        self.initHover()
        self.initCF()

    def initControl(self):
        """Setup control-flow variables"""
        self.exit = False

    def initCamera(self):
        """Setup camera variables

        Will prompt the user for feedback.  Capable of loading webcam or an
        ip-camera streaming JPEG.  Uses shelve to remember last entered
        value
        """
        
        # fetch settings
        settings = shelve.open('/tmp/hover.settings')
        lastCamIp = settings.get('camIp')

        # prompt for input
        if lastCamIp:
            camIp = raw_input("Specify camera: 'cam' for webcam, " +
                              "an ip of network camera or <ENTER> for the " +
                              "previous value of '{lastCamIp}':\n"
                              .format(lastCamIp=lastCamIp))
        else:
            camIp = raw_input("Specify camera: 'cam' for webcam or " +
                              "an ip of network camera")

        logger.info("Camera specified as '{camIp}'".format(camIp=camIp))
        
        # save settings
        settings['camIp'] = camIp

        # setup camera
        if camIp == "cam":
            self.cam = Camera()
        elif '.' not in camIp:
            self.cam = JpegStreamCamera("http://192.168.1.{ip}:8080/video"
                                        .format(ip=camIp))
        else:
            self.cam = JpegStreamCamera("http://{ip}:8080/video"
                                        .format(ip=camIp))

        # additional values -- for now, just hard coded
        self.camRes = (800,600)
        logger.info("Camera resolution={res}".format(res=self.camRes))

    """ setup tracking """
    def initTracking(self):
        self.trackingColor = Color.BLUE
        self.trackingBlobMin = 5
        self.trackingBlobMax = 1000
        self.x = -1
        self.y = -1
        self.target = (300,400)
        logger.info(("Tracking color={color}; min={min}; max={max}; " +
                     "target={target}")
                    .format(color=self.trackingColor,
                            min=self.trackingBlobMin,
                            max=self.trackingBlobMax,
                            target=self.target))
        self.trackingFrameQ = Queue()

    def initHover(self):
        self.hoverFrames = []
        self.eSum = 0

    def initCF(self):
        self.cfConnected = False
        self.cf = None
        self.cfUri = None

        logger.debug("Initializing Drivers; Debug=FALSE")
        InitDrivers(enable_debug_driver=False)

        logger.info("Scanning")
        available = Scan()

        logger.info("Found:")
        for cf in available:
            logger.debug(cf[0])
        
        if len(available) > 0:
            self.cfUri = available[0][0]
            self.cf = Crazyflie()
            self.cf.connected.add_callback(self.cfOnConnected)
            self.cf.disconnected.add_callback(self.cfOnDisconnected)
            self.cf.connection_failed.add_callback(self.cfOnFailed)
            self.cf.connection_lost.add_callback(self.cfOnLost)
            logger.info("Crazyflie @{uri} Initialized".format(uri=self.cfUri)) 
        else:
            logger.info("No Crazyflies found")
    
    def cfOnConnected(self, uri):
        logger.info("{func} {uri}".format(func=inspect.stack()[0][3], uri=uri))
        self.cfConnected = True

    def cfOnDisconnected(self, uri):
        logger.info("{func} {uri}".format(func=inspect.stack()[0][3], uri=uri))
        self.cfConnected = False

    def cfOnFailed(self, uri):
        logger.info("{func} {uri}".format(func=inspect.stack()[0][3], uri=uri))

    def cfOnLost(self, uri, msg):
        logger.info("{func} {uri} {msg}".format(func=inspect.stack()[0][3], 
                                                uri=uri, msg=msg))

    def visionLoop(self):
        while not self.exit:
            # acquire image
            img = self.cam.getImage()
            
            # exit if we've got nothing
            if img is None:
                break

            # adjust image
            '''
            img = img.resize(self.camRes[0], self.camRes[1])
            img = img.rotate90()
            '''
            img = img.rotate90()

            # blob search
            colorDiff = img - img.colorDistance(self.trackingColor)
            blobs = colorDiff.findBlobs(-1, self.trackingBlobMin, 
                                        self.trackingBlobMax)
            '''
            blobs = img.findBlobs((255,60,60), self.trackingBlobMin,
                                  self.trackingBlobMax)
            '''

            # blob find
            if blobs is not None:
                self.x = blobs[-1].x
                self.y = blobs[-1].y

            # blob show
            if blobs is not None:
                # roi = region of interest
                roiLayer = DrawingLayer((img.width, img.height))
                
                # draw all blobs
                for blob in blobs:
                    blob.draw(layer=roiLayer)
                
                # draw a circle around the main blob
                roiLayer.circle((self.x,self.y), 50, Color.RED, 2)

                # apply roi to img
                img.addDrawingLayer(roiLayer)
                img = img.applyLayers()
            
            img.show()

            # fps
            now = datetime.utcnow()
            self.trackingFrameQ.put(now)
            if self.trackingFrameQ.qsize() < 30:
                fps = 0.0
            else:
                fps = 30.0/(now - self.trackingFrameQ.get()).total_seconds()

            # logging
            logger.debug("{func} ({x},{y}) {fps:5.2f}"
                         .format(func=inspect.stack()[0][3],
                                 x=self.x, y=self.y, fps=fps))
        # loop has ened
        logger.debug("{func} stopped.".format(func=inspect.stack()[0][3]))

    def hoverLoop(self):
        while not self.exit:
            # hover throttled to camera frame rate
            sleep(1.0/30.0)

            # fps
            now = datetime.utcnow()
            self.hoverFrames.append(now)
            if len(self.hoverFrames) < 30:
                fps = 0.0
            else:
                fps = 30.0/(now - self.hoverFrames[-30]).total_seconds()
            
            # pid variables
            kp = (3000.0/400.0)
            ki = 0.18

            # determine immediate error e
            e = self.y - self.target[1]
            
            # determine accumulated errors eSum
            if len(self.hoverFrames) > 1:
                dt = (now - self.hoverFrames[-2]).total_seconds()
            else:
                dt = 0
            self.eSum = self.eSum + e * dt

            # calculate thrust
            hoverThrust = 37000
            thrust = hoverThrust + (kp * e) + (ki * self.eSum)

            # set the throttle
            self.setThrust(thrust)

            # logging
            logger.debug(("{func} e={e}, dt={dt:0.4f}, eSum={eSum:0.4f}, " +
                          "thrust={thrust},  [{fps:5.2f}]")
                         .format(func=inspect.stack()[0][3],
                                 e=e, dt=dt, eSum=self.eSum, thrust=thrust,
                                 fps=fps)) 
        
        
        # loop has ened
        logger.debug("{func} stopped.".format(func=inspect.stack()[0][3]))

    def setThrust(self, thrust):
        """ sets thrust - but if control has exited, will kill thrust """
        if self.exit:
            thrust = 0
        
        if self.cf is not None:
            self.cf.commander.send_setpoint(0,0,0, thrust)

    def cfOpenLink(self):
        if self.cf is not None:
            self.cf.open_link(self.cfUri)
            logger.info("Linked opened to {uri}".format(uri=self.cfUri))

    def start(self):
        logger.info("Starting VisionLoop")
        threading.Thread(target=self.visionLoop).start()

        logger.info("Starting HoverLoop")
        threading.Thread(target=self.hoverLoop).start()

        logger.info("Opening Crazyflie link")
        self.cfOpenLink()

        raw_input("Press enter to stop")
        self.stop()
        
    def stop(self):
        # kill our loops
        self.exit = True

        # explicitly kill thrust
        self.setThrust(0)

        # kill crazyflie
        if self.cf and self.cfConnected:
            self.cf.close_link()

if __name__ == '__main__':
    hover = Hover()
    hover.start()
