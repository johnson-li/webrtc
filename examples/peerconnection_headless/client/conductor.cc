/*
 *  Copyright 2012 The WebRTC Project Authors. All rights reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#include "examples/peerconnection_headless/client/conductor.h"

#include <stddef.h>
#include <stdint.h>

#include <memory>
#include <utility>
#include <vector>
#include <iostream>

#include "absl/memory/memory.h"
#include "absl/types/optional.h"
#include "api/audio/audio_mixer.h"
#include "api/audio_codecs/audio_decoder_factory.h"
#include "api/audio_codecs/audio_encoder_factory.h"
#include "api/audio_codecs/builtin_audio_decoder_factory.h"
#include "api/audio_codecs/builtin_audio_encoder_factory.h"
#include "api/audio_options.h"
#include "api/create_peerconnection_factory.h"
#include "api/rtp_sender_interface.h"
#include "api/task_queue/default_task_queue_factory.h"
#include "api/test/create_frame_generator.h"
#include "api/video_codecs/builtin_video_decoder_factory.h"
#include "api/video_codecs/builtin_video_encoder_factory.h"
#include "api/video_codecs/video_decoder_factory.h"
#include "api/video_codecs/video_encoder_factory.h"
#include "examples/peerconnection_headless/client/defaults.h"
#include "modules/audio_device/include/audio_device.h"
#include "modules/audio_processing/include/audio_processing.h"
#include "modules/video_capture/video_capture.h"
#include "modules/video_capture/video_capture_factory.h"
#include "p2p/base/port_allocator.h"
#include "pc/video_track_source.h"
#include "rtc_base/checks.h"
#include "rtc_base/logging.h"
#include "rtc_base/rtc_certificate_generator.h"
#include "rtc_base/strings/json.h"
#include "test/vcm_capturer.h"
#include "test/frame_generator_capturer.h"

namespace {
// Names used for a IceCandidate JSON object.
const char kCandidateSdpMidName[] = "sdpMid";
const char kCandidateSdpMlineIndexName[] = "sdpMLineIndex";
const char kCandidateSdpName[] = "candidate";

// Names used for a SessionDescription JSON object.
const char kSessionDescriptionTypeName[] = "type";
const char kSessionDescriptionSdpName[] = "sdp";

class DummySetSessionDescriptionObserver
    : public webrtc::SetSessionDescriptionObserver {
 public:
  static rtc::scoped_refptr<DummySetSessionDescriptionObserver> Create() {
    return rtc::make_ref_counted<DummySetSessionDescriptionObserver>();
  }
  virtual void OnSuccess() { RTC_LOG(LS_INFO) << __FUNCTION__; }
  virtual void OnFailure(webrtc::RTCError error) {
    RTC_LOG(LS_INFO) << __FUNCTION__ << " " << ToString(error.type()) << ": "
                     << error.message();
  }
};

class CapturerTrackSource : public webrtc::VideoTrackSource {
 public:
  static rtc::scoped_refptr<CapturerTrackSource> Create() {
    const size_t kWidth = 640;
    const size_t kHeight = 480;
    const size_t kFps = 30;
    std::unique_ptr<webrtc::test::VcmCapturer> capturer;
    std::unique_ptr<webrtc::VideoCaptureModule::DeviceInfo> info(
        webrtc::VideoCaptureFactory::CreateDeviceInfo());
    if (!info) {
      return nullptr;
    }
    int num_devices = info->NumberOfDevices();
    for (int i = num_devices - 1; i >= 0; --i) {
      capturer = absl::WrapUnique(
          webrtc::test::VcmCapturer::Create(kWidth, kHeight, kFps, i));
      if (capturer) {
        return rtc::make_ref_counted<CapturerTrackSource>(std::move(capturer));
      }
    }
    return nullptr;
  }

 protected:
  explicit CapturerTrackSource(
      std::unique_ptr<webrtc::test::VcmCapturer> capturer)
      : VideoTrackSource(/*remote=*/false), capturer_(std::move(capturer)) {}

 private:
  rtc::VideoSourceInterface<webrtc::VideoFrame>* source() override {
    return capturer_.get();
  }
  std::unique_ptr<webrtc::test::VcmCapturer> capturer_;
};

