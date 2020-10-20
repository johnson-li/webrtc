#!/bin/bash

cd ~/Workspace/webrtc/src
mkdir -p /tmp/webrtc/logs
mkdir -p /tmp/webrtc/yolov5
mkdir -p /tmp/webrtc/yolov5/utils
mkdir -p /tmp/webrtc/yolov5/models
mkdir -p /tmp/webrtc/yolov5/weights
sed -i "246s/.*/  max_bitrate = $bitrate;/" media/engine/webrtc_video_engine.cc
ninja -C out/Default -j"$(nproc)" >/tmp/webrtc/logs/compile.log

cp ~/Workspace/webrtc/src/out/Default/peerconnection_server_headless /tmp/webrtc
cp ~/Workspace/webrtc/src/out/Default/peerconnection_client_headless /tmp/webrtc
cp ~/Workspace/NetworkMonitor/build/NetworkMonitor /tmp/webrtc
cp ~/Workspace/webrtc/src/out/Default/sync_server /tmp/webrtc
cp ~/Workspace/webrtc-controller/scripts/server_remote.sh /tmp/webrtc
cp ~/Workspace/webrtc-controller/scripts/server_remote_init.sh /tmp/webrtc
cp ~/Workspace/webrtc-controller/scripts/server_remote_init_wrapper.sh /tmp/webrtc
cp ~/Workspace/yolov5/stream.py /tmp/webrtc/yolov5
cp ~/Workspace/yolov5/utils/__init__.py /tmp/webrtc/yolov5/utils
cp ~/Workspace/yolov5/utils/datasets.py /tmp/webrtc/yolov5/utils
cp ~/Workspace/yolov5/utils/utils.py /tmp/webrtc/yolov5/utils
cp ~/Workspace/yolov5/utils/google_utils.py /tmp/webrtc/yolov5/utils
cp ~/Workspace/yolov5/utils/torch_utils.py /tmp/webrtc/yolov5/utils
cp ~/Workspace/yolov5/models/yolov5s.yaml /tmp/webrtc/yolov5/models
cp ~/Workspace/yolov5/models/yolo.py /tmp/webrtc/yolov5/models
cp ~/Workspace/yolov5/models/experimental.py /tmp/webrtc/yolov5/models
cp ~/Workspace/yolov5/models/common.py /tmp/webrtc/yolov5/models
cp ~/Workspace/yolov5/weights/yolov5s.pt /tmp/webrtc/yolov5/weights
