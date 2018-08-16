'''
Created on Jan 27, 2016
version: 1.7.1
modification: 2016-09-08 add config upload and download 
modification: 2016-09-28 update config with rebooting face_tool
modification: 2016-09-28 logoutface:delete 5p image in featpath
modification: 2016-10-10 add udp broadcast
modification: 2016-10-30 add reboot and poweroff function
modification: 2016-11-08 add DetHandler,return image with 5p
modification: 2016-11-18 add logoutall and filter userid in registerhandler
modification: 2016-11-29 fix command:shutdown didnot work, change shutdown now to poweroff
modification: 2016-12-16 add handler:LogHandler, ImgHandler, ResetConfigHanlder, GPIOHandler, sheduler of filtering logs
modification: 2016-12-19 fix scheduler
modification: 2016-12-20 add LogListHandler
modification: 2016-12-30 add function of using httpserver register in rtsp and usb mode
modification: 2017-01-04 add recognizer guardance and the maximum image size obtained from config.txt
@author: adam

modification: 2017-03-01 add uboxtype( if 1 then: return feat while registering elif 0 then just as usual)
modification: 2017-03-11 add max num for registering
modification: 2017-04-01 add handler:WGHandler
modification: 2017-04-18 add handler:DelRecordFacesHandler

'''
#!/usr/bin/python
#-*- encoding:utf-8 -*-
import fcntl
import tornado.ioloop
import tornado.web
import tornado.gen
import tornado.options
import glob
import os
import urllib
import base64
import time
import datetime
import socket
import json
import re
from tornado.options import define, options
import multiprocessing
from PIL import Image
import StringIO
import cmd
import uuid
import socket
import struct
import shutil
import stat
import serial

BASE_PATH = "/home/ubuntu/code/UBox_proj/bin"
#LARGEST_IMG_SIZE = (1280, 960)
UBOX_TYPE=0  #0:normal_ubox  1:ubox for register
USER_MAX=1000
define("port", default=8000, help="run on the given port", type=int)
define("imagepath", default=os.path.join(BASE_PATH, 'loadpath_http'), help="recognized image path", type=str)
define("savepath", default=os.path.join(BASE_PATH, 'savepath_http'), help="result saved path", type=str)
define("resultpath", default=os.path.join(BASE_PATH, 'resultpath'), help="recog image saved path", type=str)
define("facepath", default=os.path.join(BASE_PATH, 'facepath'), help="registered face image path", type=str)
define("featpath", default=os.path.join(BASE_PATH, 'featpath'), help="feature path")
define("newfeatpath", default=os.path.join(BASE_PATH, 'newpath'), help="feature path")
define("imgorgpath", default=os.path.join(BASE_PATH, 'loadpath_register'), help="path of original image to register")
define("img5ppath", default=os.path.join(BASE_PATH, 'savepath_register'), help="path of 5 point image")
define("recogname", default="ubox", help="recognizer name")
define("configpath", default=BASE_PATH, help="path of config.txt")
define("rootpath", default="config.txt", help="path of original config.txt")

NORMAL = 0
TIMEOUT = 1
RESULT_FORMAT_WRONG = 2
ERRCODE_ERROR = 3
SCORE_ERROR = 4
INPUT_ERROR = 5
NO_FACE = 6
FACE_READ_ERROR = 7
BASE64DEC_ERROR = 8
FACEEXTRACT_ERROR = 9
FACEREMOVE_ERROR = 10
IMAGE_TOO_LARGE = 11
FILE_NOT_EXISTS = 12
IMAGE_OPEN_FAIL = 13
FACE_EXISTS = 14
NO_NETCARD = 15
INPUT_INVALID = 16
GPIO_EXEC_FAIL = 17
FILE_READ_FAIL = 18
RESET_CONFIG_FAIL = 2019
CLEAR_FOLDER_FAIL = 2020
LIST_LOGFILE_FAIL = 2021
MAC_NOT_MATCH = 22
INVALID_PASSWORD = 23
USER_TOO_MANY=24
RECORDIMG_REMOVE_ERROR=25

def getFrameSize(configname):
    if not os.path.exists(configname):
        return (1280, 960)
    width = 1280
    height = 960
    with open(configname, 'r') as fp:
        for line in fp:
            tmp = line.split('=')
            if len(tmp) != 2:
                continue
            if tmp[0].strip() == 'frame_width' and tmp[1].strip().isdigit():
                width = int(tmp[1].strip())
            elif tmp[0].strip() == 'frame_height' and tmp[1].strip().isdigit():
                height = int(tmp[1].strip())
    return (width, height)

def getNormalUser():
    string = "1111111111"
    hexInt = hex(int(string))
    mybytes = bytearray(4)
    mybytes[0] = int(hexInt[2:-6], 16)
    mybytes[1] = int(hexInt[-6:-4], 16)
    mybytes[2] = int(hexInt[-4:-2], 16)
    mybytes[3] = int(hexInt[-2:], 16)
    return mybytes

def saveImage(imagebinary, imagename, imagetype, imagepath):
    if (len(imagebinary) == 0 or len(imagename) == 0 
        or len(imagetype) == 0 or len(imagepath) == 0 
        or os.path.isdir(imagepath) == False):
        return False
    name = imagename + '.' + imagetype
    fullname = os.path.join(imagepath, name)
    print "save %s in %s"%(name,fullname)
    with open(fullname, "wb") as fp:
        fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
        fp.write(imagebinary)
    return os.path.isfile(fullname)

def readImage(imagename, imagetype, imagepath):
    imagebinary = str()
    fullname = os.path.join(imagepath, imagename) + '.' + imagetype
    if not os.path.exists(fullname):
        return str()
    with open(fullname, "rb") as fp:
        imagebinary = fp.read()
    return imagebinary
 
