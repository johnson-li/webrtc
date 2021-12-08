for f in sync_client sync_server peerconnection_client_headless peerconnection_server_headless
do
rsync mobix:~/Workspace/webrtc/src/out/Default/$f ~/bin/
done
