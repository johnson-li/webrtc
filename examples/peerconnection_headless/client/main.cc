/*
 *  Copyright 2012 The WebRTC Project Authors. All rights reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#include <stdio.h>

#include "absl/flags/parse.h"
#include "api/scoped_refptr.h"
#include "examples/peerconnection_headless/client/conductor.h"
#include "examples/peerconnection_headless/client/flag_defs.h"
#include "examples/peerconnection_headless/client/peer_connection_client.h"
#include "rtc_base/physical_socket_server.h"
#include "rtc_base/ref_counted_object.h"
#include "rtc_base/ssl_adapter.h"
#include "rtc_base/thread.h"
#include "system_wrappers/include/field_trial.h"
#include "test/field_trial.h"

class CustomSocketServer : public rtc::PhysicalSocketServer {
 public:
  explicit CustomSocketServer()
      : conductor_(NULL), client_(NULL) {}

  void SetMessageQueue(rtc::Thread* queue) override { message_queue_ = queue; }

  void set_client(PeerConnectionClient* client) { client_ = client; }
  void set_conductor(Conductor* conductor) { conductor_ = conductor; }

  bool Wait(int cms, bool process_io) override {
    return rtc::PhysicalSocketServer::Wait(0 /*cms == -1 ? 1 : cms*/,
                                           process_io);
  }

 protected:
  rtc::Thread* message_queue_;
  Conductor* conductor_;
  PeerConnectionClient* client_;
};

void startLocalRenderer(std::unique_ptr<VideoRenderer>& localRenderer, webrtc::VideoTrackInterface* local_video) {
    localRenderer.reset(new VideoRenderer(local_video));
}

void stopLocalRenderer(std::unique_ptr<VideoRenderer>& localRenderer) {
    localRenderer.reset();
}

void startRemoteRenderer(std::unique_ptr<VideoRenderer>& remoteRenderer, webrtc::VideoTrackInterface* remote_video) {
    remoteRenderer.reset(new VideoRenderer(remote_video));
}

void stopRemoteRenderer(std::unique_ptr<VideoRenderer>& remoteRenderer, webrtc::VideoTrackInterface* remote_video) {
    remoteRenderer.reset();
}

void startLogin(Conductor* conductor, std::string server, int port) {
    conductor->StartLogin(server, port); 
}

int main(int argc, char* argv[]) {
  absl::ParseCommandLine(argc, argv);

  const std::string forced_field_trials = absl::GetFlag(FLAGS_force_fieldtrials);
  webrtc::field_trial::InitFieldTrialsFromString(forced_field_trials.c_str());

  const std::string server = absl::GetFlag(FLAGS_server);
  const int port = absl::GetFlag(FLAGS_port);

  CustomSocketServer socket_server;
  rtc::AutoSocketServerThread thread(&socket_server);

  rtc::InitializeSSL();
  PeerConnectionClient client;
  rtc::scoped_refptr<Conductor> conductor(new rtc::RefCountedObject<Conductor>(&client));
  socket_server.set_client(&client);
  socket_server.set_conductor(conductor);

  thread.Run();

  startLogin(conductor, server, port);

  rtc::CleanupSSL();
  return 0;
}