def recogParse(strresult):
    retv = {'Id':'None', 'Confidence': 0.0, 'Ret': 0}
    listresult = strresult.split()
    if len(listresult) != 3:
        retv['Ret'] = RESULT_FORMAT_WRONG
        return retv
    pattern = re.compile(r'^[-+]?[0-9]+\.[0-9]+$')
    if not listresult[0].isdigit():
        retv['Ret'] = ERRCODE_ERROR
        return retv
    if not listresult[1].isdigit() and not pattern.match(listresult[1]):
        retv['Ret'] = SCORE_ERROR
        return retv
    retv['Ret'] = int(listresult[0])
    retv['Confidence'] = float(listresult[1])
    retv['Id'] = listresult[2]
    return retv

def veriParse(strresult):
    retv = {'Similarity': 0.0, 'Ret': 0}
    listresult = strresult.split()
    print "listresult:",listresult
    if len(listresult) != 3:
        retv['Ret'] = RESULT_FORMAT_WRONG
        return retv
    pattern = re.compile(r'^[-+]?[0-9]+\.[0-9]+$')
    if not listresult[0].isdigit():
        retv['Ret'] = ERRCODE_ERROR
        return retv
    if not listresult[1].isdigit() and not pattern.match(listresult[1]):
        retv['Ret'] = SCORE_ERROR
        return retv
    print "retv: ",retv
    retv['Ret'] = int(listresult[0])
    retv['Similarity'] = float(listresult[1])
    return retv

def getUserList():
    print "Entering getUserList"
    listname = os.listdir(options.featpath)
    retList = list()
    for name in listname:
        tmp = os.path.splitext(name)
        if tmp[1] == '.feat' and tmp[0]:
            retList.append(tmp[0])
    return retList
'''
def getUserList():
    print "Entering getUserList"
    cmd = "ls %s | awk '{print basename $1}'"%options.facepath
    listname = os.popen(cmd).read().split()
    if(len(listname) == 0):
        return "None"
    retList = list()
    for line in listname:
        retList.append(line.split('.')[0])
    return retList
'''

@tornado.gen.coroutine
def detectFace(imagebinary):
    retv = {'Image':"", 'Ret':NORMAL}
    imagename = str(int(time.time()*1000000))
    saveImage(imagebinary, imagename, 'jpg', options.imgorgpath)
    fullname = os.path.join(options.img5ppath,imagename) + '.txt'
    starttime = time.time()
    thd = 10.0
    while True:
        nowtime = time.time()
        if(nowtime - starttime > thd):
            retv['Ret'] = TIMEOUT
            break
        if(os.path.isfile(fullname)):
            res = str()
            with open(fullname, "r") as fp:
                fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
                res = fp.read().strip()
            os.remove(fullname)
            if res == '0':
                fullname = os.path.join(options.img5ppath, imagename) + '.jpg'
                if os.path.isfile(fullname):
                    imagebinary = str()
                    with open(fullname, "rb") as fp:
                        fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
                        imagebinary = fp.read()
                    retv['Image'] = base64.b64encode(imagebinary)
                    os.remove(fullname)
                else:
                    retv['Ret'] = FACEEXTRACT_ERROR
            else:
                retv['Ret'] = FACEEXTRACT_ERROR
            break 
        time.sleep(0.005)
    return (imagename, retv)

def killRecog():
    procs = os.popen("ps aux | grep -v grep | grep ./%s"%options.recogname,'r').readlines()
    pids = []
    for proc in procs:
        tmp = proc.split()
        if len(tmp)>2 and tmp[-1] == "./%s"%options.recogname:
            pids.append(tmp[1])
    for pid in pids:
        print 'kill -9 %s'%pid
        os.system('kill -9 %s'%pid)

def rebootRecog(pids):
    for pid in pids:
        print 'kill -9 %s'%pid
        os.system('kill -9 %s'%pid)
    procs = os.popen("ps aux | grep -v grep | grep ./%s"%options.recogname,'r').readlines()
    pids = []
    for proc in procs:
        tmp = proc.split()
        if len(tmp)>2 and tmp[-1] == "./%s"%options.recogname:
            pids.append(tmp[1])
    if len(pids) == 0:
        pwd = os.getcwd()
        os.chdir(BASE_PATH)
        os.system('./%s &'%options.recogname)
        os.chdir(pwd)
    

def logoutFace(userid):
    ret = {"Ret": NORMAL}
    try:
        fullname = os.path.join(options.facepath, userid) + '.jpg'
        os.remove(fullname)
        #os.system('rm ' + fullname)
        fullname = os.path.join(options.featpath, userid) + '.feat'
        os.remove(fullname)
        #os.system('rm ' + fullname)
    except Exception,e:
        print e
    userList = getUserList()
    if userid in userList:
        ret["Ret"] = FACEREMOVE_ERROR
    #else:
    #    rebootRecg()
    return ret
def logoutAll():
    ret = {"Ret": NORMAL}
    try:
        filelist = os.listdir(options.facepath)
        for filename in filelist:
            curpath=os.path.join(options.facepath, filename)
            if os.path.isfile(curpath):
                os.remove(curpath)
            else:
                shutil.rmtree(curpath)
        filelist = os.listdir(options.featpath)
        for filename in filelist:
            curpath=os.path.join(options.featpath, filename)    
            if os.path.isfile(curpath):
                os.remove(curpath)
            else:
                os.remove(curpath)
    except Exception,e:
        ret['Ret'] = FACEREMOVE_ERROR
    return ret
