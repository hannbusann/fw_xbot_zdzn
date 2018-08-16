#!/bin/bash
#
#
echo "ubuntu镜像源：（ubuntu 16.04）"
sudo sh -c 'echo "deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ xenial main restricted
deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ xenial-updates main restricted
deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ xenial universe
deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ xenial-updates universe
deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ xenial multiverse
deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ xenial-updates multiverse
deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ xenial-backports main restricted universe multiverse
deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ xenial-security main restricted
deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ xenial-security universe
deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ xenial-security multiverse 
deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main
" > /etc/apt/sources.list.d/ros-latest.list'
##########################################################################
#
#install ROS and xbot drivers
#
##########################################################################
echo "开始安装基础工具软件......"
sudo apt-get update
sudo apt-get install git -y
sudo apt-get install ssh -y
echo "开始对机器人端口进行映射......"
sudo cp 58-xbot.rules /etc/udev/rules.d/
sudo service udev restart
echo "加入ROS安装库......"
# Setup keys
sudo apt-key adv --keyserver hkp://ha.pool.sks-keyservers.net:80 --recv-key 421C365BD9FF1F717815A3895523BAEEB01FA116
# Installation
sudo apt-get update
sudo apt-get install ros-kinetic-desktop-full -y
# Add Individual Packagejis here
# You can install a specific ROS package (replace underscores with dashes of the package name):
# sudo apt-get install ros-kinetic-PACKAGE
# e.g.
# sudo apt-get install ros-kinetic-navigation
#
# To find available packages:
# apt-cache search ros-kinetic
# 
# Initialize rosdep
sudo apt-get install python-rosdep -y

# Initialize rosdep
sudo rosdep init
# To find available packages, use:
rosdep update
# Environment Setup
echo "source /opt/ros/kinetic/setup.bash" >> ~/.bashrc
source ~/.bashrc
# Install rosinstall
# 安装xbot ROS驱动包依赖的软件
sudo apt-get install python-rosinstall -y
sudo apt-get install ros-kinetic-yocs-cmd-vel-mux -y
sudo apt-get install ros-kinetic-controller-manager -y
sudo apt-get install ros-kinetic-move-base -y
sudo apt-get install ros-kinetic-move-base-msgs -y
sudo apt-get install ros-kinetic-hector-slam -y
sudo apt-get install ros-kinetic-gmapping -y
sudo apt-get install ros-kinetic-dwa-local-planner -y
sudo apt-get install ros-kinetic-robot-upstart -y
sudo apt-get install ros-kinetic-ecl -y
sudo apt-get install ros-kinetic-yocs-controllers -y
sudo apt-get install ros-kinetic-rosbridge-server -y

sudo apt-get install ros-kinetic-rplidar-ros -y
sudo apt-get install ros-kinetic-amcl -y
sudo apt-get install ros-kinetic-map-server -y
sudo apt-get install ros-kinetic-yocs-velocity-smoother -y

bash ./setupCatkinWorkspace.sh


#安装xbot驱动程序以及ROS驱动包
#sudo cp ~/catkin_ws/src/rplidar_ros/scripts/rplidar.rules /etc/udev/rules.d/57-rplidar.rules
sudo cp ../rplidar_ros/scripts/rplidar.rules /etc/udev/rules.d/57-rplidar.rules
sudo cp ../installXBot-U/58-xbot.rules /etc/udev/rules.d/
sudo service udev restart
source ~/.bashrc


# 安装realsense驱动包
echo 'deb http://realsense-hw-public.s3.amazonaws.com/Debian/apt-repo xenial main' | sudo tee /etc/apt/sources.list.d/realsense-public.list
sudo apt-key adv --keyserver keys.gnupg.net --recv-key 6F3EFCDE
sudo apt-get update
sudo apt-get install librealsense2-dkms -y
sudo apt-get install librealsense2-utils -y
sudo apt-get install librealsense2-dev -y
sudo apt-get install librealsense2-dbg -y

sudo apt-get install aptitude -y
sudo aptitude full-upgrade catkin -y
sudo apt-get install libasound-dev -y


# rosrun robot_upstart install xbot_bringup/launch/xbot-u.launch
# sudo systemctl daemon-reload
# sudo systemctl start xbot
#


sudo echo "source /opt/ros/kinetic/setup.bash" >> ~/.bashrc
sudo echo "source ~/catkin_ws/devel/setup.bash" >> ~/.bashrc
sudo echo "export ROS_MASTER_URI=http://192.168.8.101:11311" >> ~/.bashrc
sudo echo "export ROS_HOSTNAME=192.168.8.101" >> ~/.bashrc

source ~/.bashrc
# catkin_make
cd ~/catkin_ws

rm -rf devel build


catkin_make --pkg xbot_msgs
catkin_make

