#!/bin/bash

session_name=client
tmux has-session -t ${session_name} 2> /dev/null; if [[ $? == 0 ]]; then tmux kill-session -t ${session_name}; fi
tmux new-session -ds ${session_name}
for i in `seq 4`; do
    tmux new-window -t ${session_name}:$i
    tmux send-key -t ${session_name}:$i 'conda activate webrtc-exp8' Enter
done

tmux send-key -t ${session_name}:0 'killall peerconnection_client_headless' Enter
tmux send-key -t ${session_name}:0 'mkdir -p /tmp/webrtc/logs' Enter
tmux send-key -t ${session_name}:0 "conda activate webrtc-exp7" Enter
tmux send-key -t ${session_name}:0 "cd /tmp/webrtc/python_src" Enter
tmux send-key -t ${session_name}:0 "python -m experiment.fakewebcam" Enter
tmux send-key -t ${session_name}:1 "/tmp/webrtc/peerconnection_client_headless --server ${server_ip} --logger /tmp/webrtc/logs/client2.logb > /tmp/webrtc/logs/client2.log 2>&1" Enter
tmux send-key -t ${session_name}:2 "/tmp/webrtc/sync_client ${server_ip} > /tmp/webrtc/logs/sync.log" Enter

