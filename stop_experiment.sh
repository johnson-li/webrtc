ssh lab6 'killall -s SIGINT peerconnection_client_headless; killall -s SIGINT peerconnection_server_headless'

sleep 3

scp lab6:~/Workspace/webrtc/src/experiment/client1.log ./data
scp lab6:~/Workspace/webrtc/src/experiment/client1.logb ./data

