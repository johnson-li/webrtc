/*
 *  Copyright 2012 The WebRTC Project Authors. All rights reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#ifndef EXAMPLES_PEERCONNECTION_CLIENT_CONDUCTOR_H_
#define EXAMPLES_PEERCONNECTION_CLIENT_CONDUCTOR_H_

#include <deque>
#include <map>
#include <memory>
#include <string>
#include <vector>
#include <chrono>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>

#include "api/media_stream_interface.h"
#include "api/peer_connection_interface.h"
#include "examples/peerconnection_headless/client/peer_connection_client.h"
#include "base/debug/stack_trace.h"
#include "rtc_base/logging.h"
#include "third_party/libyuv/include/libyuv/convert_from.h"

namespace webrtc {
class VideoCaptureModule;
}  // namespace webrtc

namespace cricket {
class VideoRenderer;
}  // namespace cricket

#define BUFFER_SIZE 100 * 1024 * 1024
#define CONTENT_SIZE BUFFER_SIZE - 2048
struct shared_frames {
  uint32_t size;
  uint32_t offset;
  struct {
    uint32_t offset;
    uint32_t length;
    uint32_t timestamp;
    uint8_t finished;
  } indexes[128];
  uint8_t padding[376];
  uint8_t content[CONTENT_SIZE];
};

class VideoRenderer : public rtc::VideoSinkInterface<webrtc::VideoFrame> {
 public:
  VideoRenderer(std::string name, webrtc::VideoTrackInterface* track_to_render)
      : name_(name), width_(0), height_(0), shared_frames_(nullptr), rendered_track_(track_to_render)  {
    rendered_track_->AddOrUpdateSink(this, rtc::VideoSinkWants());
    initSharedMemory();
  }

  ~VideoRenderer() {
    rendered_track_->RemoveSink(this);
  }

  /**
   * Layout of the shared index memory
   *
   *  0                   1                   2                   3
   *  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 
   * +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   * |   S   |   OO  |   O   |   L   |   T   |F|      ...            |
   * +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   * S (4 bytes) = number of the indexes
   * OO (4 bytes) = offset (in bytes) in the data memory of the next frame
   * O (4 bytes) = offset (in bytes) in the data memory of the corresponding frame
   * L (4 bytes) = length (in bytes) in the data memory of the corresponding frame
   * T (4 bytes) = timestamp (in milliseconds) of the corresponding frame
   * F (1 bytes) = indicating if writting to the data memory of the corresponding frame is finished 
   * *Capacity = 128 indexes
   * *Size = 4 + 4 + (4 + 4 + 4 + 1) * 128 = 1672 bytes
   * *Wrapped Size = 2048 bytes
   * *Padding = 2048 - 1672 = 376 bytes 
   *
   * Layout of the shared data memory
   * *Size = 10 * 1024 * 1024 - 2048 = 10483712 bytes 
   *
   * *Total Size = 10 MB
   */
  void initSharedMemory() {
    int fd_shm;
    if ((fd_shm = shm_open("/webrtc_frames", O_RDWR|O_CREAT, 0660)) == -1) {
      perror("shm_open"); 
    }
    if (ftruncate(fd_shm, sizeof(struct shared_frames)) == -1) {
      perror("ftruncate"); 
    }
    if ((shared_frames_ = (struct shared_frames*) mmap(NULL, sizeof(struct shared_frames), PROT_READ | PROT_WRITE, MAP_SHARED, fd_shm, 0)) == MAP_FAILED) {
      perror ("mmap");
    } 
    shared_frames_->size = 0;
    shared_frames_->offset = 0;
    shared_frames_->indexes[0].finished = -1;
  }

  void OnFrame(const webrtc::VideoFrame& frame) {
    auto buffer = frame.video_frame_buffer();
    rtc::scoped_refptr<webrtc::I420BufferInterface> buf(buffer->ToI420());
    SetSize(buf->width(), buf->height());

    int frame_size = buf->width() * buf->height() * 4;;
    if (frame_size > (CONTENT_SIZE) / 4) {
      RTC_LOG(LERROR) << "frame_size: " << frame_size << " is too large for content_size: " << CONTENT_SIZE;   
    }

    int index = shared_frames_->size++;
    shared_frames_->indexes[shared_frames_->size].finished = -1;
    uint32_t offset = shared_frames_->offset;
    if (offset + frame_size > CONTENT_SIZE) {
        offset = 0;
    }
    shared_frames_->offset += frame_size;
    shared_frames_->indexes[index].offset = offset; 
    shared_frames_->indexes[index].length = frame_size; 
    shared_frames_->indexes[index].timestamp = frame.timestamp();
    libyuv::I420ToARGB(buf->DataY(), buf->StrideY(), buf->DataU(),
            buf->StrideU(), buf->DataV(), buf->StrideV(),
            shared_frames_->content + offset, width_ * 4, buf->width(), buf->height());
    shared_frames_->indexes[index].finished = 1;
    
    RTC_LOG(INFO) << "[" << name_ << "] Received frame of size: " << 
        buf->width() << "x" << buf->height() << " at " << 
        std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count();
  }

  const uint8_t* image() const { return image_.get(); }
  int width() const { return width_; }
  int height() const { return height_; }

 protected:
  void SetSize(int width, int height) {
    if (width_ == width && height_ == height) {
      return;
    }
    width_ = width;
    height_ = height;
    image_.reset(new uint8_t[width * height * 4]);
  }
  std::unique_ptr<uint8_t[]> image_;
  std::string name_;
  int width_;
  int height_;
  struct shared_frames* shared_frames_;
  unsigned char* shared_memory_;
  rtc::scoped_refptr<webrtc::VideoTrackInterface> rendered_track_;
};

