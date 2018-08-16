# installXBot-U一键安装说明
## 一 系统安装

1. 下载xbot_installation.tar.gz到桌面
2. 解压
> tar zxf '/home/xxxx/桌面/xbot_installation.tar.gz'
3. 转换目录和sh添加权限
> cd '/home/xxxx/桌面/src/installXBot-U/'
> sudo  chmod +w *.sh
4. 执行安装
./installXBot-U.sh


## 二 测试机器人

机器人接上显示屏然后在命令行分别启动机器人驱动包

> roslaunch xbot_bringup xbot.launch

另外启动一个命令行窗口运行

> rosrun xbot_tools keyboard_control.py

后按前后左右箭头控制机器人直行和旋转,查看结果.

在新的命令行窗口运行

> rqt_plot

在出现的窗口中选择红外或者超声的topic查看图形.

## 三 验收机器人

按照*重德智能XBot-U发货单-20180314-1.docx* 文件的10条验收标准逐一进行验收.

使用pad的浏览器前往重德智能官网页脚的链接中下载XBot-U助手并安装,安装后启动设置ip地址为192.168.8.101即可.

| 编号   | 运行指令或操作                |
| ---- | ---------------------- |
| 1    | 使用rostopic list可看到节点列表 |
| 2    | 可看到RPlidar转动           |
| 3    | 开启App上电机可遥控,关闭不可遥控     |
| 4    | 可使用App遥控               |
| 5    | 可控制水平云台转动              |
| 6    | 可控制竖直云台转动              |
| 7    | 可看到摄像头画面               |
| 8    | 按住急停电机失效               |
| 9    | 接口有电压                  |

