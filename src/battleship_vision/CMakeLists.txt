cmake_minimum_required(VERSION 3.0.2)
project(battleship_vision)

## Encontrar dependencias de catkin
find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  sensor_msgs
  cv_bridge
  image_transport
)

## Declaración del paquete
catkin_package()

## Rutas de include (no usas C++ aquí, pero lo dejamos estándar)
include_directories(
  ${catkin_INCLUDE_DIRS}
)

## Instalar scripts Python como nodos ejecutables de ROS
## IMPORTANTE: asegúrate de que todos tienen shebang correcto (# !/usr/bin/env python3)
## y permiso de ejecución (chmod +x).
catkin_install_python(
  PROGRAMS
    scripts/usb_camera_node.py

    scripts/hand/hand_camera_node.py
    scripts/hand/hand_node.py

    scripts/board/board_camera_node.py
    scripts/board/board_node.py

    scripts/game_logic/game_logic_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

## No hay nodos C++ ni mensajes personalizados, así que no hace falta add_executable() ni message_generation