@tornado.gen.coroutine
def recognizeFace(imagebinary):
    retv = {'Confidence':0.0, 'Id':'None', 'Ret':0}
    imagename = str(int(time.time()*1000000))
    saveImage(imagebinary, imagename, 'jpg', options.imagepath)
    fullname = os.path.join(options.savepath,imagename)
    starttime = time.time()
    thd = 10.0
    while True:
        nowtime = time.time()
        if(nowtime - starttime > thd):
            retv['Ret'] = TIMEOUT
            break
        if(os.path.isfile(fullname)):
            with open(fullname, "r") as fp:
                fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
                retv = recogParse(fp.read())
            os.remove(fullname)
            break 
        time.sleep(0.005)
    return retv

@tornado.gen.coroutine
def verifyFace(imagebinary, id):
    retv = {'Similarity':0.0, 'Ret':0}
    imagename = str(int(time.time()*1000000)) + '_' + id
    saveImage(imagebinary, imagename, 'jpg', options.imagepath)
    fullname = os.path.join(options.savepath,imagename)
    starttime = time.time()
    thd = 10.0
    while True:
        nowtime = time.time()
        if(nowtime - starttime > thd):
            retv['Ret'] = TIMEOUT
            break
        if(os.path.isfile(fullname)):
            with open(fullname, "r") as fp:
                fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
                retv = veriParse(fp.read())
            os.remove(fullname)
            break 
        time.sleep(0.005)
    return retv



class RecogHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def post(self):
        retv = {'Confidence':0.0, 'Id':'None', 'Ret':INPUT_ERROR}
        dict_json = dict()
        try:
            dict_json = json.loads(self.request.body)
        except:
            retv['Ret'] = INPUT_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        if "Image" in dict_json:
            imagebinary = str()
            try:
                imagebinary = base64.b64decode(dict_json["Image"])
            except:
                retv['Ret'] = BASE64DEC_ERROR
                self.write(json.dumps(retv, sort_keys=True, indent=4))
                self.finish()
                return
            try:
                img = Image.open(StringIO.StringIO(imagebinary))
                print img.size
                if img.size[0] > LARGEST_IMG_SIZE[0] or img.size[1] > LARGEST_IMG_SIZE[1]:
                    retv["Ret"] = IMAGE_TOO_LARGE
                    self.write(json.dumps(retv, sort_keys=True, indent=4))
                    self.finish()
                    return
            except:
                retv['Ret'] = IMAGE_OPEN_FAIL
                self.write(json.dumps(retv, sort_keys=True, indent=4))
                self.finish()
                return
            #retv = recognizeFace(imagebinary)
            retv = yield tornado.gen.Task(recognizeFace, imagebinary)
        self.write(json.dumps(retv, sort_keys=True, indent=4))
        self.finish()
        return
    
    
class VeriHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def post(self):
        retv = {'Similarity':0.0, 'Ret':NORMAL}
        dict_json = dict()
        try:
            dict_json = json.loads(self.request.body)
        except:
            retv['Ret'] = INPUT_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        if "Image" in dict_json and "Id" in dict_json:
            imagebinary = str()
            try:
                imagebinary = base64.b64decode(dict_json["Image"])
            except:
                retv['Ret'] = BASE64DEC_ERROR
                self.write(json.dumps(retv, sort_keys=True, indent=4))
                self.finish()
                return
            try:
                img = Image.open(StringIO.StringIO(imagebinary))
                print img.size
                if img.size[0] > LARGEST_IMG_SIZE[0] or img.size[1] > LARGEST_IMG_SIZE[1]:
                    retv["Ret"] = IMAGE_TOO_LARGE
                    self.write(json.dumps(retv, sort_keys=True, indent=4))
                    self.finish()
                    return
            except:
                retv['Ret'] = IMAGE_OPEN_FAIL
                self.write(json.dumps(retv, sort_keys=True, indent=4))
                self.finish()
                return
            id = dict_json["Id"]
            #retv = verifyFace(imagebinary, id)
            retv = yield tornado.gen.Task(verifyFace, imagebinary, id)
        self.write(json.dumps(retv, sort_keys=True, indent=4))
        self.finish()
        return

class FaceHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        retv = {"Image":"", "Ret": NORMAL}
        userid = self.get_argument('userid','')
        if not userid:
            retv["Ret"] = INPUT_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        fullname = os.path.join(options.facepath, userid)
        imglist = os.popen("ls %s.jpg"%fullname).readlines()
        if not imglist:
            retv["Ret"] = NO_FACE
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        imagebinary = str()
        fullname = imglist[0].strip()
        with open(fullname, "rb") as fp:
            imagebinary = fp.read()
        if not imagebinary:
            retv["Ret"] = FACE_READ_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        imagebinary = base64.b64encode(imagebinary)
        retv["Image"] = imagebinary
        self.write(json.dumps(retv, sort_keys=True, indent=4))
        self.finish()
        return

class DetHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def post(self):
        retv = {"Image":"", "Ret": NORMAL}
        dict_json = dict()
        try:
            dict_json = json.loads(self.request.body)
        except:
            retv['Ret'] = INPUT_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        #dict_json = {'Image':base64}    
        if 'Image' not in dict_json:
            retv["Ret"] = INPUT_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        if not dict_json['Image']:
            retv["Ret"] = INPUT_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        imagebinary = str()
        try:
            imagebinary = base64.b64decode(dict_json["Image"])
        except:
            retv['Ret'] = BASE64DEC_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        print "image size=",len(imagebinary)
        try:
            img = Image.open(StringIO.StringIO(imagebinary))
            print img.size
            if img.size[0] > LARGEST_IMG_SIZE[0] or img.size[1] > LARGEST_IMG_SIZE[1]:
                retv["Ret"] = IMAGE_TOO_LARGE
                self.write(json.dumps(retv, sort_keys=True, indent=4))
                self.finish()
                return
        except:
            retv['Ret'] = IMAGE_OPEN_FAIL
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        #retv = detectFace(imagebinary)
        (imgname, retv) = yield tornado.gen.Task(detectFace, imagebinary)
        self.write(json.dumps(retv, sort_keys=True, indent=4))
        self.finish()
        return