class FrameGeneratorTrackSource: public webrtc::VideoTrackSource {
  public:
    static rtc::scoped_refptr<FrameGeneratorTrackSource> Create(uint32_t width, uint32_t fps, std::string path) {
      std::ostringstream filename;
      filename << path << "/drive_" << width << "p.yuv";
      std::unique_ptr<webrtc::test::FrameGeneratorInterface> yuv_frame_generator(
        webrtc::test::CreateFromYuvFileFrameGenerator(
            std::vector<std::string>{filename.str()}, 
            width / 9 * 16, width, 1));
      std::unique_ptr<webrtc::test::FrameGeneratorCapturer> capturer(
        new webrtc::test::FrameGeneratorCapturer(
            webrtc::Clock::GetRealTimeClock(),        /* clock */
            std::move(yuv_frame_generator),           /* frame_generator */
            fps,                 /* target_fps*/
            *webrtc::CreateDefaultTaskQueueFactory())); /* task_queue_factory */
      return rtc::make_ref_counted<FrameGeneratorTrackSource>(std::move(capturer));
    }
  
  protected:
    explicit FrameGeneratorTrackSource(std::unique_ptr<webrtc::test::FrameGeneratorCapturer> capturer)
        : VideoTrackSource(/*remote=*/false), capturer_(std::move(capturer)) {
          if (capturer_ && capturer_->Init()) {
            capturer_->Start();
          }
        }
  
  private:
    rtc::VideoSourceInterface<webrtc::VideoFrame>* source() override {
      return capturer_.get();
    }
    std::unique_ptr<webrtc::test::FrameGeneratorCapturer> capturer_;
  };
}  // namespace

Conductor::Conductor(PeerConnectionClient* client, bool receiving_only, 
                     uint32_t width, uint32_t fps, std::string path, std::string dump_path)
    : peer_id_(-1), remote_peer_(-1), width_(width), fps_(fps), loopback_(false), 
      receiving_only_(receiving_only), flag_(false), path_(path), 
      dump_path_(dump_path), client_(client) {
  client_->RegisterObserver(this);
  RTC_INFO << "Dump path: " << dump_path_;
}

Conductor::~Conductor() {
  RTC_DCHECK(!peer_connection_);
}

bool Conductor::InitializePeerConnection() {
  RTC_DCHECK(!peer_connection_factory_);
  RTC_DCHECK(!peer_connection_);

  if (!signaling_thread_.get()) {
    signaling_thread_ = rtc::Thread::CreateWithSocketServer();
    signaling_thread_->Start();
  }
  peer_connection_factory_ = webrtc::CreatePeerConnectionFactory(
      nullptr /* network_thread */, nullptr /* worker_thread */,
      signaling_thread_.get(), nullptr /* default_adm */,
      webrtc::CreateBuiltinAudioEncoderFactory(),
      webrtc::CreateBuiltinAudioDecoderFactory(),
      // nullptr, nullptr,
      webrtc::CreateBuiltinVideoEncoderFactory(),
      webrtc::CreateBuiltinVideoDecoderFactory(), nullptr /* audio_mixer */,
      nullptr /* audio_processing */);

  if (!peer_connection_factory_) {
    RTC_LOG(LS_ERROR) << "Failed to initialize PeerConnectionFactory";
    return false;
  }

  if (!CreatePeerConnection()) {
    RTC_ERROR << "CreatePeerConnection failed";
  }

  if (!receiving_only_) {
    AddTracks();
  }

  return peer_connection_ != nullptr;
}

bool Conductor::ReinitializePeerConnectionForLoopback() {
  loopback_ = true;
  std::vector<rtc::scoped_refptr<webrtc::RtpSenderInterface>> senders =
      peer_connection_->GetSenders();
  peer_connection_ = nullptr;
  // Loopback is only possible if encryption is disabled.
  webrtc::PeerConnectionFactoryInterface::Options options;
  options.disable_encryption = true;
  peer_connection_factory_->SetOptions(options);
  if (CreatePeerConnection()) {
    for (const auto& sender : senders) {
      RTC_INFO << "Add track";
      peer_connection_->AddTrack(sender->track(), sender->stream_ids());
    }
    peer_connection_->CreateOffer(
        this, webrtc::PeerConnectionInterface::RTCOfferAnswerOptions());
  }
  options.disable_encryption = false;
  peer_connection_factory_->SetOptions(options);
  return peer_connection_ != nullptr;
}

