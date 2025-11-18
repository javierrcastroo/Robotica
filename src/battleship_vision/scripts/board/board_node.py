#!/usr/bin/env python3
import os
import json
import cv2
import numpy as np

import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
from std_msgs.msg import String

from board_config import USE_UNDISTORT_BOARD, BOARD_CAMERA_PARAMS_PATH, WARP_SIZE
import board_ui
import board_state
import board_processing as bp
import aruco_utils
import battleship_logic


class BoardNode(object):
    def __init__(self):
        self.bridge = CvBridge()
        self.last_frame = None

        image_topic = rospy.get_param("~image_topic", "board_camera/image_raw")
        rospy.loginfo(f"[board_node] Suscribiéndose a: {image_topic}")
        self.sub = rospy.Subscriber(image_topic, Image, self.cb_image, queue_size=1)

        # publicador de layout de tablero
        self.board_pub = rospy.Publisher("battleship/board_layout", String, queue_size=10)

        # calibración
        self.mtx = None
        self.dist = None
        if USE_UNDISTORT_BOARD and os.path.exists(BOARD_CAMERA_PARAMS_PATH):
            data = np.load(BOARD_CAMERA_PARAMS_PATH)
            self.mtx = data["camera_matrix"]
            self.dist = data["dist_coeffs"]
            rospy.loginfo("[board_node] Undistort activado para tablero")

        # estado de tableros
        self.boards_state_list = [
            board_state.init_board_state("T1"),
            board_state.init_board_state("T2"),
        ]

        # ventanas
        cv2.namedWindow("Tablero")
        cv2.setMouseCallback("Tablero", board_ui.board_mouse_callback)
        cv2.namedWindow("Mascara tablero")
        cv2.namedWindow("Mascara barco x2")
        cv2.namedWindow("Mascara barco x1")
        cv2.namedWindow("Mascara municion")

        # timer
        self.timer = rospy.Timer(rospy.Duration(1.0 / 30.0), self.timer_cb)

    def cb_image(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except CvBridgeError as e:
            rospy.logwarn(f"[board_node] Error CvBridge: {e}")
            return
        self.last_frame = frame

    def timer_cb(self, event):
        if self.last_frame is None:
            return

        frame = self.last_frame.copy()

        # undistort
        if self.mtx is not None and self.dist is not None:
            frame = cv2.undistort(frame, self.mtx, self.dist)

        # origen ArUco
        aruco_utils.update_global_origin_from_aruco(frame, aruco_id=2)

        # process boards
        vis, mask_b, mask_ship2, mask_ship1, mask_m, layouts = bp.process_all_boards(
            frame,
            self.boards_state_list,
            cam_mtx=self.mtx,
            dist=self.dist,
            max_boards=2,
            warp_size=WARP_SIZE,
        )

        # publicar layout (en JSON)
        if layouts:
            payload = {
                "boards": layouts,
            }
            msg = String()
            msg.data = json.dumps(payload, default=self.json_default)
            self.board_pub.publish(msg)

        # validación de cada layout (como antes)
        validation_map = {}
        for layout in layouts:
            ok, msg_text = battleship_logic.evaluate_board(layout)
            validation_map[layout["name"]] = (ok, msg_text)
            print(f"[{layout['name']}] {msg_text}")

        for slot in self.boards_state_list:
            if slot["name"] in validation_map and slot["last_quad"] is not None:
                ok, msg_text = validation_map[slot["name"]]
                board_ui.draw_validation_result(vis, slot["last_quad"], msg_text, ok)

        # origen global
        if board_state.GLOBAL_ORIGIN is not None:
            gx, gy = board_state.GLOBAL_ORIGIN
            cv2.circle(vis, (int(gx), int(gy)), 10, (0, 255, 0), -1)
            cv2.putText(
                vis,
                "ORIGEN (ArUco)",
                (int(gx) + 10, int(gy) - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

        board_ui.draw_board_hud(vis)

        # mostrar
        cv2.imshow("Tablero", vis)
        if mask_b is not None:
            cv2.imshow("Mascara tablero", mask_b)
        if mask_ship2 is not None:
            cv2.imshow("Mascara barco x2", mask_ship2)
        if mask_ship1 is not None:
            cv2.imshow("Mascara barco x1", mask_ship1)
        if mask_m is not None:
            cv2.imshow("Mascara municion", mask_m)

        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            rospy.loginfo("[board_node] Saliendo por ESC/q")
            cv2.destroyAllWindows()
            rospy.signal_shutdown("User exit")
            return

        self.handle_keys(key, frame)

    @staticmethod
    def json_default(o):
        # para convertir tuples a listas si aparecen en layouts
        if isinstance(o, tuple):
            return list(o)
        raise TypeError

    def handle_keys(self, key, frame):
        import board_tracker
        import object_tracker
        import board_ui as bu

        if key == ord("b"):
            if bu.board_roi_defined:
                x0, x1 = sorted([bu.bx_start, bu.bx_end])
                y0, y1 = sorted([bu.by_start, bu.by_end])
                roi_hsv = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
                lo, up = board_tracker.calibrate_board_color_from_roi(roi_hsv)
                board_tracker.current_lower, board_tracker.current_upper = lo, up
                print("[INFO] calibrado TABLERO:", lo, up)
            else:
                print("[WARN] dibuja ROI en 'Tablero' primero")

        elif key == ord("2"):
            if bu.board_roi_defined:
                x0, x1 = sorted([bu.bx_start, bu.bx_end])
                y0, y1 = sorted([bu.by_start, bu.by_end])
                roi_hsv = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
                lo, up = object_tracker.calibrate_ship_two_color_from_roi(roi_hsv)
                object_tracker.current_ship_two_lower, object_tracker.current_ship_two_upper = lo, up
                print("[INFO] calibrado BARCO x2:", lo, up)
            else:
                print("[WARN] dibuja ROI sobre el barco largo")

        elif key == ord("1"):
            if bu.board_roi_defined:
                x0, x1 = sorted([bu.bx_start, bu.bx_end])
                y0, y1 = sorted([bu.by_start, bu.by_end])
                roi_hsv = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
                lo, up = object_tracker.calibrate_ship_one_color_from_roi(roi_hsv)
                object_tracker.current_ship_one_lower, object_tracker.current_ship_one_upper = lo, up
                print("[INFO] calibrado BARCO x1:", lo, up)
            else:
                print("[WARN] dibuja ROI sobre el barco corto")

        elif key == ord("m"):
            if bu.board_roi_defined:
                x0, x1 = sorted([bu.bx_start, bu.bx_end])
                y0, y1 = sorted([bu.by_start, bu.by_end])
                roi_hsv = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
                lo, up = object_tracker.calibrate_ammo_color_from_roi(roi_hsv)
                object_tracker.current_ammo_lower, object_tracker.current_ammo_upper = lo, up
                print("[INFO] calibrada MUNICION:", lo, up)
            else:
                print("[WARN] dibuja ROI sobre la municion")


def main():
    rospy.init_node("board_node", anonymous=True)
    node = BoardNode()
    rospy.loginfo("[board_node] Nodo de tablero iniciado.")
    rospy.spin()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
