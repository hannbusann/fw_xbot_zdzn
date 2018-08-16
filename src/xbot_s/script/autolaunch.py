#!/usr/bin/env python
#coding=utf-8

import rospy,os
from std_msgs.msg import UInt32


class AutoLaunch():
	"""docstring for AutoLaunch"""
	def __init__(sel):
		self.launch_pub = rospy.Publiser('/office/next_loop',UInt32,queue_size=1)
		