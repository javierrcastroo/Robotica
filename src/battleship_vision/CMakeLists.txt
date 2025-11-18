cmake_minimum_required(VERSION 3.0.2)
project(battleship_vision)

find_package(catkin REQUIRED COMPONENTS
  rospy
  sensor_msgs
  cv_bridge
  image_transport
)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/hand_camera_node.py
  scripts/board_camera_node.py
  scripts/usb_camera_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
