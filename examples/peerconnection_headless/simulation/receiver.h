#ifndef EXAMPLES_PEERCONNECTION_HEADLESS_SIMULATION_RECEIVER_H_
#define EXAMPLES_PEERCONNECTION_HEADLESS_SIMULATION_RECEIVER_H_

#include "examples/peerconnection_headless/simulation/base.h"
#include "api/jsep.h"

class Receiver : public SenderReceiverBase, 
                 public SdpTransmissionObserver {
 public:
  Receiver(rtc::Thread *main_thread);
  void OnSuccess(webrtc::SessionDescriptionInterface* desc) override;
  void OnMessage(std::string &msg) override;
};

#endif  // EXAMPLES_PEERCONNECTION_HEADLESS_SIMULATION_RECEIVER_H_
