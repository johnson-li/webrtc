/*
 *  Copyright 2012 The WebRTC Project Authors. All rights reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#include "examples/peerconnection_headless/client/peer_connection_client.h"

#include "examples/peerconnection_headless/client/defaults.h"
#include "rtc_base/checks.h"
#include "rtc_base/logging.h"
#include "rtc_base/net_helpers.h"
#include "system_wrappers/include/clock.h"

namespace {

rtc::Socket* CreateClientSocket(int family) {
  rtc::Thread* thread = rtc::Thread::Current();
  RTC_DCHECK(thread != NULL);
  return thread->socketserver()->CreateSocket(family, SOCK_STREAM);
}

}  // namespace

PeerConnectionClient::PeerConnectionClient()
    : callback_(NULL), resolver_(NULL) {}

PeerConnectionClient::~PeerConnectionClient() {
  rtc::Thread::Current()->Clear(this);
}

void PeerConnectionClient::RegisterObserver(
    PeerConnectionClientObserver* callback) {
  RTC_DCHECK(!callback_);
  callback_ = callback;
}

bool PeerConnectionClient::SendToPeer(int peer_id, const std::string& message) {
  auto sent = hanging_get_->Send(message.c_str(), message.length());
  RTC_TS << "Sent " << sent << " bytes";
  return sent > 0;
}

bool PeerConnectionClient::GetHeaderValue(const std::string& data,
                                          size_t eoh,
                                          const char* header_pattern,
                                          size_t* value) {
  RTC_DCHECK(value != NULL);
  size_t found = data.find(header_pattern);
  if (found != std::string::npos && found < eoh) {
    *value = atoi(&data[found + strlen(header_pattern)]);
    return true;
  }
  return false;
}

bool PeerConnectionClient::GetHeaderValue(const std::string& data,
                                          size_t eoh,
                                          const char* header_pattern,
                                          std::string* value) {
  RTC_DCHECK(value != NULL);
  size_t found = data.find(header_pattern);
  if (found != std::string::npos && found < eoh) {
    size_t begin = found + strlen(header_pattern);
    size_t end = data.find("\r\n", begin);
    if (end == std::string::npos)
      end = eoh;
    value->assign(data.substr(begin, end - begin));
    return true;
  }
  return false;
}

bool PeerConnectionClient::ReadIntoBuffer(rtc::Socket* socket,
                                          std::string* data,
                                          size_t* content_length) {
  char buffer[0xffff];
  do {
    int bytes = socket->Recv(buffer, sizeof(buffer), nullptr);
    if (bytes <= 0)
      break;
    data->append(buffer, bytes);
  } while (true);

  bool ret = false;
  size_t i = data->find("\r\n\r\n");
  if (i != std::string::npos) {
    RTC_LOG(LS_INFO) << "Headers received";
    if (GetHeaderValue(*data, i, "\r\nContent-Length: ", content_length)) {
      size_t total_response_size = (i + 4) + *content_length;
      if (data->length() >= total_response_size) {
        ret = true;
        std::string should_close;
        const char kConnection[] = "\r\nConnection: ";
        if (GetHeaderValue(*data, i, kConnection, &should_close) &&
            should_close.compare("close") == 0) {
          socket->Close();
        }
      } else {
        // We haven't received everything.  Just continue to accept data.
      }
    } else {
      RTC_LOG(LS_ERROR) << "No content length field specified by the server.";
    }
  }
  return ret;
}

void PeerConnectionClient::OnGetMessage(rtc::Socket* socket) {
  std::string msg;
  size_t content_length = 0;
  ReadIntoBuffer(socket, &msg, &content_length);
  callback_->OnMessageFromPeer(1, msg);
}

void PeerConnectionClient::OnSenderConnect(rtc::Socket* socket) {
  hanging_get_.reset(socket->Accept(nullptr));
  hanging_get_->SignalReadEvent.connect(this,
                                        &PeerConnectionClient::OnGetMessage);
}

void PeerConnectionClient::StartListen(const std::string& ip, int port) {
  RTC_TS << "Start listen";
  rtc::SocketAddress listening_addr("0.0.0.0", port);
  control_socket_.reset(CreateClientSocket(listening_addr.ipaddr().family()));
  int err = control_socket_->Bind(listening_addr);
  if (err == SOCKET_ERROR) {
    control_socket_->Close();
    RTC_LOG(LS_ERROR) << "Failed to bind listen socket to port " << port;
    return;
  }
  control_socket_->Listen(1);
  control_socket_->SignalReadEvent.connect(
      this, &PeerConnectionClient::OnSenderConnect);
}

void PeerConnectionClient::StartConnect(const std::string& ip, int port) {
  RTC_TS << "Start connection";
  rtc::SocketAddress send_to_addr(ip, port);
  hanging_get_.reset(CreateClientSocket(send_to_addr.ipaddr().family()));
  hanging_get_->SignalReadEvent.connect(this,
                                           &PeerConnectionClient::OnGetMessage);
  RTC_TS << "Connecting";
  int err = hanging_get_->Connect(send_to_addr);
  RTC_TS << "Connecting result: " << err;

  if (err == SOCKET_ERROR) {
    hanging_get_->Close();
    RTC_LOG(LS_ERROR) << "Failed to connect to receiver";
    return;
  } else {
    callback_->ConnectToPeer(1);
  }
}