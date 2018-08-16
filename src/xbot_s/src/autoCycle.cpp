/*************************************************************************
	> File Name: autoCycle.cpp
	> Author:Rocwang 
	> Mail: yowlings@gmail.com;
	> Github:https://github.com/yowlings
	> Created Time: 2018年08月02日 星期四 14时04分14秒
 ************************************************************************/
#include "ros/ros.h"
#include "std_msgs/String.h"

int main(int argc, char **argv)
{
    ros::init(argc, argv, "auto_launch");
    ros::NodeHandle nh;

    ros::Publisher auto_cycle_pub = nh.advertise<std_msgs::String>("/office/goal_name", 1000);

    ros::Rate loop_rate(1);
    int wait_time = 255+60;
    while (wait_time >254)
    {
        std_msgs::String msg;
        if(wait_time > 255)
        {
            msg.data = "nothing";
        }
        else{
            msg.data = "middle";
        }
        auto_cycle_pub.publish(msg);
        ros::spinOnce();
        wait_time--;

        loop_rate.sleep();
    }

    return 0;
}