bool Conductor::CreatePeerConnection() {
  RTC_DCHECK(peer_connection_factory_);
  RTC_DCHECK(!peer_connection_);

  webrtc::PeerConnectionInterface::RTCConfiguration config;
  // config.sdp_semantics = webrtc::SdpSemantics::kUnifiedPlan;
  config.set_video_rtcp_report_interval_ms(100);
  webrtc::PeerConnectionInterface::IceServer server;
  server.uri = GetPeerConnectionString();
  config.servers.push_back(server);

  webrtc::PeerConnectionDependencies pc_dependencies(this);
  auto error_or_peer_connection =
      peer_connection_factory_->CreatePeerConnectionOrError(
          config, std::move(pc_dependencies));
  if (error_or_peer_connection.ok()) {
    peer_connection_ = std::move(error_or_peer_connection.value());
  }
  return peer_connection_ != nullptr;
}

void Conductor::OnAddTrack(
    rtc::scoped_refptr<webrtc::RtpReceiverInterface> receiver,
    const std::vector<rtc::scoped_refptr<webrtc::MediaStreamInterface>>&
        streams) {
  OperationCallback(NEW_TRACK_ADDED, receiver->track().release());
}

void Conductor::OnRemoveTrack(
    rtc::scoped_refptr<webrtc::RtpReceiverInterface> receiver) {
  OperationCallback(TRACK_REMOVED, receiver->track().release());
}

void Conductor::OnIceCandidate(const webrtc::IceCandidateInterface* candidate) {
  // For loopback test. To save some connecting delay.
  if (loopback_) {
    if (!peer_connection_->AddIceCandidate(candidate)) {
      RTC_LOG(LS_WARNING) << "Failed to apply the received candidate";
    }
    return;
  }

  Json::Value jmessage;
  jmessage[kCandidateSdpMidName] = candidate->sdp_mid();
  jmessage[kCandidateSdpMlineIndexName] = candidate->sdp_mline_index();
  std::string sdp;
  if (!candidate->ToString(&sdp)) {
    RTC_LOG(LS_ERROR) << "Failed to serialize candidate";
    return;
  }
  jmessage[kCandidateSdpName] = sdp;

  Json::StreamWriterBuilder factory;
  SendMessage(Json::writeString(factory, jmessage));
}

void Conductor::OnMessageFromPeer(int peer_id, const std::string& message) {
  RTC_INFO << "OnMessageFromPeer";
  rtc::Thread::Current()->PostTask(
		[=] { OnMessageFromPeerOnNextIter(peer_id, message); });
}

