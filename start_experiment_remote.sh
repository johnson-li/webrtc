killall peerconnection_client_headless
killall peerconnection_server_headless

tmux has-session -t webrtc 2> /dev/null; if [[ $? == 0 ]]; then tmux kill-session -t webrtc; fi
tmux new-session -ds webrtc
for i in `seq 4`; do
    tmux new-window -t webrtc:$i
done

tmux send-key -t webrtc:0 'cd ~/Workspace/webrtc/src && ./out/Default/peerconnection_server_headless > experiment/server.log 2>&1' Enter
tmux send-key -t webrtc:1 'cd ~/Workspace/webrtc/src && ./out/Default/peerconnection_client_headless --logger experiment/client1.logb > experiment/client1.log 2>&1' Enter

