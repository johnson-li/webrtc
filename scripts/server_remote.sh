#!/bin/bash

session_name=server
tmux has-session -t ${session_name} 2> /dev/null; if [[ $? == 0 ]]; then tmux kill-session -t ${session_name}; fi
tmux new-session -ds ${session_name}
tmux send-key -t ${session_name}:0 'conda activate webrtc-exp8' Enter
for i in `seq 4`; do
    tmux new-window -t ${session_name}:$i
    tmux send-key -t ${session_name}:$i 'conda activate webrtc-exp8' Enter
done

tmux send-key -t ${session_name}:0 'killall peerconnection_client_headless' Enter
tmux send-key -t ${session_name}:0 'killall peerconnection_server_headless' Enter
tmux send-key -t ${session_name}:0 'mkdir -p /tmp/webrtc/logs' Enter
tmux send-key -t ${session_name}:0 '/tmp/webrtc/peerconnection_server_headless' Enter
sleep 1
tmux send-key -t ${session_name}:1 '/tmp/webrtc/peerconnection_client_headless --receiving_only --logger /tmp/webrtc/logs/client1.logb > /tmp/webrtc/logs/client1.log 2>&1' Enter
tmux send-key -t ${session_name}:2 '/tmp/webrtc/sync_server' Enter
tmux send-key -t ${session_name}:3 'cd /tmp/webrtc/yolov5' Enter
tmux send-key -t ${session_name}:3 'python -m stream -s 1920 > /tmp/webrtc/logs/stream.log' Enter
