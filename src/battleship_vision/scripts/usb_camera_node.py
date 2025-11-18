#!/usr/bin/env python3
import cv2
import rospy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image


class USBCameraNode:
    def __init__(self, node_name: str, default_topic: str, default_frame: str):
        rospy.init_node(node_name, anonymous=False)
        self.bridge = CvBridge()
        self.topic = rospy.get_param("~image_topic", default_topic)
        self.frame_id = rospy.get_param("~frame_id", default_frame)
        self.indices = rospy.get_param("~camera_indices", list(range(0, 10)))
        self.frame_width = rospy.get_param("~frame_width", 1280)
        self.frame_height = rospy.get_param("~frame_height", 720)
        publish_rate = rospy.get_param("~publish_rate", 10.0)
        self.rate = rospy.Rate(publish_rate)

        self.publisher = rospy.Publisher(self.topic, Image, queue_size=1)
        self.camera_index = None
        self.capture = None

    def _open_camera(self):
        for index in self.indices:
            rospy.loginfo("[%s] Trying camera index %d", rospy.get_name(), index)
            capture = cv2.VideoCapture(index)
            if not capture.isOpened():
                capture.release()
                continue

            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)

            ok, frame = capture.read()
            if not ok or frame is None:
                rospy.logwarn("[%s] Camera index %d opened but no frame captured", rospy.get_name(), index)
                capture.release()
                continue

            self.camera_index = index
            rospy.loginfo(
                "[%s] Using camera index %d publishing on %s", rospy.get_name(), index, self.topic
            )
            return capture

        rospy.logerr("[%s] No working camera found in indices %s", rospy.get_name(), self.indices)
        return None

    def _ensure_camera(self):
        if self.capture is None:
            self.capture = self._open_camera()
            if self.capture is None:
                rospy.sleep(1.0)
                return False
        return True

    def spin(self):
        while not rospy.is_shutdown():
            if not self._ensure_camera():
                continue

            ok, frame = self.capture.read()
            if not ok or frame is None:
                rospy.logwarn(
                    "[%s] Lost connection to camera index %s. Retrying other indices...",
                    rospy.get_name(),
                    self.camera_index,
                )
                self.capture.release()
                self.capture = None
                self.camera_index = None
                continue

            message = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            message.header.stamp = rospy.Time.now()
            message.header.frame_id = self.frame_id
            self.publisher.publish(message)
            self.rate.sleep()

    def shutdown(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None


def main(node_name: str, default_topic: str, default_frame: str):
    node = USBCameraNode(node_name=node_name, default_topic=default_topic, default_frame=default_frame)
    try:
        node.spin()
    except rospy.ROSInterruptException:
        pass
    finally:
        node.shutdown()


if __name__ == "__main__":
    rospy.loginfo("This module is intended to be imported by specific camera nodes.")
