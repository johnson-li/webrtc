#include "examples/peerconnection_headless/simulation/sender.h"

#include "api/rtp_transceiver_interface.h"
#include "api/peer_connection_interface.h"
#include "rtc_base/strings/json.h"
#include "absl/strings/string_view.h"
#include "rtc_base/string_encode.h"

Sender::Sender(rtc::Thread *thread, std::string path, uint32_t width, uint32_t fps)
    : SenderReceiverBase(thread), path_(path), width_(width), fps_(fps) { }

void Sender::add_tracks() {
  rtc::scoped_refptr<FrameGeneratorTrackSource> video_device =
      FrameGeneratorTrackSource::Create(width_, fps_, path_);
  rtc::scoped_refptr<webrtc::VideoTrackInterface> video_track_(
      peer_connection_factory_->CreateVideoTrack("video_track",
                                                  video_device.get()));
  webrtc::RtpTransceiverInit init;
  peer_connection_->AddTransceiver(video_track_, init);
  auto result_or_error =
      peer_connection_->AddTrack(video_track_, {"stream_id"});
}

void Sender::connect_receiver() {
  init_peerconnection();
  auto options = webrtc::PeerConnectionInterface::RTCOfferAnswerOptions();
  peer_connection_->CreateOffer(this, options);
}

void Sender::OnSuccess(webrtc::SessionDescriptionInterface* desc) {
  peer_connection_->SetLocalDescription(
      DummySetSessionDescriptionObserver::Create().get(), desc);
  auto receiver = remote_peer_;
  std::string sdp;
  desc->ToString(&sdp);
  Json::Value jmessage;
  jmessage[kSessionDescriptionTypeName] =
      webrtc::SdpTypeToString(desc->GetType());
  jmessage[kSessionDescriptionSdpName] = sdp;
  main_thread_->PostTask([receiver, jmessage] {
    Json::StreamWriterBuilder factory;
    auto json = Json::writeString(factory, jmessage);
    receiver->OnMessage(json);
  });
}

void Sender::OnMessage(std::string &msg) {
  RTC_TS << "Receive SDP answer from receiver: " << msg;
  Json::CharReaderBuilder factory;
  std::unique_ptr<Json::CharReader> reader = absl::WrapUnique(factory.newCharReader());
  Json::Value jmessage;
  reader->parse(msg.data(), msg.data() + msg.length(), &jmessage, nullptr);
  std::string type_str;
  std::string json_object;
  rtc::GetStringFromJsonObject(jmessage, kSessionDescriptionTypeName, &type_str);
  if (!type_str.empty()) {
    // SDP offer
    absl::optional<webrtc::SdpType> type_maybe = webrtc::SdpTypeFromString(type_str);
    webrtc::SdpType type = *type_maybe;
    std::string sdp;
    rtc::GetStringFromJsonObject(jmessage, kSessionDescriptionSdpName, &sdp);
    webrtc::SdpParseError error;
    std::unique_ptr<webrtc::SessionDescriptionInterface> session_description =
        webrtc::CreateSessionDescription(type, sdp, &error);
    peer_connection_->SetRemoteDescription(
        DummySetSessionDescriptionObserver::Create().get(), 
        session_description.release());
  }
  else {
    // ICE candidate
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
    peer_connection_->AddIceCandidate(candidate.get());
  }
}