session_name=client-accu
tmux has-session -t ${session_name} 2> /dev/null; if [[ $? == 0 ]]; then tmux kill-session -t ${session_name}; fi
tmux new-session -ds ${session_name}
for i in `seq 4`; do
    tmux new-window -t ${session_name}:$i
    tmux send-key -t ${session_name}:$i 'conda activate webrtc-exp8' Enter
done

tmux send-key -t ${session_name}:0 'killall peerconnection_client_headless' Enter
tmux send-key -t ${session_name}:0 'killall peerconnection_server_headless' Enter
tmux send-key -t ${session_name}:0 'mkdir -p /tmp/webrtc/logs' Enter
tmux send-key -t ${session_name}:0 "conda activate webrtc-exp7" Enter
tmux send-key -t ${session_name}:0 "cd /tmp/webrtc/python_src" Enter
tmux send-key -t ${session_name}:0 "sudo modprobe v4l2loopback devices=2" Enter
# Start to feed fake webcam
tmux send-key -t ${session_name}:0 "python -m experiment.fakewebcam" Enter

# Start the webrtc server
tmux send-key -t ${session_name}:1 '/tmp/webrtc/peerconnection_server_headless > /tmp/webrtc/logs/server_accu.log 2>&1' Enter

# Start the webrtc client for receiving video stream
tmux send-key -t ${session_name}:2 "/tmp/webrtc/peerconnection_client_headless --server ${server_ip} --logger /tmp/webrtc/logs/client1.logb > /tmp/webrtc/logs/client1_accu.log 2>&1" Enter

# Wait for the fake webcam to be ready
tmux send-key -t ${session_name}:3 'while [[ `echo ""| nc -u localhost 4401 -w1` != "True" ]]; do echo "Wait for the fake webcam" `date`; done' Enter
# Start the webrtc client for sending video stream
tmux send-key -t ${session_name}:3 "/tmp/webrtc/peerconnection_client_headless --server ${server_ip} --logger /tmp/webrtc/logs/client2.logb > /tmp/webrtc/logs/client2.log 2>&1" Enter

tmux send-key -t ${session_name}:4 "cd /tmp/webrtc/python_src" Enter
# Start the
tmux send-key -t ${session_name}:4 "python -m experiment.client --logger /tmp/webrtc/logs/detections.log" Enter


