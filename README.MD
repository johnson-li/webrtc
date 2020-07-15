Offloading-based Object Detection Benchmark Platform 
===


Participants
===
1. Client: responsible for webcam capturing, video streaming (sender), and result analysing.
2. Server: responsible for video streaming (receiver), object detection, and feedback.
3. Local: collect logs from the client and the server, calculating and illustrating statics.


Major Procedures
===
1. [Client] Feed the dataset (video frames) into the fake webcam.
2. [Client] Stream the video frames to the server.
3. [Server] Receive the video frames and share them via shared memory for inter process communication (IPC).
4. [Server] Process the video frames with neural network and feedback with the detected objects.
5. [Client] Calculate the video frame processing latency and the object detection accuracy.
6. [Local] Download logs from client and server, calculating statics.


Libraries
===
1. https://github.com/johnson-li/webrtc, a tool for video transmission and performance (latency and accuracy) analysis.
2. ~~https://github.com/johnson-li/yolov3, an object detection library that relies on yolov3~~ 
(Replace by newer version of yolo).
3. https://github.com/johnson-li/yolov5, an object detection library that relies on yolov5.


Network Ports
===
1. Server port for detected objects: 4400
2. Client port for fake webcam initiation: 4401

Setup Instructions
===
There are two set of experiments:
1. Local-based. Both the client and the server run on the same machine and they communicate via localhost. 
Check [SETUP_LOCAL.MD](./SETUP_LOCAL.MD) for more details.
2. Edge-based. The client runs on a laptop (vehicle) which use smart phone to connect to the 5G network 
and the server runs on a physical machine (edge server) deployed close to the 5G core network. 
They communicate via wireless network. Check [SETUP_EDGE.MD](./SETUP_EDGE.MD) for more details.