for host in lab4 lab6
do
  for f in sync_client sync_server peerconnection_client_headless peerconnection_server_headless
  do
    rsync ~/Workspace/webrtc/src/out/Default/$f $host:~/bin/
  done
done
