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
#include <sys/socket.h>
#include <fcntl.h>
#include <arpa/inet.h>
#include <sys/un.h>
#include "cuda.h"

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
    return rtc::PhysicalSocketServer::Wait(-1 /*cms == -1 ? 1 : cms*/,
                                           process_io);
  }

 protected:
  rtc::Thread* message_queue_;
  Conductor* conductor_;
  PeerConnectionClient* client_;
  bool logging_;
};

void init_cuda() {
  cuInit(0);
  int nGpu = 0;
  cuDeviceGetCount(&nGpu);
  auto iGpu = nGpu - 1;
  CUdevice cuDevice = 0;
  cuDeviceGet(&cuDevice, iGpu);
  char szDeviceName[80];
  cuDeviceGetName(szDeviceName, sizeof(szDeviceName), cuDevice);
  RTC_INFO << "GPU in use: #" << iGpu << " " << szDeviceName;
}

int main(int argc, char* argv[]) {
  init_cuda();

  RTC_TS << "Program started";
  absl::ParseCommandLine(argc, argv);

  const std::string forced_field_trials =
      absl::GetFlag(FLAGS_force_fieldtrials);
  webrtc::field_trial::InitFieldTrialsFromString(forced_field_trials.c_str());
  const std::string server = absl::GetFlag(FLAGS_server);
  const std::string name = absl::GetFlag(FLAGS_name);
  const std::string path = absl::GetFlag(FLAGS_path);
  const std::string dump_path = absl::GetFlag(FLAGS_dump_path);
  const std::string obs_socket = absl::GetFlag(FLAGS_obs_socket);
  const int port = absl::GetFlag(FLAGS_port);
  const int width = absl::GetFlag(FLAGS_width);
  const int fps = absl::GetFlag(FLAGS_fps);
  const bool receiving_only = absl::GetFlag(FLAGS_receiving_only);
  const std::string resolution = absl::GetFlag(FLAGS_resolution);

  RTC_TS << "Obs socket: " << obs_socket;
  if (!receiving_only && !obs_socket.empty()) {
    OBS_SOCKET_FD = socket(AF_UNIX, SOCK_DGRAM, 0);
    int flags = ::fcntl(OBS_SOCKET_FD, F_GETFL);
    ::fcntl(OBS_SOCKET_FD, F_SETFL, flags | O_NONBLOCK);
    struct sockaddr_un server {
      .sun_family = AF_UNIX,
    };
    strncpy(server.sun_path, obs_socket.c_str(), sizeof(server.sun_path) - 1);
    ::connect(OBS_SOCKET_FD, (struct sockaddr *)&server, sizeof(server));
    rtc::ObsProgramStart obs {
      .ts = (uint64_t) TS(),
    };
    auto data = reinterpret_cast<const uint8_t*>(&obs);
    send(OBS_SOCKET_FD, data, sizeof(obs), 0);
    RTC_TS << "Enable observation on " << obs_socket;
  }

  CustomSocketServer socket_server{!receiving_only};
  rtc::AutoSocketServerThread thread(&socket_server);

  rtc::InitializeSSL();
  PeerConnectionClient client;
  auto conductor = rtc::make_ref_counted<Conductor>(&client, receiving_only, width, fps, path, dump_path);
  socket_server.set_client(&client);
  socket_server.set_conductor(conductor.get());

  if (receiving_only) {
    client.StartListen(server, port);
  } else {
    client.StartConnect(server, port);
  }
  thread.Run();

  rtc::CleanupSSL();
  return 0;
}
