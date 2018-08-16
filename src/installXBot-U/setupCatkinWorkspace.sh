#!/bin/bash
# Create a Catkin Workspace and setup ROS environment variables
# Usage setupCatkinWorkspace.sh dirName

source /opt/ros/kinetic/setup.bash
DEFAULTDIR=~/catkin_ws
CLDIR="$1"
if [ ! -z "$CLDIR" ]; then 
 DEFAULTDIR=~/"$CLDIR"
fi
if [ -e "$DEFAULTDIR" ] ; then
  echo "$DEFAULTDIR already exists; no action taken" 
  exit 1
else 
  echo "Creating Catkin Workspace: $DEFAULTDIR"
fi
echo "$DEFAULTDIR"/src
mkdir -p "$DEFAULTDIR"/src
#cd "$DEFAULTDIR"/src
SHELL_FOLDER=$(cd "$(dirname "$0")";pwd)
cd "$SHELL_FOLDER"
cp -r ../../src "$DEFAULTDIR"
catkin_init_workspace
cd "$DEFAULTDIR"
catkin_make


#setup ROS environment variables
echo "source ~/catkin_ws/devel/setup.bash" >> ~/.bashrc
echo "export ROS_MASTER_URI=http://192.168.8.101:11311" >> ~/.bashrc
echo "export ROS_HOSTNAME=192.168.8.101" >> ~/.bashrc
echo "export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH" >> ~/.bashrc