### /management/register?method=normal/force          
class RegisterHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def post(self):
        retv = {"Image": "", "Ret": NORMAL}
        method = self.get_argument('method', 'normal')
        userList=getUserList()
        if method == "normal" and len(userList)>=USER_MAX:
            retv["Ret"] = USER_TOO_MANY
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        if method != "normal" and method != "force":
            retv["Ret"] = INPUT_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        dict_json = dict()
        try:
            dict_json = json.loads(self.request.body)
        except:
            retv['Ret'] = INPUT_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        #dict_json = {'Userid':xxx, 'Image':base64}    
        if 'Userid' not in dict_json  or 'Image' not in dict_json:
            retv["Ret"] = INPUT_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        if dict_json['Userid'].find(' ')>=0 or dict_json['Userid'].find('\n')>=0 or dict_json['Userid'].find('\r')>=0:
            retv['Ret'] = INPUT_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        if not dict_json['Userid'] or not dict_json['Image']:
            retv["Ret"] = INPUT_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        imagebinary = str()
        try:
            imagebinary = base64.b64decode(dict_json["Image"])
        except:
            retv['Ret'] = BASE64DEC_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        userid = dict_json["Userid"]
        print "image size=",len(imagebinary)
        #### The userid has been registered before
        if method=='normal' and os.path.isfile(os.path.join(options.facepath, userid+'.jpg')):
            retv = {"Ret":FACE_EXISTS, "Image":""}
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        try:
            img = Image.open(StringIO.StringIO(imagebinary))
            print img.size
            if img.size[0] > LARGEST_IMG_SIZE[0] or img.size[1] > LARGEST_IMG_SIZE[1]:
                retv["Ret"] = IMAGE_TOO_LARGE
                if "Feat" not in dict_json:
                    self.write(json.dumps(retv, sort_keys=True, indent=4))
                    self.finish()
                    return
        except:
            retv['Ret'] = IMAGE_OPEN_FAIL
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        #retv = detectFace(imagebinary)
        if retv["Ret"] == NORMAL :
            (imgname ,retv) = yield tornado.gen.Task(detectFace, imagebinary)
            if retv['Ret'] == 0 and os.path.isfile(os.path.join(options.img5ppath,imgname+'.feat')):
                src = os.path.join(options.img5ppath, imgname+'.feat')
                if UBOX_TYPE==1:
                    filebinary = readImage(imgname, "feat", options.img5ppath)
                    if filebinary:
                        retv["Feat"] = base64.b64encode(filebinary)
                dst = os.path.join(options.newfeatpath, userid+'.feat')
                saveImage(imagebinary, userid, 'jpg', options.facepath)
                #os.rename(src, dst)
                print 'src: %s\ndst: %s'%(src, dst)
                shutil.move(src, dst)
                #rebootRecg()
        if retv["Ret"] != NORMAL and "Feat" in dict_json:
            saveImage(imagebinary, userid, 'jpg', options.facepath)
            filebinary = base64.b64decode(dict_json["Feat"])
            with open(os.path.join(options.newfeatpath, userid + '.feat'), "wb") as fp:
                # with open(filename, "wb") as fp:
                fp.write(filebinary)
            retv["Ret"] = NORMAL

        self.write(json.dumps(retv, sort_keys=True, indent=4))
        self.finish()
        return
    
class  LogoutHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        userid = self.get_argument('userid','')
        retv = {"Ret": NORMAL}
        if not userid:
            retv['Ret'] = INPUT_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        userList = getUserList()
        if userid not in userList:
            retv['Ret'] = INPUT_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        retv = logoutFace(userid)
        self.write(json.dumps(retv, sort_keys=True, indent=4))
        self.finish()
        return

class LogoutAllHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        retv = logoutAll()
        self.write(json.dumps(retv, sort_keys=True, indent=4))
        self.finish()
        return

class UserListHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        retv = {"Ret": NORMAL, "Userids": []}
        retv["Userids"] = getUserList()
        self.write(json.dumps(retv, sort_keys=True, indent=4))
        self.finish()
        return

class CommandHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        retv = {"Ret":INPUT_ERROR}
        cmd = self.get_argument('cmd', '')
        execution = str()
        if cmd == 'reboot':
            execution = 'reboot'
        elif cmd == 'shutdown':
            execution = 'poweroff'
        elif cmd == 'recover':
            execution = 'rm interfaces'
        if not execution:
            self.write(json.dumps(retv))
        else:
            retv['Ret'] = NORMAL
            self.write(json.dumps(retv))
        self.finish()
        os.system(execution)


def netStatus(gateway):
    info = os.popen('ping -c 2 -w 1 %s'%gateway).read()
    if info.find('0 received, 100% packet loss') != -1:
        return False
    else:
        return True

def netSetup(mode, addr, mask, gateway):
    eth = os.popen("ifconfig | grep eth | head -1 | awk -F ' ' '{print $1}'").read().strip()
    if not eth:
        return NO_NETCARD
    if mode != 'static' and mode != 'dhcp':
        return INPUT_ERROR
    pattern = re.compile(r'^[0-9]+?\.[0-9]+?\.[0-9]+?\.[0-9]+$')
    if mode=='static' and (not pattern.match(addr) or not pattern.match(mask) or not pattern.match(gateway)):
        return INPUT_ERROR
    filename = "interfaces"
    if mode == "dhcp":
        os.remove(filename)
    elif mode == "static":
        with open(filename, "w") as fp:
            fp.write("ifconfig %s %s netmask %s\n"%(eth, addr, mask))
            fp.write("route add default gw %s\n"%gateway)
        os.chmod(filename, stat.S_IRWXU|stat.S_IRGRP|stat.S_IROTH)
    return NORMAL

