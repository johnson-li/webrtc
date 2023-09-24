#ifndef EXAMPLES_PEERCONNECTION_SIMULATION_SOURCE_H_
#define EXAMPLES_PEERCONNECTION_SIMULATION_SOURCE_H_

#include "pc/video_track_source.h"
#include "api/test/create_frame_generator.h"
#include "api/task_queue/default_task_queue_factory.h"
#include "test/frame_generator_capturer.h"

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
#endif  // EXAMPLES_PEERCONNECTION_SIMULATION_SOURCE_H_