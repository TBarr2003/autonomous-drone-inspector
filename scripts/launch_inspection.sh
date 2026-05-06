#!/bin/bash

export GZ_CONFIG_PATH=/usr/share/gz
export GZ_SIM_RESOURCE_PATH=/home/trist/PX4-Autopilot/Tools/simulation/gz/models
export ROS_DOMAIN_ID=0
export PX4_GZ_WORLD=inspection

source /opt/ros/jazzy/setup.bash
source /home/trist/drone_ws/install/setup.bash

echo "Starting Gazebo + PX4..."
cd /home/trist/PX4-Autopilot
make px4_sitl gz_x500_mono_cam &
PX4_PID=$!

echo "Waiting 20 seconds for Gazebo to initialize..."
sleep 20

echo "Starting camera bridge..."
BRIDGE_TOPIC="/world/default/model/x500_mono_cam_0/link/camera_link/sensor/camera/image"
ros2 run ros_gz_bridge parameter_bridge ${BRIDGE_TOPIC}@sensor_msgs/msg/Image@gz.msgs.Image &
BRIDGE_PID=$!

sleep 3

echo "Starting YOLO detection node..."
ros2 run drone_inspection yolo_detection_node &
YOLO_PID=$!

echo "All systems running. Press Ctrl+C to stop."
wait