##{'Mode':static/dhcp, 'Address':'192.168.1.100', 'Netmask':'255.255.255.0', 'Gateway':'192.168.1.1'}
class NetworkHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def post(self):
        retv={'Ret':NORMAL}
        dict_json = dict()
        try:
            dict_json = json.loads(self.request.body)
        except:
            print "Except"
            retv['Ret'] = INPUT_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        mode = dict_json.get('Mode','')
        addr = dict_json.get('Address','')
        mask = dict_json.get('Mask','')
        gateway = dict_json.get('Gateway','')
        retv['Ret'] = netSetup(mode, addr, mask, gateway)
        self.write(json.dumps(retv, sort_keys=True, indent=4))
        self.finish()
        if retv['Ret'] == NORMAL:
            os.system('bash ./interfaces')
        return
            

class ConfigHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        retv = {"Ret":NORMAL, "Config":str()}
        filebinary = readImage("config", "txt", options.configpath);
        if filebinary:
            retv["Config"] = base64.b64encode(filebinary)
        else:
            retv["Ret"] = FILE_NOT_EXISTS
        self.write(json.dumps(retv, sort_keys=True, indent=4))
        self.finish()
        return
    def post(self):
        retv = {"Ret":NORMAL}
        dict_json = dict()
        try:
            dict_json = json.loads(self.request.body)
        except:
            retv = INPUT_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        if not dict_json["Config"]:
            retv["Ret"] = INPUT_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        filebinary = str()
        try:
            filebinary = base64.b64decode(dict_json["Config"])
        except:
            retv['Ret'] = BASE64DEC_ERROR
            self.write(json.dumps(retv, sort_kesys=True, indent=4))
            self.finish()
            return
        filename = os.path.join(options.configpath, "config.txt")
        with open(filename, "wb") as fp:
            fp.write(filebinary)
        #rebootTool()
        killRecog()
        self.write(json.dumps(retv, sort_keys=True, indent=4))
        self.finish()
        return

class GPIOHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        '''
        /management/gpio?cmd=open&interval=1
        '''
        retv = {"Ret":GPIO_EXEC_FAIL}
        cmd = self.get_argument('cmd', '')
        interval = self.get_argument('interval', 1)
        if cmd == 'open':
            if not os.path.exists('/sys/class/gpio/gpio57'):
                os.system('echo 57 > /sys/class/gpio/export')
            bret1 = os.system('echo out > /sys/class/gpio/gpio57/direction')
            bret2 = os.system('echo 1 > /sys/class/gpio/gpio57/value')
            time.sleep(float(interval))
            bret3 = os.system('echo 0 > /sys/class/gpio/gpio57/value')
            if bret1==0 and bret2==0 and bret3==0:
                retv['Ret'] = NORMAL
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        retv['Ret'] = INPUT_INVALID
        self.write(json.dumps(retv, sort_keys=True, indent=4))
        self.finish()
        return

class WGHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        '''
        /management/weigand?cmd=open&interval=1
        '''
        retv = {"Ret": GPIO_EXEC_FAIL}
        cmd = self.get_argument('cmd', '')
        print cmd
        if cmd == 'open':
            if  gate_serial:
                bret1 = gate_serial.write(NORMAL_USER)
                print "bret1:",bret1
                if bret1 == 4 :
                    retv['Ret'] = NORMAL
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        retv['Ret'] = INPUT_INVALID
        self.write(json.dumps(retv, sort_keys=True, indent=4))
        self.finish()
        return

# record format: [2016-12-09 11:45:37.924][None_None_None_None_None][13918694239-0.549438_20161209114537711_976_823_161_160][Close][Live][Fail][13918694239][0.549438][Time_cost:][98][23][0][44]
def filterImages(logfile):
    try:
        if not os.path.isfile(logfile):
            return
        records = []
        time_length = len('[yyyy-dd-mm HH:MM:SS.msc')
        time_length_ex = len('yyyy-dd-mm HH:MM:SS')
        with open(logfile, 'rb') as fp:
            for line in fp.readlines():
                parts = line.split('][')
                if len(parts) != 13 or len(parts[0]) != time_length or parts[6]=="UNKNOWN":
                    continue
                records.append({
                    'timestamp': time.mktime(time.strptime(parts[0][1:time_length_ex+1], "%Y-%m-%d %H:%M:%S")),
                    'name': parts[6],
                    'image': parts[2] + '.jpg',
                    'score': float(parts[7]),
                    'text': line.strip()
                })
        if not records:
            return True
        start_time = records[0]['timestamp']
        max_score = -1
        pre_name=""
        cur_record = None
        filter_records = []
        for record in records:
            if cur_record:
                if pre_name==record["name"] and record['timestamp'] - start_time <5:  # unit=second
                    if record['score'] > max_score:
                        max_score = record['score']
                        cur_record = record['text']
                    else:
                        path = os.path.join(options.resultpath, record['image'])
                        if os.path.isfile(path):
                            os.remove(path)
                else:
                    filter_records.append(cur_record)
                    max_score = record['score']
                    cur_record = record['text']
            else:
                cur_record=record["text"]
                max_score=record['score']
                pre_name=record["name"]
            start_time=record['timestamp']
        if cur_record:
            filter_records.append(cur_record)
        parts = logfile.split('.')
        newfile = "%s_filter.%s"%(parts[0], '.'.join(parts[1:]))
        with open(newfile, 'w+') as fp:
            for line in filter_records:
                fp.write(line+'\n')
    except Exception, e:
        print "Meet Exception: ", e
        return False
    return True

class LogHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        '''
        GET /management/log?date=2016-01-01
        '''
        retv = {'Ret': NORMAL, 'Log': ''}
        strtoday = datetime.datetime.today().strftime('%Y-%m-%d')
        logdate = self.get_argument('date', strtoday)
        
        logname = logdate + '.log'
        logname_filter = logdate + '_filter.log'
        fullname = os.path.join(BASE_PATH, logname)
        
        if not os.path.exists(fullname):
            logname = logdate + '.log.done'
            logname_filter = logdate + '_filter.log.done'
            fullname = os.path.join(BASE_PATH, logname)
        
        fullname_filter = os.path.join(BASE_PATH, logname_filter)
        
        if logdate == strtoday or not os.path.exists(fullname_filter):
            filterImages(fullname)
        
        if not os.path.exists(fullname_filter):
            retv['Ret'] = FILE_NOT_EXISTS
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        
        try:
            with open(fullname_filter, 'r') as fp:
                retv['Log'] = fp.read()
        except:
            retv['Ret'] = FILE_READ_FAIL
        
        self.write(json.dumps(retv, sort_keys=True, indent=4))
        self.finish()
        return


class ImgHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        '''
        GET /management/image?imgname=xxx
        '''
        retv = {"Image":"", "Ret": NORMAL}
        imgname = self.get_argument('imgname','')
        if not imgname:
            retv["Ret"] = INPUT_ERROR
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        fullname = os.path.join(options.resultpath, imgname)
        if not os.path.exists(fullname):
            retv["Ret"] = FILE_NOT_EXISTS
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        imagebinary = str()
        with open(fullname, "rb") as fp:
            imagebinary = fp.read()
        if not imagebinary:
            retv["Ret"] = FILE_READ_FAIL
            self.write(json.dumps(retv, sort_keys=True, indent=4))
            self.finish()
            return
        imagebinary = base64.b64encode(imagebinary)
        retv["Image"] = imagebinary
        self.write(json.dumps(retv, sort_keys=True, indent=4))
        self.finish()
        return       

def clearDir(path, insignificant=True):
    try:
        if os.path.isdir(path):
            filenames = os.listdir(path)
            for filename in filenames:
                fullpath = os.path.join(path, filename)
                if os.path.isdir(fullpath):
                    shutil.rmtree(fullpath)
                else:
                    os.remove(fullpath)
        else:
            return insignificant
    except Exception, e:
        print "Meet Exception: ", e;
        return False
    return True

# period: [from, to)
def getExistLogNames(from_date=None, to_date=None):
    logpath = BASE_PATH
    filenames = os.listdir(logpath)
    logs = []
    datelength = len('yyyy-mm-dd')
    for filename in filenames:
        if os.path.isfile(os.path.join(logpath, filename)):
            parts = filename.split('.')
            if len(parts[0]) == datelength and len(parts[0].split('-')) == 3:
                if len(parts) == 2 and parts[1] == 'log':
                    logs.append(parts[0])
                elif len(parts) == 3 and parts[1] == 'log' and parts[2] == 'done':
                    logs.append(parts[0])
    
    if from_date == None and to_date == None:
        return logs
    
    fromts = time.mktime(time.strptime(from_date, "%Y-%m-%d")) if from_date else None
    tots = time.mktime(time.strptime(to_date, "%Y-%m-%d")) if to_date else None
    sublogs = []
    for alog in logs:
        ts = time.mktime(time.strptime(alog, "%Y-%m-%d"))
        if fromts:
            if ts < fromts:
                continue
        if tots:
            if ts >= tots:
                continue
        sublogs.append(alog)
    
    return sublogs

def resetConfig():
    # clear folders
    result = dict()
    result['imagepath'] = clearDir(options.imagepath, False)
    result['savepath'] = clearDir(options.savepath, False)
    result['facepath'] = clearDir(options.facepath, False)
    result['featpath'] = clearDir(options.featpath, False)
    result['imgorgpath'] = clearDir(options.imgorgpath, False)
    result['img5ppath'] = clearDir(options.img5ppath, False)
    result['resultpath'] = clearDir(options.resultpath, True)
    result['logfile'] = True
    # clear logs
    logs = getExistLogNames()
    for strdate in logs:
        try:
            path = os.path.join(BASE_PATH, strdate+'.log')
            if os.path.isfile(path):
                os.remove(path)
            path = os.path.join(BASE_PATH, strdate+'.log.done')
            if os.path.isfile(path):
                os.remove(path)
            path = os.path.join(BASE_PATH, strdate+'_filter.log')
            if os.path.isfile(path):
                os.remove(path)
            path = os.path.join(BASE_PATH, strdate+'_filter.log.done')
            if os.path.isfile(path):
                os.remove(path)
        except Exception, e:
            print "Meet Exception: ", e
            result['logfile'] = False
    # reset config
    retcode = 0
    try:
        command = "cp %s %s"%(options.rootpath, options.configpath)
        retcode = os.system(command)
    except Exception, e:
        print "Meet Exception: ", e;
        retcode = -1
    # create return value
    retv = {'Ret': NORMAL, 'Message': 'Success.'}
    failed = []
    for folder, success in result.items():
        if not success:
            failed.append(folder)
    if retcode != 0:
        retv['Ret'] = RESET_CONFIG_FAIL
        retv['Message'] = "ERROR! Cannot Reset Config. Command(cp) Error Code: %d"%(retcode)
    elif len(failed) > 0:
        retv['Ret'] = CLEAR_FOLDER_FAIL
        retv['Message'] = "WARNING! Cannot Clear Target: %s"%(", ".join(failed))
    return retv
            
class ResetConfigHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        mac = self.get_argument('mac','')
        if mac != get_mac_addr():
            retv = {'Ret':INPUT_ERROR, 'Message':'MAC Invalid'}
            self.write(json.dumps(retv))
            self.finish()
            return
        retv = resetConfig()
        if retv['Ret'] == NORMAL:
            killRecog()
        self.write(json.dumps(retv))
        self.finish()
        return
    def post(self):
        self.get()
        return