class Conductor : public webrtc::PeerConnectionObserver,
                  public webrtc::CreateSessionDescriptionObserver,
                  public PeerConnectionClientObserver {
 public:
  enum CallbackID {
    MEDIA_CHANNELS_INITIALIZED = 1,
    PEER_CONNECTION_CLOSED,
    SEND_MESSAGE_TO_PEER,
    NEW_TRACK_ADDED,
    TRACK_REMOVED,
  };

  Conductor(PeerConnectionClient* client);
  bool connection_active() const;
  void Close();

 protected:
  ~Conductor();
  bool InitializePeerConnection();
  bool ReinitializePeerConnectionForLoopback();
  bool CreatePeerConnection(bool dtls);
  void DeletePeerConnection();
  void EnsureStreamingUI();
  void AddTracks();
  void StartLocalRenderer(webrtc::VideoTrackInterface* local_video);
  void StopLocalRenderer();
  void StartRemoteRenderer(webrtc::VideoTrackInterface* remote_video);
  void StopRemoteRenderer();

  //
  // PeerConnectionObserver implementation.
  //

  void OnSignalingChange(
      webrtc::PeerConnectionInterface::SignalingState new_state) override {}
  void OnAddTrack(
      rtc::scoped_refptr<webrtc::RtpReceiverInterface> receiver,
      const std::vector<rtc::scoped_refptr<webrtc::MediaStreamInterface>>&
          streams) override;
  void OnRemoveTrack(
      rtc::scoped_refptr<webrtc::RtpReceiverInterface> receiver) override;
  void OnDataChannel(
      rtc::scoped_refptr<webrtc::DataChannelInterface> channel) override {}
  void OnRenegotiationNeeded() override {}
  void OnIceConnectionChange(
      webrtc::PeerConnectionInterface::IceConnectionState new_state) override {}
  void OnIceGatheringChange(
      webrtc::PeerConnectionInterface::IceGatheringState new_state) override {}
  void OnIceCandidate(const webrtc::IceCandidateInterface* candidate) override;
  void OnIceConnectionReceivingChange(bool receiving) override {}

  //
  // PeerConnectionClientObserver implementation.
  //

  void OnSignedIn() override;
  void OnDisconnected() override;
  void OnPeerConnected(int id, const std::string& name) override;
  void OnPeerDisconnected(int id) override;
  void OnMessageFromPeer(int peer_id, const std::string& message) override;
  void OnMessageSent(int err) override;
  void OnServerConnectionFailure() override;

  //
  // Operation.
  //
 public:
  void StartLogin(const std::string& server, int port);
  void DisconnectFromServer();
  void ConnectToPeer(int peer_id);
  void DisconnectFromCurrentPeer();
  void OperationCallback(int msg_id, void* data);
  void OnSuccess(webrtc::SessionDescriptionInterface* desc) override;
  void OnFailure(webrtc::RTCError error) override;

 protected:
  // Send a message to the remote peer.
  void SendMessage(const std::string& json_object);

  int peer_id_;
  bool loopback_;
  rtc::scoped_refptr<webrtc::PeerConnectionInterface> peer_connection_;
  rtc::scoped_refptr<webrtc::PeerConnectionFactoryInterface>
      peer_connection_factory_;
  PeerConnectionClient* client_;
  std::deque<std::string*> pending_messages_;
  std::string server_;
  std::unique_ptr<VideoRenderer> local_renderer_;
  std::unique_ptr<VideoRenderer> remote_renderer_;
};

#endif  // EXAMPLES_PEERCONNECTION_CLIENT_CONDUCTOR_H_
