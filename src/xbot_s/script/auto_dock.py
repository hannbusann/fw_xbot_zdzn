#!/usr/bin/env python
#coding=utf-8

import rospy,os
from sensor_msgs import LaserScan




class AutoDock():
	"""docstring for AutoDock"""
	def __init__(self):
		self.laser_sub = rospy.Subscriber('/scan', LaserScan, self.laser_scanCB)
		


		rospy.spin()

	def laser_scanCB(self,msg):
		self.laser_data = LaserScan()
		self.laser_data = msg
		self.data_len = (int)((self.laser_data.angle_max-self.laser_data.angle_min)/self.laser_data.angle_increment)
		self.data_width = len(self.laser_data.ranges)
		print self.data_len self.data_width



if __name__ == '__main__':
	rospy.init_node('auto_dock')
	try:
		rospy.loginfo('auto_dock initialized...')
		office_slam()
	except rospy.ROSInterruptException:
		rospy.loginfo('auto_dock initialize failed, please retry...')

