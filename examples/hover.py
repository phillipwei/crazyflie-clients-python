#!/usr/bin/python

# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2014 Bitcraze AB
#
#  Crazyflie Nano Quadcopter Client
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA  02110-1301, USA.

"""
- lift to target
- hovers
- lands
- enter to kill
"""

import time, sys
from threading import Thread

#FIXME: Has to be launched from within the example folder
sys.path.append("../lib")
import cflib
from cflib.crazyflie import Crazyflie
from cfclient.utils.logconfigreader import LogConfig

import logging
logging.basicConfig(level=logging.ERROR)

import SimpleCV

class HoverExample:    
    def __init__(self, link_uri):
        """ global loop vars """
        self._exit = False

        """ camera setup """
        cam_ip = raw_input("Specify camera; enter for webcam, or ip of network :\n")
        if cam_ip is '':
            self._cam = SimpleCV.Camera()
        elif '.' not in cam_ip:
            self._cam = SimpleCV.JpegStreamCamera("http://192.168.1." + cam_ip + ":8080/video")
        else:
            self._cam = SimpleCV.JpegStreamCamera("http://" + cam_ip + ":8080/video")

        self._img_floor_accepted = False
        self._img_ceiling_accepted = False
        self._img_height_accepted = False
        self._img_floor_y = 0
        self._img_ceiling_y = 0
        self._img_max_height = 1.82 # six feet in meters
        self._img_size = (800,600)
        self._img_color = SimpleCV.Color.RED
        self._img_blob_min = 10
        self._img_blob_max = 10000
        self._img_log_path = '/tmp/hover.img.log'
        
        # start the vision loop -- will need to initialize though
        Thread(target=self._vision_loop).start()
        
        raw_input("Acquiring floor reading.  Press any key to accept\n")
        self._img_floor_accepted = True
        self._img_floor_y = self._img_pos.y
        
        raw_input("Acquiring ceiling reading.  Press any key to accept\n")
        self._img_ceiling_accepted = True
        self._img_ceiling_y = self._img_pos.y
        
        height = raw_input("Enter the height from floor to ceiling; enter to assume {0}\n"\
                .format(self._img_max_height))
        if height is not '':
            self._img_max_height = height
        self._img_height_accepted = True

        raw_input("Press any key to begin Crazyflie initiation code.")

        """ Initialize and run the example with the specified link_uri """

        self._cf = Crazyflie()
        self._cf.connected.add_callback(self._connected)
        self._cf.disconnected.add_callback(self._disconnected)
        self._cf.connection_failed.add_callback(self._connection_failed)
        self._cf.connection_lost.add_callback(self._connection_lost)

        self._hover_target = 1
        self._flight_time = 10
        self._flight_log_path = "/tmp/hover.log"

        self._asl = 0
        self._alt_accepted = False

        print "Connecting to %s" % link_uri
        
        self._cf.open_link(link_uri)

        raw_input("Acquiring altitude reading.  Press any key to accept\n")
        self._alt_accepted = True

        raw_input("Beginning hover.  Press any key to stop\n")
        self._exit = True

    def _connected(self, link_uri):
        """ This callback is called form the Crazyflie API when a Crazyflie
        has been connected and the TOCs have been downloaded."""
        print "Connected to %s" % link_uri

        self._log = LogConfig(name="Stabilizer", period_in_ms=10)
        self._log.add_variable("baro.aslRaw", "float")

        self._cf.log.add_config(self._log)
        if self._log.valid:
            self._log.data_received_cb.add_callback(self._log_data)
            self._log.error_cb.add_callback(self._log_error)
            self._log.start()
        else:
            print("Could not add logconfig -- TOC?")
        
        Thread(target=self._hover_loop).start()
        
    def _log_data(self, timestamp, data, logconf):
        self._asl = data["baro.aslRaw"]
        # print "[%d][%s]: %s" % (timestamp, logconf.name, self._asl)

    def _log_error(self, logconf, msg):
        print "Error when logging %s: %s" % (logconf.name, msg)

    def _connection_failed(self, link_uri, msg):
        """Callback when connection initial connection fails (i.e no Crazyflie
        at the speficied address)"""
        print "Connection to %s failed: %s" % (link_uri, msg)

    def _connection_lost(self, link_uri, msg):
        """Callback when disconnected after a connection has been made (i.e
        Crazyflie moves out of range)"""
        print "Connection to %s lost: %s" % (link_uri, msg)

    def _disconnected(self, link_uri):
        """Callback when the Crazyflie is disconnected (called in all cases)"""
        print "Disconnected from %s" % link_uri

    def _vision_loop(self):
        log = open(self._img_log_path, 'w', 0)
        while not self._exit:
            img = self._cam.getImage()
            
            # image adjustments
            if self._img_size:
                img = img.resize(self._img_size[0], self._img_size[1])

            # blob search
            color = img - img.colorDistance(self._img_color)
            blobs = color.findBlobs(-1, self._img_blob_min, self._img_blob_max)
            
            # blob draw
            if blobs is not None:
                self._img_pos = blobs[-1]
                roiLayer = SimpleCV.DrawingLayer((img.width, img.height))
                for blob in blobs:
                    blob.draw(layer=roiLayer)
                roiLayer.circle((self._img_pos.x,self._img_pos.y), 50, SimpleCV.Color.RED, 2)
                img.addDrawingLayer(roiLayer)
                blobs.draw(SimpleCV.Color.GREEN, 1)
            img = img.applyLayers()
            img.show()

            # height determination
            if self._img_floor_accepted and\
                self._img_ceiling_accepted and\
                self._img_height_accepted:
                dy = self._img_pos.y - self._img_floor_y
                ypct = dy / (self._img_ceiling_y - self._img_floor_y)
                self._img_height = ypct * self._img_max_height
                log.write("{x},{y},{h}\n"\
                   .format(x=self._img_pos.x,y=self._img_pos.y,h=self._img_height))

        log.close()

    def _hover_loop(self):
        # aquire asl_start over first 3 seconds -- 30 samples
        asl_start = 0
        asl_readings = 0
        while not self._alt_accepted or asl_readings == 0:
            time.sleep(0.01)
            asl_start += self._asl
            asl_readings += 1
            print "\rAltitude reading = %s (#%d, last=%s)" % (asl_start / asl_readings, asl_readings, self._asl),
        asl_start = asl_start / asl_readings

        # print out
        print ""
        print ""
        print "Starting altitude = %s" % asl_start
        asl_target = asl_start + self._hover_target
        print "Hover target = %s" % self._hover_target
        print "Target altitude = %s" % asl_target
        print "Flight time = %s" % self._flight_time

        # flight loop
        flight_time_start = time.time()
        control_time_last = 0
        hover_thrust = 37300
        corrective_thrust = 3000
        while time.time() - flight_time_start < 10 and not self._exit:
            if time.time() - control_time_last > 0.01: # control at most every 10ms
                control_time_last = time.time()
                asl_diff = asl_target - self._asl

                # lift off speed
                if asl_diff > 0.6:
                    thrust = 42000
                # come down speed
                elif asl_diff < -25:
                    thrust = 25000
                # get to hover point
                else: 
                    thrust = hover_thrust + asl_diff * corrective_thrust
                    # update our concept of what hover thrust is
                print "%s : %s (last=%s)" % (asl_diff, thrust, self._asl)
                self._cf.commander.send_setpoint(0,0,0,thrust)

                # upwards corrections seem fine
                # drift down seems worse
                # 
        print "Killing Thrust"
        self._cf.commander.send_setpoint(0,0,0,0)
        time.sleep(1)

        print "Stopped."
        self._cf.close_link()

        '''
        thrust_mult = 1
        thrust_step = 500
        thrust = 20000
        pitch = 0
        roll = 0
        yawrate = 0
        while thrust >= 20000:
            self._cf.commander.send_setpoint(roll, pitch, yawrate, thrust)
            time.sleep(0.1)
            if thrust >= 25000:
                thrust_mult = -1
            thrust += thrust_step * thrust_mult
        self._cf.commander.send_setpoint(0, 0, 0, 0)
        # Make sure that the last packet leaves before the link is closed
        # since the message queue is not flushed before closing
        time.sleep(0.1)
        self._cf.close_link()
        '''

if __name__ == '__main__':
    # Initialize the low-level drivers (don't list the debug drivers)
    cflib.crtp.init_drivers(enable_debug_driver=False)

    # Scan for Crazyflies and use the first one found
    print "Scanning interfaces for Crazyflies..."
    available = cflib.crtp.scan_interfaces()
    print "Crazyflies found:"
    for i in available:
        print i[0]

    le = HoverExample(None)

    if len(available) > 0:
        le = HoverExample(available[0][0])
    else:
        print "No Crazyflies found, cannot run example"
