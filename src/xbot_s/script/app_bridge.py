#!/usr/bin/env python
#coding=utf-8

import rospy,numpy
from xbot_s.msg import XbotPose
from nav_msgs.msg import OccupancyGrid
from nav_msgs.srv import GetMap
from std_srvs.srv import Empty
from geometry_msgs.msg import *
from tf.transformations import *
# clear_costmaps_srv = rospy.ServiceProxy('/move_base/clear_costmaps',Empty)
# resp1 = clear_costmaps_srv()

class xbot_app_bridge():
	"""docstring for xbot_app_bridge"""
	def __init__(self):
		# 订阅机器人在世界当中的位置,由amcl发布的实时位置
		self.amcl_pose_sub = rospy.Subscriber("/amcl_pose",PoseWithCovarianceStamped,self.amcl_poseCB)
		# 订阅由用户在app上选点模式中点击地图图片所产生的图片坐标,以图片的左下角为坐标轴,得到(x,y,theta)
		self.image_pose_sub = rospy.Subscriber("/app/image_pose",XbotPose,self.image_poseCB)
		# 发布给APP的机器人当前的位置,该位置由amcl_pose转换而来,用于可视化中机器人位置的实时更新显示
		self.xbot_pose = rospy.Publisher('/app/xbot_pose', XbotPose, queue_size=10)
		self.orientation_quat = Quaternion()
		rospy.spin()


	def image_poseCB(self,msg):
		pass



	def amcl_poseCB(self,msg):
		self.orientation_quat = (
			msg.pose.pose.orientation.x,
			msg.pose.pose.orientation.y,
			msg.pose.pose.orientation.z,
			msg.pose.pose.orientation.w)
		euler = euler_from_quaternion(self.orientation_quat)
		roll = euler[0]
		pitch = euler[1]
		yaw = euler[2]
		pose_msg = XbotPose()
		pose_msg.header.stamp = rospy.Time.now()
		pose_msg.x = msg.pose.pose.position.x
		pose_msg.y = msg.pose.pose.position.y
		pose_msg.theta = yaw
		self.xbot_pose.publish(pose_msg)



if __name__ == '__main__':
	rospy.init_node('xbot_app_bridge')
	try:
		rospy.loginfo('office slam initialized...')
		xbot_app_bridge()
	except rospy.ROSInterruptException:
		rospy.loginfo('office slam initialize failed, please retry...')


