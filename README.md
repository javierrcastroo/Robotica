# Robotica

Este repositorio contiene un paquete de ROS (catkin) para arrancar nodos de cámara USB destinados a un sistema de hundir la flota con un UR3. Se incluyen dos nodos: uno para la cámara de la mano (`hand`) y otro para la cámara del tablero (`board`).

## Estructura

- `CMakeLists.txt`: archivo mínimo de workspace catkin.
- `src/battleship_vision`: paquete con los nodos de visión.
  - `package.xml`, `CMakeLists.txt`: definición del paquete.
  - `scripts/usb_camera_node.py`: lógica común para abrir la cámara e iterar índices.
  - `scripts/hand_camera_node.py`: nodo de cámara de la mano.
  - `scripts/board_camera_node.py`: nodo de cámara del tablero.

## Uso

1. Crea el workspace y compílalo desde el directorio raíz:

   ```bash
   catkin_make
   source devel/setup.bash
   ```

2. Lanza cada nodo. Por ejemplo, con `rosrun` o mediante los ficheros de `launch` incluidos:

   ```bash
   rosrun battleship_vision hand_camera_node.py
   rosrun battleship_vision board_camera_node.py
   # o bien
   roslaunch battleship_vision hand_camera.launch
   roslaunch battleship_vision board_camera.launch
   # o ambas cámaras a la vez
   roslaunch battleship_vision cameras.launch
   ```

   Cada nodo iterará automáticamente sobre los índices de cámara USB (`0-9` por defecto) hasta encontrar uno operativo.

3. Parámetros disponibles (namespace privado `~`):

   - `camera_indices` (lista): índices a probar, p. ej. `[2,3,4]`.
   - `frame_width`, `frame_height`: resolución deseada (por defecto `1280x720`).
   - `publish_rate`: frecuencia en Hz (`10.0` por defecto).
   - `retry_delay`: segundos de espera antes de reintentar apertura o lectura (`1.0` por defecto).
   - `max_consecutive_failures`: número de frames fallidos antes de reabrir la cámara (`5` por defecto).
   - `image_topic`: tópico de publicación (por defecto `hand_camera/image_raw` o `board_camera/image_raw`).
   - `frame_id`: frame de la imagen.

Los tópicos se publican como `sensor_msgs/Image` con codificación `bgr8` y sellado temporal en cada frame.
