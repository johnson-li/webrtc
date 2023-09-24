#ifndef EXAMPLES_PEERCONNECTION_SIMULATION_BASE_H_
#define EXAMPLES_PEERCONNECTION_SIMULATION_BASE_H_

#include "api/peer_connection_interface.h"
#include "api/jsep.h"
#include "api/create_peerconnection_factory.h"
#include "api/video_codecs/builtin_video_decoder_factory.h"
#include "api/video_codecs/builtin_video_encoder_factory.h"
#include "api/audio_codecs/builtin_audio_decoder_factory.h"
#include "api/audio_codecs/builtin_audio_encoder_factory.h"

const char kSessionDescriptionTypeName[] = "type";
const char kSessionDescriptionSdpName[] = "sdp";

class SdpTransmissionObserver {
  public: 
    virtual ~SdpTransmissionObserver() = default;
    virtual void OnMessage(std::string &msg) = 0;
};

class DummySetSessionDescriptionObserver
    : public webrtc::SetSessionDescriptionObserver {
 public:
  static rtc::scoped_refptr<DummySetSessionDescriptionObserver> Create() {
    return rtc::make_ref_counted<DummySetSessionDescriptionObserver>();
  }
  virtual void OnSuccess() {  }
  virtual void OnFailure(webrtc::RTCError error) {
  }
};

class SenderReceiverBase : public webrtc::PeerConnectionObserver,
                           public webrtc::CreateSessionDescriptionObserver {

 public:
  SenderReceiverBase(rtc::Thread *thread) { main_thread_.reset(thread); }
  ~SenderReceiverBase() { }

  void create_peerconnection() {
    webrtc::PeerConnectionInterface::RTCConfiguration config;
    config.set_video_rtcp_report_interval_ms(100);
    webrtc::PeerConnectionInterface::IceServer server;
    server.uri = "stun:stun.l.google.com:19302";
    config.servers.push_back(server);
    webrtc::PeerConnectionDependencies pc_dependencies(this);
    auto error_or_peer_connection =
        peer_connection_factory_->CreatePeerConnectionOrError(
            config, std::move(pc_dependencies));
    peer_connection_ = std::move(error_or_peer_connection.value());
  }

  void init_peerconnection() {
    if (!signaling_thread_.get()) {
      RTC_INFO << "Create signaling thread.";
      signaling_thread_ = rtc::Thread::CreateWithSocketServer();
      signaling_thread_->AllowInvokesToThread(main_thread_.get());
      signaling_thread_->Start();
    }
    peer_connection_factory_ = webrtc::CreatePeerConnectionFactory(
        nullptr /* network_thread */, nullptr /* worker_thread */,
        signaling_thread_.get(), nullptr /* default_adm */,
        webrtc::CreateBuiltinAudioEncoderFactory(),
        webrtc::CreateBuiltinAudioDecoderFactory(),
        webrtc::CreateBuiltinVideoEncoderFactory(),
        webrtc::CreateBuiltinVideoDecoderFactory(), nullptr /* audio_mixer */,
        nullptr /* audio_processing */);
    create_peerconnection();
    add_tracks();
  }

  void SetRemotePeer(SdpTransmissionObserver* remote_peer) {
    remote_peer_ = remote_peer;
  }

  // Implement the CreateSessionDescriptionObserver interface.
  void OnSuccess(webrtc::SessionDescriptionInterface* desc) { }
  void OnFailure(webrtc::RTCError error) { }

  // Implement the PeerConnectionObserver interface.
  virtual void add_tracks() {}
  void OnSignalingChange(webrtc::PeerConnectionInterface::SignalingState new_state) { }
  void OnAddStream(rtc::scoped_refptr<webrtc::MediaStreamInterface> stream) {}
  void OnRemoveStream(rtc::scoped_refptr<webrtc::MediaStreamInterface> stream) { }
  void OnDataChannel(rtc::scoped_refptr<webrtc::DataChannelInterface> data_channel) { }
  void OnRenegotiationNeeded() { }
  void OnNegotiationNeededEvent(uint32_t event_id) {}
  void OnIceConnectionChange(webrtc::PeerConnectionInterface::IceConnectionState new_state) {}
  void OnStandardizedIceConnectionChange(webrtc::PeerConnectionInterface::IceConnectionState new_state) {}
  void OnConnectionChange(webrtc::PeerConnectionInterface::PeerConnectionState new_state) {}
  void OnIceGatheringChange(webrtc::PeerConnectionInterface::IceGatheringState new_state) { }
  void OnIceCandidate(const webrtc::IceCandidateInterface* candidate) { }
  void OnIceCandidateError(const std::string& address, int port, const std::string& url,
                           int error_code, const std::string& error_text) { }
  void OnIceCandidatesRemoved(const std::vector<cricket::Candidate>& candidates) {}
  void OnIceConnectionReceivingChange(bool receiving) {}
  void OnIceSelectedCandidatePairChanged(const cricket::CandidatePairChangeEvent& event) {}
  void OnAddTrack(rtc::scoped_refptr<webrtc::RtpReceiverInterface> receiver,
                  const std::vector<rtc::scoped_refptr<webrtc::MediaStreamInterface>>& streams) {}
  void OnTrack(rtc::scoped_refptr<webrtc::RtpTransceiverInterface> transceiver) {}
  void OnRemoveTrack(rtc::scoped_refptr<webrtc::RtpReceiverInterface> receiver) {}
  void OnInterestingUsage(int usage_pattern) {}

 protected:
  rtc::scoped_refptr<webrtc::PeerConnectionInterface> peer_connection_;
  rtc::scoped_refptr<webrtc::PeerConnectionFactoryInterface>
      peer_connection_factory_;
  std::unique_ptr<rtc::Thread> signaling_thread_;
  std::unique_ptr<rtc::Thread> main_thread_;
  SdpTransmissionObserver* remote_peer_;
};

#endif  // EXAMPLES_PEERCONNECTION_SIMULATION_BASE_H_