class LogListHandler(tornado.web.RequestHandler):    
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        retv = {'Ret': NORMAL, 'Dates': []}
        from_date = None
        to_date = None
        try:
            from_date = self.get_argument('date', None)
            if not from_date:
                from_date = self.get_argument('from', None)
            to_date = self.get_argument('to', None)
        except Exception, e:
            print "WARNING! Meet Exception: ", e
            retv['Ret'] = INPUT_ERROR
            self.write(json.dumps(retv))
            self.finish()
            return
        try:
            logs = getExistLogNames(from_date, to_date)
            retv['Dates'] = logs
        except Exception, e:
            retv['Ret'] = LIST_LOGFILE_FAIL
        
        self.write(json.dumps(retv))
        self.finish()
        return
    def post(self):
        self.get()
        return

def getDateList(strFromDate, strToDate):
    list=[]
    if strToDate:
        strtoday  = datetime.datetime.today().date()
        strFromDate=datetime.datetime.strptime(strFromDate, "%Y%m%d").date()
        strToDate = datetime.datetime.strptime(strToDate, "%Y%m%d").date()
        if strtoday < strFromDate:
            return list
        if strtoday < strToDate:
            strToDate = strtoday

        curDate = strFromDate
        finalDate = strToDate
        while curDate <= finalDate:
            strCurDate = str(curDate).replace("-","")
            list.append(strCurDate)
            curDate = curDate + datetime.timedelta(1)
    else:
        list=[strFromDate]
    return list

class DelRecordFacesHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        retv = {'Ret': NORMAL}
        from_date = None
        to_date = None
        try:
            from_date = self.get_argument('from', None)
            to_date = self.get_argument('to', None)
        except Exception, e:
            print "WARNING! Meet Exception: ", e
            retv['Ret'] = INPUT_ERROR
            self.write(json.dumps(retv))
            self.finish()
            return
        try:
            # if not from_date or len(from_date) != 8 or (to_date and len(to_date)!= 8) :
            #     retv['Ret'] = INPUT_ERROR
            #     print "=============",from_date,"----",to_date
            # else:
            #     dateList=getDateList(from_date,to_date)
            #     print dateList
            #     for item in dateList:
            #         os.system('rm -f '+options.resultpath+"/*-*_"+item+"*.jpg")
            if not from_date or len(from_date) != 10 or not to_date or len(to_date) != 10 or from_date>=to_date :
                retv['Ret'] = INPUT_ERROR
            else:
                os.system("find "+options.resultpath+"/ "+"-maxdepth 1 -type f -newermt \""+from_date+"\" -not -newermt \""+to_date+"\" -delete")
        except Exception, e:
            retv['Ret'] = RECORDIMG_REMOVE_ERROR
        self.write(json.dumps(retv))
        self.finish()
        return

    def post(self):
        self.get()
        return

def VerifyPassword(password, mac):
    if not password:
        return {'Ret': INPUT_ERROR, 'Message': 'No Password Found.'}
    if not mac:
        return {'Ret': INPUT_ERROR, 'Message': 'No Mac Address Found.'}
    real_mac = get_mac_addr()
    if mac != real_mac:
        return {'Ret': MAC_NOT_MATCH, 'Message': 'Wrong Mac Address.'}
    real_password = get_user_password()
    if password != real_password:
        return {'Ret': INVALID_PASSWORD, 'Message': 'Wrong Password.'}
    return {'Ret': NORMAL, 'Message': 'Success.'}

class VerifyPasswordHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        password = self.get_argument('target', '')
        mac = self.get_argument('mac', '')
        retv = VerifyPassword(password, mac)
        self.write(json.dumps(retv))
        self.finish()
        return
    def post(self):
        self.get()
        return

def delHistory(filepath):
    tnow = int(time.time()*1000000)
    if(os.path.isdir(filepath) == True):
        #strresult = os.popen("ls "+filepath).read()
        #listresult = strresult.split()
        listresult = os.listdir(filepath)
        for line in listresult:
            line1 = line[0:16]
            print line1
            print tnow
            if not line1.isdigit():
                continue
            if(tnow - int(line1) > 100000000):
                os.remove(os.path.join(filepath, line))
    


def recogGuard():
    while True:
        time.sleep(5)
        procs = os.popen("ps aux | grep -v grep | grep ./%s"%options.recogname,'r').readlines()
        print procs
        pids = []
        for proc in procs:
            tmp = proc.split()
            if len(tmp)>2 and tmp[-1] == "./%s"%options.recogname:
                pids.append(tmp[1])
        if len(pids) != 1:
            rebootRecog(pids)
    

def historyProc():
    while True:
        #print "delete history"
        delHistory(options.imagepath)
        delHistory(options.savepath)
        delHistory(options.imgorgpath)
        delHistory(options.img5ppath)
        time.sleep(100)
    return

def httpProc():
    app = tornado.web.Application([(r'/verification', VeriHandler), 
                                   (r'/recognition', RecogHandler),
                                   (r'/detection', DetHandler),
                                   (r'/face', FaceHandler),
                                   (r'/management/register', RegisterHandler),
                                   (r'/management/logout', LogoutHandler),
                                   (r'/management/logoutall', LogoutAllHandler),
                                   (r'/management/userids', UserListHandler),
                                   (r'/management/config', ConfigHandler),
                                   (r'/management/gpio', GPIOHandler),
                                   (r'/management/weigand', WGHandler),
                                   (r'/management/log', LogHandler),
                                   (r'/management/image', ImgHandler),
                                   (r'/management/factoryreset', ResetConfigHandler),
                                   (r'/management/check', VerifyPasswordHandler),
                                   (r'/listlogs', LogListHandler),
                                   (r'/delrecordfaces',DelRecordFacesHandler),
                                   (r'/command', CommandHandler),
                                   (r'/network', NetworkHandler)],)
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