void Conductor::OnMessageFromPeerOnNextIter(int peer_id, const std::string& message) {
  RTC_DCHECK(!message.empty());

  if (!peer_connection_.get()) {
    if (!InitializePeerConnection()) {
      RTC_LOG(LS_ERROR) << "Failed to initialize our PeerConnection instance";
      return;
    }
  } 
  Json::CharReaderBuilder factory;
  std::unique_ptr<Json::CharReader> reader =
      absl::WrapUnique(factory.newCharReader());
  Json::Value jmessage;
  if (!reader->parse(message.data(), message.data() + message.length(),
                     &jmessage, nullptr)) {
    RTC_LOG(LS_WARNING) << "Received unknown message. " << message;
    return;
  }
  std::string type_str;
  std::string json_object;

  rtc::GetStringFromJsonObject(jmessage, kSessionDescriptionTypeName,
                               &type_str);
  if (!type_str.empty()) {
    if (type_str == "offer-loopback") {
      // This is a loopback call.
      // Recreate the peerconnection with DTLS disabled.
      if (!ReinitializePeerConnectionForLoopback()) {
        RTC_ERROR << "Failed to initialize our PeerConnection instance";
      }
      return;
    }
    absl::optional<webrtc::SdpType> type_maybe =
        webrtc::SdpTypeFromString(type_str);
    if (!type_maybe) {
      RTC_ERROR << "Unknown SDP type: " << type_str;
      return;
    }
    webrtc::SdpType type = *type_maybe;
    std::string sdp;
    if (!rtc::GetStringFromJsonObject(jmessage, kSessionDescriptionSdpName,
                                      &sdp)) {
      RTC_ERROR
          << "Can't parse received session description message.";
      return;
    }
    webrtc::SdpParseError error;
    std::unique_ptr<webrtc::SessionDescriptionInterface> session_description =
        webrtc::CreateSessionDescription(type, sdp, &error);
    // std::string s;
    // session_description->ToString(&s);
    // RTC_INFO << "Session desc: " << s;
    if (!session_description) {
      RTC_ERROR
          << "Can't parse received session description message. "
             "SdpParseError was: "
          << error.description;
      return;
    }
    peer_connection_->SetRemoteDescription(
        DummySetSessionDescriptionObserver::Create().get(),
        session_description.release());
    RTC_INFO << "Remote streams: " << peer_connection_->GetSenders().size();
    if (type == webrtc::SdpType::kOffer) {
      auto options = webrtc::PeerConnectionInterface::RTCOfferAnswerOptions();
      // options.num_simulcast_layers = 2;
      peer_connection_->CreateAnswer(
          this, options);
    }
  } else {
    std::string sdp_mid;
    int sdp_mlineindex = 0;
    std::string sdp;
    if (!rtc::GetStringFromJsonObject(jmessage, kCandidateSdpMidName,
                                      &sdp_mid) ||
        !rtc::GetIntFromJsonObject(jmessage, kCandidateSdpMlineIndexName,
                                   &sdp_mlineindex) ||
        !rtc::GetStringFromJsonObject(jmessage, kCandidateSdpName, &sdp)) {
      RTC_LOG(LS_WARNING) << "Can't parse received message.";
      return;
    }
    webrtc::SdpParseError error;
    std::unique_ptr<webrtc::IceCandidateInterface> candidate(
        webrtc::CreateIceCandidate(sdp_mid, sdp_mlineindex, sdp, &error));
    if (!candidate.get()) {
      RTC_ERROR << "Can't parse received candidate message. "
                             "SdpParseError was: "
                          << error.description;
      return;
    }
    if (!peer_connection_->AddIceCandidate(candidate.get())) {
      RTC_ERROR << "Failed to apply the received candidate";
      return;
    }
  }
}

void Conductor::OnMessageSent(int err) {
  // Process the next pending message if any.
  OperationCallback(SEND_MESSAGE_TO_PEER, NULL);
}

void Conductor::ConnectToPeer(int peer_id) {
  // RTC_DCHECK(peer_id_ == -1);
  // RTC_DCHECK(peer_id != -1);
  RTC_INFO << "Connecting to peer: " << peer_id;

  if (peer_connection_.get()) {
    RTC_ERROR << "We only support connecting to one peer at a time";
    return;
  }

  if (InitializePeerConnection()) {
    // peer_id_ = peer_id;
    auto options = webrtc::PeerConnectionInterface::RTCOfferAnswerOptions();
    // options.num_simulcast_layers = 2;
    peer_connection_->CreateOffer(
        this, options);
  } else {
    RTC_ERROR << "Failed to initialize PeerConnection";
  }
}

void Conductor::OnServerConnectionFailure() {
  RTC_LOG(LS_ERROR) << "Failed to connect to " << server_;
}

