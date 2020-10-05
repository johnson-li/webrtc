#!/bin/bash

session_name=client
tmux has-session -t ${session_name} 2> /dev/null; if [[ $? == 0 ]]; then tmux kill-session -t ${session_name}; fi
tmux new-session -ds ${session_name}
for i in $(seq 6); do
    tmux new-window -t ${session_name}:$i
    tmux send-key -t ${session_name}:$i 'conda activate webrtc-exp8' Enter
done

tmux send-key -t ${session_name}:0 'mkdir -p /tmp/webrtc/logs' Enter
tmux send-key -t ${session_name}:0 "conda activate webrtc-exp7" Enter
tmux send-key -t ${session_name}:0 "cd /tmp/webrtc/python_src" Enter
tmux send-key -t ${session_name}:0 "python -m experiment.fakewebcam" Enter
tmux send-key -t ${session_name}:1 "/tmp/webrtc/sync_client ${server_ip} > /tmp/webrtc/logs/sync.log" Enter
tmux send-key -t ${session_name}:2 'while [[ `echo ""| nc -u localhost 4401 -w1` != "True" ]]; do echo "Wait for the fake webcam" `date`; done' Enter
tmux send-key -t ${session_name}:2 "sleep 1 && /tmp/webrtc/peerconnection_client_headless --server ${server_ip} --resolution 1920x1280 --logger /tmp/webrtc/logs/client2.logb > /tmp/webrtc/logs/client2.log 2>&1" Enter
tmux send-key -t ${session_name}:3 "cd /tmp/webrtc/python_src" Enter
tmux send-key -t ${session_name}:3 "python -m experiment.client -s ${server_ip} --logger /tmp/webrtc/logs/detections.log" Enter
# tmux send-key -t ${session_name}:4 'sudo /tmp/webrtc/NetworkMonitor --dev enp0s20f0u3 --protocol udp > /tmp/webrtc/logs/network_client.log' Enter
tmux send-key -t ${session_name}:4 'sudo /tmp/webrtc/NetworkMonitor --dev enp59s0u1 --protocol udp > /tmp/webrtc/logs/network_client.log' Enter
