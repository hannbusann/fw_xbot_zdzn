#!/usr/bin/env python
#coding=utf-8
#
#
import yaml

offset = (345,875)
pi=3.1415926
A={'time':307,'interupt':134,'audio':'1A.wav','text':'模型有费点有星点,解决方法,max中选择非四边面检查,还有可以导出BOJ的时候选择导出四边形,看看有错误没。'}

P=[]
for i in range(0,10):
	x=i/0.05+offset[0]
	y=i/0.05+offset[1]
	theta=i*pi/16
	p={'pose':(x,y,theta),'abstract':'this is iscas museum!','plan':{'A':A,'B':A,'C':A}}
	P.append(p)

Route = {
		'R15':{'time':15,'length':10,'start':P[0],'end':P[9],'Line':P},
		'R20':{},
		'R30':{}
		}

f=open('route.yaml','w')
yaml.dump(Route,f)
f.close()