void Conductor::AddTracks() {
  // RTC_TS << "asdf, " << (peer_connection_ != nullptr);
  if (!peer_connection_->GetSenders().empty()) {
    return;  // Already added tracks.
  }

  rtc::scoped_refptr<FrameGeneratorTrackSource> video_device =
      FrameGeneratorTrackSource::Create(width_, fps_, path_);
  if (video_device) {
    rtc::scoped_refptr<webrtc::VideoTrackInterface> video_track_(
        peer_connection_factory_->CreateVideoTrack(kVideoLabel,
                                                   video_device.get()));
    StartLocalRenderer(video_track_.get());

    webrtc::RtpTransceiverInit init;
    webrtc::RtpEncodingParameters para1, para2, para3;
    // auto scalability_mode = "L2T1";
    para1.rid = "q";
    para1.scale_resolution_down_by = 1;
    // para1.scalability_mode = scalability_mode;
    para2.rid = "h";
    para2.scale_resolution_down_by = 2;
    // para2.scalability_mode = scalability_mode;
    para3.rid = "f";
    para3.scale_resolution_down_by = 4;
    // para3.scalability_mode = scalability_mode;
    // init.send_encodings.emplace_back(para1);
    // init.send_encodings.emplace_back(para2);
    // init.send_encodings.emplace_back(para3);
    RTC_INFO << "Encoding size: " << init.send_encodings.size();
    peer_connection_->AddTransceiver(video_track_, init);
    RTC_INFO << "Senders: " << peer_connection_->GetSenders().size();
    auto result_or_error = peer_connection_->AddTrack(video_track_, {kStreamId});
    auto parameters = peer_connection_->GetSenders()[0]->GetParameters();
    RTC_INFO << "Encodings: " << parameters.encodings.size();
    if (!result_or_error.ok()) {
      RTC_LOG(LS_ERROR) << "Failed to add video track to PeerConnection: "
                        << result_or_error.error().message();
    }
  } else {
    RTC_ERROR << "OpenVideoCaptureDevice failed";
  }
}

void Conductor::StartLocalRenderer(webrtc::VideoTrackInterface* local_video) {
    local_renderer_.reset(new cricket::VideoRenderer("local", local_video));
}

void Conductor::StopLocalRenderer() {
    local_renderer_.reset();
}

void Conductor::StartRemoteRenderer(webrtc::VideoTrackInterface* remote_video) {
    remote_renderer_.reset(new cricket::VideoRenderer("remote", remote_video));
}

void Conductor::StopRemoteRenderer() {
    remote_renderer_.reset();
}

void Conductor::OperationCallback(int msg_id, void* data) {
  switch (msg_id) {
    case PEER_CONNECTION_CLOSED:
      break;

    case SEND_MESSAGE_TO_PEER: {
      RTC_TS << "SEND_MESSAGE_TO_PEER, peer id: " << peer_id_;
      std::string* msg = reinterpret_cast<std::string*>(data);
      if (!client_->SendToPeer(peer_id_, *msg)) {
        RTC_ERROR << "SendToPeer failed";
      }
      break;
    }

    case NEW_TRACK_ADDED: {
      auto* track = reinterpret_cast<webrtc::MediaStreamTrackInterface*>(data);
      if (track->kind() == webrtc::MediaStreamTrackInterface::kVideoKind) {
        auto* video_track = static_cast<webrtc::VideoTrackInterface*>(track);
        StartRemoteRenderer(video_track);
      }
      track->Release();
      break;
    }

    case TRACK_REMOVED: {
      // Remote peer stopped sending a track.
      auto* track = reinterpret_cast<webrtc::MediaStreamTrackInterface*>(data);
      track->Release();
      break;
    }

    default:
      RTC_DCHECK_NOTREACHED();
      break;
  }
}

void Conductor::OnSuccess(webrtc::SessionDescriptionInterface* desc) {
  peer_connection_->SetLocalDescription(
      DummySetSessionDescriptionObserver::Create().get(), desc);

  std::string sdp;
  desc->ToString(&sdp);

  // For loopback test. To save some connecting delay.
  if (loopback_) {
    // Replace message type from "offer" to "answer"
    std::unique_ptr<webrtc::SessionDescriptionInterface> session_description =
        webrtc::CreateSessionDescription(webrtc::SdpType::kAnswer, sdp);
    peer_connection_->SetRemoteDescription(
        DummySetSessionDescriptionObserver::Create().get(),
        session_description.release());
    return;
  }

  Json::Value jmessage;
  jmessage[kSessionDescriptionTypeName] =
      webrtc::SdpTypeToString(desc->GetType());
  jmessage[kSessionDescriptionSdpName] = sdp;

  Json::StreamWriterBuilder factory;
  SendMessage(Json::writeString(factory, jmessage));
}

void Conductor::OnFailure(webrtc::RTCError error) {
  RTC_ERROR << ToString(error.type()) << ": " << error.message();
}

void Conductor::SendMessage(const std::string& json_object) {
  std::string* msg = new std::string(json_object);
  OperationCallback(SEND_MESSAGE_TO_PEER, msg);
}
