#!/usr/bin/env python
# coding=utf-8
######################################################################################
#> File Name: cycle_maze.py
#> Author:Rocwang 
#> Mail: yowlings@gmail.com;
#> Github:https://github.com/yowlings
#> Created Time: 2018年08月01日 星期三 16时55分07秒
######################################################################################
import rospy, yaml, os, thread, time

from std_msgs.msg import String, UInt32
from geometry_msgs.msg import Pose, PoseStamped
from actionlib_msgs.msg import GoalStatusArray
from move_base_msgs.msg import MoveBaseActionResult
from std_srvs.srv import Empty

class office_slam():
	"""docstring for office_slam"""
	def __init__(self):
#       声明节点订阅与发布的消息
#       
		self.goal_name_sub = rospy.Subscriber('/office/goal_name', String, self.goal_nameCB)
		self.move_base_goal_pub = rospy.Publisher('/move_base_simple/goal', PoseStamped, queue_size=1)
		self.move_base_result_sub = rospy.Subscriber('/move_base/result', MoveBaseActionResult, self.move_base_resultCB)
		self.clear_costmaps_srv = rospy.ServiceProxy('/move_base/clear_costmaps',Empty)
#        每一个讲解点的名字:位置字典
		self.position_dict = dict()
#        记录机器人当前的目标点
		self.current_goal = "middle"
		self.last_goal = "origin"
#        循环次数,原本是想使用逐次累加的方式计数
#        现在已改为255表示进行新的一轮循环讲解,200表示语音未识别,开启摄像头确认交互人是否还在,在的话进行继续交互
		self.loop_tag = UInt32()
#        读取一存储的讲解点字典文件,默认位于xbot_s/param/position_dic.yaml文件
		yaml_path = rospy.get_param('/cycle/position_dict_path','/home/xbot/catkin_ws/src/xbot_s/param/cycle_maze.yaml')
#		yaml_path = yaml_path + '/scripts/position_dic.yaml'
		f = open(yaml_path, 'r')
		self.position_dict = yaml.load(f)
		f.close()
		# self.make_launch()
		cmd = 'rostopic pub -1 /office/next_loop std_msgs/UInt32 "data: 255" '
		# os.system(cmd)
		rospy.spin()

	#    收到目标点名之后查字典得到位置坐标,然后发布给导航程序
	def goal_nameCB(self, name):
		if name.data != "nothing":
			self.pubGoalName(name.data)
		else:
			pass

	def pubGoalName(self, name):
		pos = self.position_dict[name]
		goal = PoseStamped()
		goal.header.frame_id = 'map'
		goal.pose.position.x = pos[0][0]
		goal.pose.position.y = pos[0][1]
		goal.pose.position.z = pos[0][2]
		goal.pose.orientation.x = pos[1][0]
		goal.pose.orientation.y = pos[1][1]
		goal.pose.orientation.z = pos[1][2]
		goal.pose.orientation.w = pos[1][3]
		self.clear_costmaps_srv()
		self.move_base_goal_pub.publish(goal)



#    导航程序对前往目标点的执行结果
	def move_base_resultCB(self, result):
		if result.status.status == 3:
#            成功到达目标点
			if self.current_goal == "origin" or self.current_goal == "end":
				self.pubGoalName("middle")
				self.last_goal = self.current_goal
				self.current_goal = "middle"
			elif self.current_goal =="middle":
				if self.last_goal =="origin":
					self.pubGoalName("end")
					self.last_goal = self.current_goal
					self.current_goal = "end"
				else:
					self.pubGoalName("origin")
					self.last_goal = self.current_goal
					self.current_goal = "origin"
		elif result.status.status == 4:
#			到达目标点失败,slam发布abort信号给talker,talker会请求前方人员让一下,然后重新规划路径尝试去往目标点
			self.pubGoalName(self.current_goal)


if __name__ == '__main__':
	rospy.init_node('cycle_maze')
	try:
		rospy.loginfo('cycle maze node initialized...')
		office_slam()
	except rospy.ROSInterruptException:
		rospy.loginfo('cycle maze node failed, please retry...')

