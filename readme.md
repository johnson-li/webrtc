Offloading-based Object Detection Benchmark Platform 
===


Participants
===
1. Vehicle (Client): lab7, responsible for webcam capturing, video streaming, and benchmarking.
2. MEC (Server): lab4/inari, responsible for video streaming, object detection (offloading), and feedbacking.


Procedures
===
1. [Client] Feed the dataset (video frames) into the fake webcam.
2. [Client] Stream the video frams to the remote peer.
3. [Server] Receive the video frames and share them via shared memory for IPC.
4. [Server] Process the video frames with neural network and feedback the detected objects.
5. [Client] Calculate the video frame processing latency and the object detection accuracy.


Libraries
===
1. https://github.com/johnson-li/webrtc, a tool for video transmission and performance (latency and accuracy) analysis.
2. https://github.com/johnson-li/yolov3, an object detection library that relies on yolo.


Ports
===

1. Server port for detected objects: 4400
2. Client port for fake webcam initiation: 4401

