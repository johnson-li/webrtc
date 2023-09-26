#include "examples/peerconnection_headless/simulation/receiver.h"
#include "api/peer_connection_interface.h"
#include "api/jsep_session_description.h"
#include "rtc_base/strings/json.h"
#include "absl/strings/string_view.h"
#include "rtc_base/string_encode.h"

Receiver::Receiver(rtc::Thread *main_thread): SenderReceiverBase(main_thread) {} 

void Receiver::OnMessage(std::string &msg) {
  if (!peer_connection_.get()) {
    init_peerconnection();
  }
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
    auto options = webrtc::PeerConnectionInterface::RTCOfferAnswerOptions();
    peer_connection_->CreateAnswer(this, options);
  } else {
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
};

void Receiver::OnSuccess(webrtc::SessionDescriptionInterface* desc) {
  peer_connection_->SetLocalDescription(
      DummySetSessionDescriptionObserver::Create().get(), desc);
  auto sender = remote_peer_;
  std::string sdp;
  desc->ToString(&sdp);
  Json::Value jmessage;
  jmessage[kSessionDescriptionTypeName] =
      webrtc::SdpTypeToString(desc->GetType());
  jmessage[kSessionDescriptionSdpName] = sdp;
  main_thread_->PostTask([sender, jmessage] {
    Json::StreamWriterBuilder factory;
    auto json = Json::writeString(factory, jmessage);
    sender->OnMessage(json);
  });
}