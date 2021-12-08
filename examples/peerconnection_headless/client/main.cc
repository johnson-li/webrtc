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
#include <signal.h>
#include <unistd.h>

#include "absl/flags/parse.h"
#include "api/scoped_refptr.h"
#include "base/debug/stack_trace.h"
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

Conductor* conductor_ = NULL;
PeerConnectionClient client;

void startLogin(Conductor* conductor, std::string server, int port, std::string name) {
  conductor->StartLogin(server, port, name);
}

std::string LOGGER_PATH = "client.logb";
bool dumped = false;

void tearup(int signum) {
  RTC_LOG_TS << "Caught signal: " << signum;
  if (!dumped) {
    dumped = true;
    //LOGGER->print();
    //LOGGER->exportLog(LOGGER_PATH);
  }
  RTC_LOG_TS << "Exiting...";
  if (conductor_ != NULL && conductor_->Connected()) {
    RTC_LOG_TS << "Close conductor";
    conductor_->Close();
    rtc::CleanupSSL();
  } else {
    exit(0);
  }
}

void test() {
  auto* logger = base::debug::Logger::getLogger();
  auto index = logger->getIndex(base::debug::Logger::PlaceHolder);
  auto offset = 2;
  offset = logger->template write<uint64_t>(index, offset, base::debug::Logger::Timestamp, 123l);
  offset = logger->template write<uint16_t>(index, offset, base::debug::Logger::End, 0);
  index = logger->getIndex(base::debug::Logger::CaptureFrame);
  offset = 2;
  offset = logger->template write<uint64_t>(index, offset, base::debug::Logger::SequenceNumber, 123l);
  offset = logger->writeString(index, offset, base::debug::Logger::Info, "asdfasdf");
  offset = logger->template write<uint16_t>(index, offset, base::debug::Logger::End, 0);
  auto pair = logger->logWithTimestamp(base::debug::Logger::EncoderQueueEnqueue);
  offset = pair.second;
  offset = logger->template write<uint64_t>(index, offset, base::debug::Logger::SequenceNumber, 123l);
  logger->print();
}

int main(int argc, char* argv[]) {
  signal(SIGINT, tearup);
  absl::ParseCommandLine(argc, argv);

  const std::string forced_field_trials = absl::GetFlag(FLAGS_force_fieldtrials);
  webrtc::field_trial::InitFieldTrialsFromString(forced_field_trials.c_str());

  const std::string server = absl::GetFlag(FLAGS_server);
  const std::string name = absl::GetFlag(FLAGS_name);
  const std::string dump_dir = absl::GetFlag(FLAGS_dump);
  const int port = absl::GetFlag(FLAGS_port);
  const bool receiving_only = absl::GetFlag(FLAGS_receiving_only);
  LOGGER_PATH = absl::GetFlag(FLAGS_logger);
  const std::string resolution = absl::GetFlag(FLAGS_resolution);

  CustomSocketServer socket_server;
  rtc::AutoSocketServerThread thread(&socket_server);

  rtc::InitializeSSL();
  rtc::scoped_refptr<Conductor> conductor(new rtc::RefCountedObject<Conductor>(&client, receiving_only, resolution, dump_dir));
  conductor_ = conductor;
  socket_server.set_client(&client);
  socket_server.set_conductor(conductor);

  startLogin(conductor, server, port, name);
  thread.Run();

  rtc::CleanupSSL();
  return 0;
}


