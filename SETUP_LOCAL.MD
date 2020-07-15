Download the code
===
0. Supposing you are working on the directory ~/Workspace 
    ```shell script
    cd ~/Workspace
    ```
1. Get the webrtc code
    ```shell script
    cp -r /home/lix16/Workspace/webrtc .  # run this if you are on lab6
    scp -r lab6:/home/lix16/Workspace/webrtc .  # run this if you are not on lab6
    ```

2. Get the webrtc-controller
    ```shell script
    git clone -b controller git@github.com:johnson-li/webrtc.git webrtc-controller
    ```

3. Get the yolo codes
    ```shell script
    git clone -b johnson git@github.com:johnson-li/yolov5.git 
    ```
   
4. Setup running environment
    ```shell script
    mkdir -p /tmp/webrtc/logs
   
    conda create -n dev7 python=3.7
    conda create -n dev8 python=3.8
   
    conda activate dev7
    cd ~/Workspace/webrtc-controller
    pip install -r requirements.txt
    cd ~/Workspace/webrtc-controller/python_src
    pip install -r requirements.txt
     
    conda activate dev8
    cd ~/Workspace/yolov5
    pip install -r requirements.txt
   
    cd ~/Workspace/webrtc/src
    ninja -C out/Default # Run this command whenever you modified the WebRTC source code
    ```
   
5. Run the programmes. **It is recommended to run each program in a separate tmux window.**
    ```shell script
   
    # Fake webcam
    sudo modprobe v4l2loopback devices=2
    cd ~/Workspace/webrtc-controller/python_src
    conda activate dev7
    python -m experiment.fakewebcam  # Program 1: feed the dataset into the fake webcam
   
    # WebRTC 
    cd ~/Workspace/webrtc/src
    ./out/Default/peerconnection_server_headless  # Program 2: start the WebRTC server
    ./out/Default/peerconnection_client_headless --receiving_only --server 127.0.0.1 --logger /tmp/webrtc/logs/client1.logb > /tmp/webrtc/logs/client1.log 2>&1  # Program 3: start the WebRTC client for receiving the video stream 
    ./out/Default/peerconnection_client_headless --resolution 1920x1280 --server 127.0.0.1 --logger /tmp/webrtc/logs/client2.logb > /tmp/webrtc/logs/client2.log 2>&1 # Program 4: start the WebRTC client for sending the video stream
       
    # Object detection
    cd ~/Workspace/yolov5/
    conda activate dev8
    python -m stream -s 1920 > /tmp/webrtc/logs/stream.log  # Program 5: start the yolo for object detection
   
    # Receive the feedback
    cd ~/Workspace/webrtc-controller/python_src
    conda activate dev8 
    python -m experiment.client -l /tmp/webrtc/logs/detections.log -s 127.0.0.1  # Program 6: receive the object detection result
    ```

Log Files
===
 - /tmp/webrtc/logs/client1.log
 - /tmp/webrtc/logs/client2.log
 - /tmp/webrtc/logs/detections.log
 - /tmp/webrtc/logs/stream.log

Statics Analysing
===
```shell script
cd ~/Workspace/webrtc-controller
conda activate dev7
python -m analysis.main  # This program downloads the logs into the results directory and calculates some statics. Please check the code before using it.
```