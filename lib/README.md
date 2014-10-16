Goal
====
Fine grained (centimeter-level granularity) control of the crazyflie in non-
isolated environment (i.e. in a reasonably controlled but not sterile room)

Sub-goals
=========
1. Hold Position
2. Do a Flip (or figure eight)
3. Go to specified position

Approach
========
Currently we intend to use external vision assistance (cameras on phones/
laptops), but are open to using other sensors if they make sense, e.g:

* Camera (on-board): purchase, soldering, comms.
* Kinect: get it from Kenji
* Sonar: too-heavy 
* GPS: insufficient resolution

Todo
====
* Better vision tracking -- current SimpleCV color tracking is pretty noisy
