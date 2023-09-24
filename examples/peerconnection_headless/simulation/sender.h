#ifndef EXAMPLES_PEERCONNECTION_SIMULATION_SENDER_H_
#define EXAMPLES_PEERCONNECTION_SIMULATION_SENDER_H_

#include "examples/peerconnection_headless/simulation/base.h"
#include "examples/peerconnection_headless/simulation/source.h"
#include "api/jsep.h"

class Sender : public SenderReceiverBase, 
               public SdpTransmissionObserver {
 public:
  Sender(rtc::Thread *thread, std::string path, uint32_t width, uint32_t fps);
  void add_tracks() override;
  void connect_receiver();
  void OnSuccess(webrtc::SessionDescriptionInterface* desc) override;
  void OnMessage(std::string &msg) override;

 private:
  std::string path_;
  uint32_t width_;
  uint32_t fps_;
};

#endif  // EXAMPLES_PEERCONNECTION_SIMULATION_SENDER_H_