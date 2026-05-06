import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ultralytics import YOLO
import cv2

CLASS_NAMES = {0: 'crack', 1: 'corrosion', 2: 'spallation'}
COLORS = {0: (0, 0, 255), 1: (0, 165, 255), 2: (255, 0, 0)}

CAMERA_TOPIC = '/world/default/model/x500_mono_cam_0/link/camera_link/sensor/camera/image'

class YoloDetectionNode(Node):
    def __init__(self):
        super().__init__('yolo_detection_node')
        self.declare_parameter('model_path', '/home/trist/drone_inspection/weights/best.pt')
        self.declare_parameter('confidence', 0.25)

        model_path = self.get_parameter('model_path').get_parameter_value().string_value
        self.conf = self.get_parameter('confidence').get_parameter_value().double_value

        self.get_logger().info(f'Loading YOLO model from {model_path}')
        self.model = YOLO(model_path)
        self.model.to('cpu')
        self.bridge = CvBridge()
        self.frame_count = 0
        self.detection_count = 0

        # Try both QoS profiles
        qos_reliable = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            durability=DurabilityPolicy.VOLATILE
        )

        self.subscription = self.create_subscription(
            Image, CAMERA_TOPIC, self.image_callback, qos_reliable)

        self.publisher = self.create_publisher(Image, '/detection/image', 10)

        # Heartbeat timer
        self.timer = self.create_timer(5.0, self.heartbeat)
        self.get_logger().info(f'YOLO Node ready — subscribing to {CAMERA_TOPIC}')

    def heartbeat(self):
        self.get_logger().info(f'Heartbeat — frames received so far: {self.frame_count}')

    def image_callback(self, msg):
        self.frame_count += 1
        self.get_logger().info(f'Frame received #{self.frame_count} — size: {msg.width}x{msg.height}')

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='rgb8')
        except Exception as e:
            self.get_logger().warn(f'cv_bridge error: {e}')
            return

        results = self.model(frame, conf=self.conf, verbose=False)

        for result in results:
            for box in result.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                label = f"{CLASS_NAMES.get(cls, 'unknown')} {conf:.2f}"
                color = COLORS.get(cls, (255, 255, 255))
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                self.detection_count += 1
                self.get_logger().info(
                    f'Detected: {CLASS_NAMES.get(cls)} | conf={conf:.2f}')

        out_msg = self.bridge.cv2_to_imgmsg(frame, encoding='rgb8')
        self.publisher.publish(out_msg)

def main(args=None):
    rclpy.init(args=args)
    node = YoloDetectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info(f'Total detections: {node.detection_count}')
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