UDPPORT = 51423
def get_hostname():
    return os.popen("hostname").read().strip()
def get_mac_addr():
    return os.popen("ifconfig | grep eth | head -1 | awk -F ' ' '{print $5}'").read().strip()
    #return uuid.UUID(int = uuid.getnode()).hex[-12:]
def get_ip():
    ifname = os.popen("ifconfig | grep eth | head -1 | awk -F ' ' '{print $1}'").read().strip()
    print ifname
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15]))[20:24])
def get_user_password(user=None):
    return 'youtu@)!^'

def broadcast():
    while True:
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except:
            print "Socket created fail"
            continue
        content = str()
        while True:
            mac = str()
            ip = str()
            hostname = str()
            try:
                hostname = get_hostname()
            except:
                hostname = "NONE"
            try:
                mac = get_mac_addr()
            except:
                mac = "NONE"
            try:
                ip = get_ip()
            except:
                ip = "NONE"
            #content = "%s %s %s\n"%(hostname, mac, ip)
            content = "%s %s %d\n"%(mac, ip, UBOX_TYPE)
            print content
            try:
                s.sendto(content, ('<broadcast>',UDPPORT))
            except:
                print "udp send fail"
            time.sleep(1)
        s.close()


TASK_FLAG = True
BackgroundScheduler = None
CronTrigger = None
try:        
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
except Exception, e:
    print "WARNING! Module \'apscheduler\' Not Installed. Timed Task Cannot Execute This Time."
    TASK_FLAG = False

def clearAncientLogImages():
    cmd = "du -s %s"%(options.resultpath)
    size = os.popen(cmd).read().split()[0]
    if len(size) < 9:
        return
    pass

def task():
    yesterday = ( datetime.datetime.today().date() - datetime.timedelta(days=1) ).strftime('%Y-%m-%d')
    logfile = os.path.join(BASE_PATH, yesterday+'.log')
    filterImages(logfile)
    return

class MyScheduler:
    m_execute_time = {}
    m_scheduler = None
    m_trigger = None
    m_task = None
    
    def __init__(self, hour, minute, second):
        self.m_execute_time = {'hour': hour, 'minute': minute, 'second': second}
        pass
    
    def start(self):
        if not self.m_scheduler:
            self.m_scheduler = BackgroundScheduler()
        if not self.m_trigger:
            self.m_trigger = CronTrigger(
                hour = self.m_execute_time.get('hour', 0),
                minute = self.m_execute_time.get('minute', 0),
                second = self.m_execute_time.get('second', 0)
            )
        if not self.m_task:
            self.m_task = self.m_scheduler.add_job(task, self.m_trigger)
        self.m_scheduler.start()
        pass
    
    def close(self):
        if self.m_scheduler:
            self.m_scheduler.shutdown()
        pass

if __name__ == '__main__' and TASK_FLAG:
    print "INFO: Timed Task Start."
    scheduler = MyScheduler(hour=0, minute=5, second=0)
    scheduler.start()

LARGEST_IMG_SIZE = getFrameSize(os.path.join(options.configpath,'config.txt'))
print LARGEST_IMG_SIZE
GATE_TTY="/dev/ttyS0"
NORMAL_USER=getNormalUser()
gate_serial=""
if os.path.exists(GATE_TTY):
    gate_serial = serial.Serial(GATE_TTY, 9600, timeout=60)

if __name__ == "__main__":
    tornado.options.parse_command_line()
    clearAncientLogImages()
    if(not os.path.isdir(options.imagepath)):
        os.makedirs(options.imagepath)
        print "Create Directory: ", options.imagepath
    if(not os.path.isdir(options.savepath)):
        os.makedirs(options.savepath)
        print "Create Directory: ", options.savepath
    if(not os.path.isdir(options.facepath)):
        os.makedirs(options.facepath)
        print "Create Directory: ", options.facepath
    if not os.path.isdir(options.featpath):
        os.makedirs(options.featpath)
        print "Create Directory: ", options.featpath
    if not os.path.isdir(options.newfeatpath):
        os.makedirs(options.newfeatpath)
        print "Create Directory: ", options.newfeatpath
    if not os.path.isdir(options.imgorgpath):
        os.makedirs(options.imgorgpath)
        print "Create Directory: ", options.imgorgpath
    if not os.path.isdir(options.img5ppath):
        os.makedirs(options.img5ppath)
        print "Create Directory: ", options.img5ppath
    delname = os.path.join(options.imagepath, "*")
    for i in glob.glob(delname):
        os.remove(i)
        print "Delete File: ", i
    delname = os.path.join(options.savepath, "*")
    for i in glob.glob(delname):
        os.remove(i)
        print "Delete File: ", i
    
    subproc1 = multiprocessing.Process(target=historyProc, args=())
    subproc2 = multiprocessing.Process(target=httpProc, args=())
    subproc3 = multiprocessing.Process(target=broadcast, args=())
    subproc4 = multiprocessing.Process(target=recogGuard, args=())
    subproc1.start()
    subproc2.start()
    subproc3.start()
    subproc4.start()
    if os.path.isfile('interfaces'):
        time.sleep(10)
        os.system('bash ./interfaces')
    while True:
        if not subproc1.is_alive():
            subproc1 = multiprocessing.Process(target=historyProc, args=())
            subproc1.start()
        if not subproc2.is_alive():
            subproc2 = multiprocessing.Process(target=httpProc, args=())
            subproc2.start()
        if not subproc3.is_alive():
            subproc3 = multiprocessing.Process(target=broadcast, args=())
            subproc3.start()
        if not subproc4.is_alive():
            subproc4 = multiprocessing.Process(target=recogGuard, args=())
            subproc4.start()
        time.sleep(10)
    
    subproc1.join()
    subproc2.join()
    subproc3.join()


