#!/bin/bash

tmux send-keys -t 0:3 'cd ~/Workspace/webrtc-controller/python_src && python -m experiment.fakewebcam' Enter
sleep 1
tmux send-keys -t 0:0 'cd ~/Workspace/webrtc/src && ./out/Default/peerconnection_server_headless' Enter
sleep 1
tmux send-keys -t 0:1 'cd ~/Workspace/webrtc/src && ./out/Default/peerconnection_client_headless --receiving_only --server 127.0.0.1 --logger /tmp/webrtc/logs/client1.logb > /tmp/webrtc/logs/client1.log 2>&1' Enter
sleep 1
tmux send-keys -t 0:2 'cd ~/Workspace/webrtc/src && ./out/Default/peerconnection_client_headless --resolution 1920x1280 --server 127.0.0.1 --logger /tmp/webrtc/logs/client2.logb > /tmp/webrtc/logs/client2.log 2>&1' Enter

echo wait for 10s
sleep 10

echo kill processes
killall -SIGINT peerconnection_client_headless
killall -SIGINT peerconnection_server_headless
killall -SIGINT python

