#include "examples/peerconnection_headless/simulation/receiver.h"
#include "api/peer_connection_interface.h"
#include "api/jsep_session_description.h"
#include "rtc_base/strings/json.h"
#include "absl/strings/string_view.h"
#include "rtc_base/string_encode.h"

Receiver::Receiver(rtc::Thread *main_thread): SenderReceiverBase(main_thread) {} 

void Receiver::OnMessage(std::string &msg) {
  RTC_INFO << "Receive SDP offer from receiver.";
  init_peerconnection();
  Json::CharReaderBuilder factory;
  std::unique_ptr<Json::CharReader> reader = absl::WrapUnique(factory.newCharReader());
  Json::Value jmessage;
  reader->parse(msg.data(), msg.data() + msg.length(), &jmessage, nullptr);
  std::string type_str;
  std::string json_object;
  rtc::GetStringFromJsonObject(jmessage, kSessionDescriptionTypeName, &type_str);
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
};

void Receiver::OnSuccess(webrtc::SessionDescriptionInterface* desc) {
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