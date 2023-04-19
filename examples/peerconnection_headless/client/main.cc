/*
 *  Copyright 2012 The WebRTC Project Authors. All rights reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#include <iostream>
#include <stdio.h>

#include "absl/flags/parse.h"
#include "api/scoped_refptr.h"
#include "examples/peerconnection_headless/client/conductor.h"
#include "examples/peerconnection_headless/client/flag_defs.h"
#include "examples/peerconnection_headless/client/peer_connection_client.h"
#include "rtc_base/physical_socket_server.h"
#include "rtc_base/ssl_adapter.h"
#include "rtc_base/thread.h"
#include "system_wrappers/include/field_trial.h"
#include "test/field_trial.h"
#include "base/debug/stack_trace.h"

class CustomSocketServer : public rtc::PhysicalSocketServer {
 public:
  explicit CustomSocketServer(bool logging)
      : conductor_(NULL), client_(NULL), logging_(logging) {}
  virtual ~CustomSocketServer() {}

  void SetMessageQueue(rtc::Thread* queue) override { message_queue_ = queue; }

  void set_client(PeerConnectionClient* client) { client_ = client; }
  void set_conductor(Conductor* conductor) { conductor_ = conductor; }

  bool Wait(int cms, bool process_io) override {
    if (logging_) {
      // base::debug::StackTrace().Print();
    }
    return rtc::PhysicalSocketServer::Wait(0 /*cms == -1 ? 1 : cms*/,
                                           process_io);
  }

 protected:
  rtc::Thread* message_queue_;
  Conductor* conductor_;
  PeerConnectionClient* client_;
  bool logging_;
};

void startLogin(Conductor* conductor, std::string server, int port, std::string name) {
  conductor->StartLogin(server, port, name);
}

int main(int argc, char* argv[]) {
  absl::ParseCommandLine(argc, argv);

  // InitFieldTrialsFromString stores the char*, so the char array must outlive
  // the application.
  const std::string forced_field_trials =
      absl::GetFlag(FLAGS_force_fieldtrials);
  webrtc::field_trial::InitFieldTrialsFromString(forced_field_trials.c_str());
  const std::string server = absl::GetFlag(FLAGS_server);
  const std::string name = absl::GetFlag(FLAGS_name);
  const int port = absl::GetFlag(FLAGS_port);
  const bool receiving_only = absl::GetFlag(FLAGS_receiving_only);
  const std::string resolution = absl::GetFlag(FLAGS_resolution);

  CustomSocketServer socket_server{!receiving_only};
  rtc::AutoSocketServerThread thread(&socket_server);

  rtc::InitializeSSL();
  // Must be constructed after we set the socketserver.
  PeerConnectionClient client;
  auto conductor = rtc::make_ref_counted<Conductor>(&client, receiving_only);
  socket_server.set_client(&client);
  socket_server.set_conductor(conductor.get());

  startLogin(conductor.get(), server, port, name);
  thread.Run();

  rtc::CleanupSSL();
  return 0;
}
