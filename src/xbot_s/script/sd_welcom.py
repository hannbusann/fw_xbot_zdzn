#!/usr/bin/env python
#coding=utf-8

# some base libs
import numpy as np
import cv2, os, time, base64, urllib2, rospy
from json import *
# ros msg
from xbot_msgs.msg import FaceResult
from std_msgs.msg import String, UInt32
#人脸识别盒子的IP地址以及接口,详见doc中的天眼魔盒API文档
url = "http://192.168.8.141:8000/recognition"



class face_recog():
	"""docstring for face_recog"""
	def __init__(self):
#       声明节点订阅与发布的消息
		self.face_result_pub = rospy.Publisher('/office/face_result',FaceResult,queue_size=1)
		self.next_loop_sub = rospy.Subscriber('/office/next_loop',UInt32, self.next_loopCB)
		rospy.spin()




#    下一循环讲解触发函数
	def next_loopCB(self, loop_count):
#        先打开摄像头
		cap = cv2.VideoCapture(0)
		msg = FaceResult()
#        如果消息为255,则正常开启人脸识别等待人脸介入
		if loop_count.data == 255:##got back to origin, start next loop
			last_face = None
			times_face = 0
			times_unknown = 0
			while True:
#               捕获当前帧,存入当前路径下的tmp.jpg文件
				ret, frame = cap.read()
				if ret:
					cv2.imwrite('tmp.jpg',frame)
#                打开缓存图像文件编码后发送给盒子服务器进行识别,返回识别结果
				with open("tmp.jpg", "rb") as fp:
					image_binary = fp.read()
					image_binary = base64.b64encode(image_binary)
					post_data = {"Image":image_binary}
					body = JSONEncoder().encode(post_data)
					req = urllib2.Request(url, body)
					response = urllib2.urlopen(req).read()
					body = JSONDecoder().decode(response)
					rospy.loginfo(body)
#                如果没有检测到人脸,人脸次数重置,
				if body['Id'] == 'UNKNOWN' or body['Id'] == 'None':#no people in frame
					times_face = 0
					times_unknown = 0
					continue
#                检测到已注册人脸,人脸次数+1,继续,连续累积次数(中间不出现重置)大于10则确认该识别结果
				elif body['Confidence'] >0.6:#registered people in frame
					times_unknown = 0
					if body['Id'] == 'minister':
						times_face = times_face +1
					else:
						times_face = 0
						continue
					if times_face >= 3:
						msg.is_staff = 0
						msg.name = 'minister'
#                        发布该人姓名给talker开始注册用户交互
						self.face_result_pub.publish(msg)
						last_face = body['Id']
						break
#                有人脸出现但是没有注册,则未知人脸次数+1,继续,连续累积次数(中间不出现重置)大于10则确认该识别结果
				else:#unregistered people in frame
					pass
#       如果消息为200,则表示talker在交互过程中未识别到用户的语音输入,开启人脸验证确认用户是否还在面前(排除噪声的影响)
#       确认时间为3秒,3秒都没有人脸,则确认用户不在.确认用户还在,则提醒对方重新说一下,如果不在,则取消交互,进入等待人脸介入环节.
#        TODO:有人的话确认是否为本轮交互的同一人.
		else:
			pass



if __name__ == '__main__':
	rospy.init_node('face_recog')
	try:
		rospy.loginfo('face recogition initialized...')
		face_recog()
	except rospy.ROSInterruptException:
		rospy.loginfo('face recogition initialize failed, please retry...')

