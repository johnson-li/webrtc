#include "h264_nvenc_encoder.h"

#include <limits>
#include <string>
#include <string.h>
#include <fcntl.h>
#include <sys/mman.h>

#include "third_party/openh264/src/codec/api/svc/codec_api.h"
#include "third_party/openh264/src/codec/api/svc/codec_app_def.h"
#include "third_party/openh264/src/codec/api/svc/codec_def.h"
#include "third_party/openh264/src/codec/api/svc/codec_ver.h"
#include "absl/strings/match.h"
#include "common_video/h264/h264_common.h"
#include "common_video/libyuv/include/webrtc_libyuv.h"
#include "modules/video_coding/utility/simulcast_rate_allocator.h"
#include "modules/video_coding/utility/simulcast_utility.h"
#include "rtc_base/checks.h"
#include "rtc_base/logging.h"
#include "rtc_base/time_utils.h"
#include "system_wrappers/include/clock.h"
#include "system_wrappers/include/metrics.h"
#include "third_party/libyuv/include/libyuv/convert.h"
#include "third_party/libyuv/include/libyuv/scale.h"

namespace webrtc {

namespace {

// QP scaling thresholds.
static const int kLowH264QpThreshold = 24;
static const int kHighH264QpThreshold = 37;

// Used by histograms. Values of entries should not be changed.
enum NvVideoEncoderEvent
{
	kH264EncoderEventInit = 0,
	kH264EncoderEventError = 1,
	kH264EncoderEventMax = 16,
};

}  // namespace

NvEncoder::NvEncoder(const cricket::VideoCodec& codec)
    : packetization_mode_(H264PacketizationMode::SingleNalUnit),
      max_payload_size_(0),
      number_of_cores_(0),
      encoded_image_callback_(nullptr),
      has_reported_init_(false),
      has_reported_error_(false) {
  RTC_CHECK(absl::EqualsIgnoreCase(codec.name, cricket::kH264CodecName));
  RTC_INFO << "Creating H264 codec: NvEncoder";
  std::string packetization_mode_string;
  if (codec.GetParam(cricket::kH264FmtpPacketizationMode,
                     &packetization_mode_string) &&
      packetization_mode_string == "1") {
    packetization_mode_ = H264PacketizationMode::NonInterleaved;
  }
  downscaled_buffers_.reserve(kMaxSimulcastStreams - 1);
  encoded_images_.reserve(kMaxSimulcastStreams);
  contexts_.reserve(kMaxSimulcastStreams);
  encoders_.reserve(kMaxSimulcastStreams);
  configurations_.reserve(kMaxSimulcastStreams);
  tl0sync_limit_.reserve(kMaxSimulcastStreams);
  initialize_params_.reserve(kMaxSimulcastStreams);

  if (SHM_STR) {
	int shm_fd = shm_open(SHM_STR, O_RDONLY, 0666);
	if (shm_fd == -1) {
		RTC_INFO << "shm_open failed";
	} else {
		struct stat shmbuf;
		if (fstat(shm_fd, &shmbuf) == -1) {
		RTC_INFO << "fstat failed";
		} else {
		auto size = shmbuf.st_size;
		shared_mem_ = static_cast<uint32_t*>(mmap(nullptr, size, PROT_READ, MAP_SHARED, shm_fd, 0));
		if (shared_mem_ == MAP_FAILED) {
			RTC_INFO << "mmap failed";
		}       
		}
		close(shm_fd);
	}
  }
}

NvEncoder::~NvEncoder() 
{
	Release();
}

int32_t NvEncoder::InitEncode(const VideoCodec* inst,
                                    const VideoEncoder::Settings& settings) {
	ReportInit();
	if (!inst || inst->codecType != kVideoCodecH264) {
		ReportError();
		return WEBRTC_VIDEO_CODEC_ERR_PARAMETER;
	}
	if (inst->maxFramerate == 0) {
		ReportError();
		return WEBRTC_VIDEO_CODEC_ERR_PARAMETER;
	}
	if (inst->width < 1 || inst->height < 1) {
		ReportError();
		return WEBRTC_VIDEO_CODEC_ERR_PARAMETER;
	}

	int32_t release_ret = Release();
	if (release_ret != WEBRTC_VIDEO_CODEC_OK) {
		ReportError();
		return release_ret;
	}

	int number_of_streams = SimulcastUtility::NumberOfSimulcastStreams(*inst);
	bool doing_simulcast = (number_of_streams > 1);

	if (doing_simulcast &&
		!SimulcastUtility::ValidSimulcastParameters(*inst, number_of_streams)) {
		return WEBRTC_VIDEO_CODEC_ERR_SIMULCAST_PARAMETERS_NOT_SUPPORTED;
	}
	downscaled_buffers_.resize(number_of_streams - 1);
	encoded_images_.resize(number_of_streams);
	contexts_.resize(number_of_streams);
	encoders_.resize(number_of_streams);
	pictures_.resize(number_of_streams);
	configurations_.resize(number_of_streams);
	tl0sync_limit_.resize(number_of_streams);
	initialize_params_.resize(number_of_streams);

	number_of_cores_ = settings.number_of_cores;
	max_payload_size_ = settings.max_payload_size;
	codec_ = *inst;

	// Code expects simulcastStream resolutions to be correct, make sure they are
	// filled even when there are no simulcast layers.
	if (codec_.numberOfSimulcastStreams == 0) {
		codec_.simulcastStream[0].width = codec_.width;
		codec_.simulcastStream[0].height = codec_.height;
	}

	for (int i = 0, idx = number_of_streams - 1; i < number_of_streams;	++i, --idx) {
        CUcontext cuContext = NULL;
		CUdevice cuDevice = 0;
		for (int gpu_index = 1; gpu_index >= 0; gpu_index--) {
			auto result = cuDeviceGet(&cuDevice, gpu_index);
			if (result == CUDA_SUCCESS) {
				result = cuCtxCreate(&cuContext, 0, cuDevice);
				if (result == CUDA_SUCCESS) {
					RTC_INFO << "Created CUDA context for GPU " << gpu_index;
					break;
				}
			}
		}
		if (cuContext == NULL) {
			RTC_INFO << "Failed to create CUDA context.";
			ReportError();
			return WEBRTC_VIDEO_CODEC_ERROR;
		}
    	NvEncoderCuda* encoder = new NvEncoderCuda(cuContext, codec_.simulcastStream[idx].width, 
							  					  codec_.simulcastStream[idx].height, 
												  NV_ENC_BUFFER_FORMAT_IYUV);
		RTC_DCHECK(encoder);

    	// Store h264 encoder.
    	encoders_[i] = encoder;
		contexts_[i] = cuContext;

		// Set internal settings from codec_settings
		configurations_[i].simulcast_idx = idx;
		configurations_[i].sending = false;
		configurations_[i].width = codec_.simulcastStream[idx].width;
		configurations_[i].height = codec_.simulcastStream[idx].height;
		configurations_[i].max_frame_rate = static_cast<float>(codec_.maxFramerate);
		configurations_[i].frame_dropping_on = codec_.GetFrameDropEnabled();
		configurations_[i].key_frame_interval = codec_.H264()->keyFrameInterval;
		configurations_[i].num_temporal_layers =
			std::max(codec_.H264()->numberOfTemporalLayers,
					codec_.simulcastStream[idx].numberOfTemporalLayers);

		// Create downscaled image buffers.
		if (i > 0) {
		downscaled_buffers_[i - 1] = I420Buffer::Create(
			configurations_[i].width, configurations_[i].height,
			configurations_[i].width, configurations_[i].width / 2,
			configurations_[i].width / 2);
		}

		// Codec_settings uses kbits/second; encoder uses bits/second.
		configurations_[i].max_bps = codec_.maxBitrate * 1000;
		configurations_[i].target_bps = codec_.startBitrate * 1000;

		NV_ENC_INITIALIZE_PARAMS initializeParams = { NV_ENC_INITIALIZE_PARAMS_VER };
		NV_ENC_CONFIG encodeConfig = { NV_ENC_CONFIG_VER };
		initializeParams.encodeConfig = &encodeConfig;
		encoder->CreateDefaultEncoderParams(&initializeParams, NV_ENC_CODEC_H264_GUID, NV_ENC_PRESET_P4_GUID, NV_ENC_TUNING_INFO_LOW_LATENCY);
		NvEncoderInitParam encodeCLIOptions;
		encodeCLIOptions.SetInitParams(&initializeParams, NV_ENC_BUFFER_FORMAT_IYUV);
		initializeParams.enablePTD = 1;  // Enable PTD so that we can force the codec to generate an IDR frame
		initializeParams.enableEncodeAsync = 0;  // Force synchronised encoding
		initializeParams.encodeConfig->frameIntervalP = 1;
		initializeParams.encodeConfig->rcParams.enableLookahead = 0;
		initializeParams.encodeConfig->profileGUID = NV_ENC_H264_PROFILE_BASELINE_GUID;
		switch (packetization_mode_) {
    		case H264PacketizationMode::SingleNalUnit:
				initializeParams.encodeConfig->encodeCodecConfig.h264Config.sliceMode = 1;
				initializeParams.encodeConfig->encodeCodecConfig.h264Config.sliceModeData = max_payload_size_;
				RTC_TS << "Encoder is configured with NALU constraint: "
								<< max_payload_size_ << " bytes";
				break;
    		case H264PacketizationMode::NonInterleaved:
				initializeParams.encodeConfig->encodeCodecConfig.h264Config.sliceMode = 3;
				initializeParams.encodeConfig->encodeCodecConfig.h264Config.sliceModeData = 1;
				RTC_TS << "Encoder is configured with slice number: 1";
				break;
		}
		encoder->CreateEncoder(&initializeParams);

		// Initialize encoded image. Default buffer size: size of unencoded data.
		const size_t new_capacity =
			CalcBufferSize(VideoType::kI420, codec_.simulcastStream[idx].width,
						codec_.simulcastStream[idx].height);
		encoded_images_[i].SetEncodedData(EncodedImageBuffer::Create(new_capacity));
		encoded_images_[i]._encodedWidth = codec_.simulcastStream[idx].width;
		encoded_images_[i]._encodedHeight = codec_.simulcastStream[idx].height;
		encoded_images_[i].set_size(0);
	}

	SimulcastRateAllocator init_allocator(codec_);
	VideoBitrateAllocation allocation =
		init_allocator.Allocate(VideoBitrateAllocationParameters(
			DataRate::KilobitsPerSec(codec_.startBitrate), codec_.maxFramerate));
	SetRates(RateControlParameters(allocation, codec_.maxFramerate));
	return WEBRTC_VIDEO_CODEC_OK;
}

int32_t NvEncoder::Release() 
{
	while (!encoders_.empty()) {		
		NvEncoderCuda* nv_encoder = encoders_.back();
		if (nv_encoder) {
			nv_encoder->DestroyEncoder();
			delete nv_encoder;
		}
		encoders_.pop_back();
	}
  	downscaled_buffers_.clear();
	configurations_.clear();
	encoded_images_.clear();
	return WEBRTC_VIDEO_CODEC_OK;
}

int32_t NvEncoder::RegisterEncodeCompleteCallback(EncodedImageCallback* callback) 
{
	encoded_image_callback_ = callback;
	return WEBRTC_VIDEO_CODEC_OK;
}

void NvEncoder::SetRates(const RateControlParameters& parameters) {
	if (encoders_.empty()) {
		RTC_LOG(LS_WARNING) << "SetRates() while uninitialized.";
		return;
	}

	if (parameters.framerate_fps < 1.0) {
		RTC_LOG(LS_WARNING) << "Invalid frame rate: " << parameters.framerate_fps;
		return;
	}

	if (parameters.bitrate.get_sum_bps() == 0) {
		// Encoder paused, turn off all encoding.
		for (size_t i = 0; i < configurations_.size(); ++i) {
		configurations_[i].SetStreamState(false);
		}
		return;
	}

  	codec_.maxFramerate = static_cast<uint32_t>(parameters.framerate_fps);

  	size_t stream_idx = encoders_.size() - 1;
  	for (size_t i = 0; i < encoders_.size(); ++i, --stream_idx) {
		configurations_[i].target_bps =
			parameters.bitrate.GetSpatialLayerSum(stream_idx);
		configurations_[i].max_frame_rate = parameters.framerate_fps;

		if (configurations_[i].target_bps) {
			configurations_[i].SetStreamState(true);

			NV_ENC_INITIALIZE_PARAMS initializeParams = { NV_ENC_INITIALIZE_PARAMS_VER };
			NV_ENC_CONFIG encodeConfig = { NV_ENC_CONFIG_VER };
			initializeParams.encodeConfig = &encodeConfig;
			encoders_[i]->CreateDefaultEncoderParams(&initializeParams, NV_ENC_CODEC_H264_GUID, NV_ENC_PRESET_P4_GUID, NV_ENC_TUNING_INFO_LOW_LATENCY);
			NvEncoderInitParam encodeCLIOptions;
			encodeCLIOptions.SetInitParams(&initializeParams, NV_ENC_BUFFER_FORMAT_IYUV);
			NV_ENC_RECONFIGURE_PARAMS reconfigureParams = {NV_ENC_RECONFIGURE_PARAMS_VER, initializeParams};
			reconfigureParams.reInitEncodeParams.encodeConfig->rcParams.averageBitRate = configurations_[i].target_bps;
			reconfigureParams.reInitEncodeParams.encodeConfig->rcParams.maxBitRate = configurations_[i].max_bps;
			reconfigureParams.reInitEncodeParams.encodeConfig->rcParams.enableLookahead = 0;
			reconfigureParams.reInitEncodeParams.encodeConfig->rcParams.lookaheadDepth = 0;
			reconfigureParams.reInitEncodeParams.encodeConfig->frameIntervalP = 1;
			reconfigureParams.reInitEncodeParams.encodeConfig->profileGUID = NV_ENC_H264_PROFILE_BASELINE_GUID;
			reconfigureParams.reInitEncodeParams.frameRateNum = int(configurations_[i].max_frame_rate);
			reconfigureParams.reInitEncodeParams.frameRateDen = 1;
			reconfigureParams.reInitEncodeParams.enableEncodeAsync = 0;
			switch (packetization_mode_) {
				case H264PacketizationMode::SingleNalUnit:
					reconfigureParams.reInitEncodeParams.encodeConfig->encodeCodecConfig.h264Config.sliceMode = 1;
					reconfigureParams.reInitEncodeParams.encodeConfig->encodeCodecConfig.h264Config.sliceModeData = max_payload_size_;
					RTC_TS << "Encoder is configured with NALU constraint: "
									<< max_payload_size_ << " bytes";
					break;
				case H264PacketizationMode::NonInterleaved:
					reconfigureParams.reInitEncodeParams.encodeConfig->encodeCodecConfig.h264Config.sliceMode = 3;
					reconfigureParams.reInitEncodeParams.encodeConfig->encodeCodecConfig.h264Config.sliceModeData = 1;
					RTC_TS << "Encoder is configured with slice number: 1";
					break;
			}
			reconfigureParams.resetEncoder = configurations_[i].key_frame_request ? 1 : 0;
			reconfigureParams.forceIDR = configurations_[i].key_frame_request ? 1 : 0;

			RTC_TS << "SetRates" 
					<< ", stream id: " << stream_idx
					<< ", bitrate: " << reconfigureParams.reInitEncodeParams.encodeConfig->rcParams.averageBitRate / 1024 << " kbps"
					<< ", max bitrate: " << reconfigureParams.reInitEncodeParams.encodeConfig->rcParams.maxBitRate / 1024 << " kbps"
					<< ", framerate: " << reconfigureParams.reInitEncodeParams.frameRateNum;
			encoders_[i]->Reconfigure(&reconfigureParams);
		} else {
      		configurations_[i].SetStreamState(false);
		}
	}
}

void NvEncoder::MaybeSetRates() {
	if (shared_mem_) {
		auto bitrate = shared_mem_[0] * 1024;
		auto fps = shared_mem_[2];
        if (bitrate > 0 || fps > 0) {
			RTC_TS << "SetRates from shared memory"
				<< ", bitrate: " << bitrate / 1024 << " kbps"
				<< ", framerate: " << fps;
			if (fps == 0) {
				fps = configurations_[0].max_frame_rate;
			}
			if (bitrate == 0) {
				bitrate = configurations_[0].target_bps;
			}
			RateControlParameters params;
			params.target_bitrate.SetBitrate(0, 0, bitrate);
			params.bitrate.SetBitrate(0, 0, bitrate);
			params.framerate_fps = fps;
			params.bandwidth_allocation = DataRate::BitsPerSec(bitrate);
			SetRates(params);
		}
	}
}

int32_t NvEncoder::Encode(const VideoFrame& input_frame,
						  const std::vector<VideoFrameType>* frame_types) {
	if (encoders_.empty()) {
		ReportError();
		return WEBRTC_VIDEO_CODEC_UNINITIALIZED;
	}
	if (!encoded_image_callback_) {
		RTC_LOG(LS_WARNING)
			<< "InitEncode() has been called, but a callback function "
			<< "has not been set with RegisterEncodeCompleteCallback()";
		ReportError();
		return WEBRTC_VIDEO_CODEC_UNINITIALIZED;
	}

	rtc::scoped_refptr<I420BufferInterface> frame_buffer =
		input_frame.video_frame_buffer()->ToI420();

	if (!frame_buffer) {
		RTC_LOG(LS_ERROR) << "Failed to convert "
						<< VideoFrameBufferTypeToString(
								input_frame.video_frame_buffer()->type())
						<< " image to I420. Can't encode frame.";
		return WEBRTC_VIDEO_CODEC_ENCODER_FAILURE;
	}
	RTC_CHECK(frame_buffer->type() == VideoFrameBuffer::Type::kI420 ||
				frame_buffer->type() == VideoFrameBuffer::Type::kI420A);

	MaybeSetRates();

	bool send_key_frame = false;
	for (size_t i = 0; i < configurations_.size(); ++i) {
		if (configurations_[i].key_frame_request && configurations_[i].sending) {
			RTC_TS << "Send key frame because of stream initiation";
			send_key_frame = true;
			break;
		}
	}

	if (!send_key_frame && frame_types) {
		for (size_t i = 0; i < configurations_.size(); ++i) {
			const size_t simulcast_idx =
				static_cast<size_t>(configurations_[i].simulcast_idx);
			if (configurations_[i].sending && simulcast_idx < frame_types->size() &&
				(*frame_types)[simulcast_idx] == VideoFrameType::kVideoFrameKey) {
				send_key_frame = true;
				RTC_TS << "Send key frame because of rtcp request";
				break;
			}
		}
	}

	RTC_DCHECK_EQ(configurations_[0].width, frame_buffer->width());
	RTC_DCHECK_EQ(configurations_[0].height, frame_buffer->height());

	// Encode image for each layer.
	for (size_t i = 0; i < encoders_.size(); ++i) {
		// EncodeFrame input.
		pictures_[i] = {0};
		pictures_[i].iPicWidth = configurations_[i].width;
		pictures_[i].iPicHeight = configurations_[i].height;
		pictures_[i].iColorFormat = EVideoFormatType::videoFormatI420;
		pictures_[i].uiTimeStamp = input_frame.ntp_time_ms();
		// Downscale images on second and ongoing layers.
		if (i == 0) {
			pictures_[i].iStride[0] = frame_buffer->StrideY();
			pictures_[i].iStride[1] = frame_buffer->StrideU();
			pictures_[i].iStride[2] = frame_buffer->StrideV();
			pictures_[i].pData[0] = const_cast<uint8_t*>(frame_buffer->DataY());
			pictures_[i].pData[1] = const_cast<uint8_t*>(frame_buffer->DataU());
			pictures_[i].pData[2] = const_cast<uint8_t*>(frame_buffer->DataV());
		} else {
			pictures_[i].iStride[0] = downscaled_buffers_[i - 1]->StrideY();
			pictures_[i].iStride[1] = downscaled_buffers_[i - 1]->StrideU();
			pictures_[i].iStride[2] = downscaled_buffers_[i - 1]->StrideV();
			pictures_[i].pData[0] =
				const_cast<uint8_t*>(downscaled_buffers_[i - 1]->DataY());
			pictures_[i].pData[1] =
				const_cast<uint8_t*>(downscaled_buffers_[i - 1]->DataU());
			pictures_[i].pData[2] =
				const_cast<uint8_t*>(downscaled_buffers_[i - 1]->DataV());
			// Scale the image down a number of times by downsampling factor.
			libyuv::I420Scale(pictures_[i - 1].pData[0], pictures_[i - 1].iStride[0],
								pictures_[i - 1].pData[1], pictures_[i - 1].iStride[1],
								pictures_[i - 1].pData[2], pictures_[i - 1].iStride[2],
								configurations_[i - 1].width,
								configurations_[i - 1].height, pictures_[i].pData[0],
								pictures_[i].iStride[0], pictures_[i].pData[1],
								pictures_[i].iStride[1], pictures_[i].pData[2],
								pictures_[i].iStride[2], configurations_[i].width,
								configurations_[i].height, libyuv::kFilterBox);
		}

		if (!configurations_[i].sending) {
			continue;
		}
		if (frame_types != nullptr) {
		// Skip frame?
			if ((*frame_types)[i] == VideoFrameType::kEmptyFrame) {
				continue;
			}
		}

		// EncodeFrame output.
		SFrameBSInfo info;
		memset(&info, 0, sizeof(SFrameBSInfo));

		// Conpact the encoded data into one single memory block.
		const NvEncInputFrame* encoderInputFrame = encoders_[i]->GetNextInputFrame();
		int sizeY = pictures_[i].iStride[0] * pictures_[i].iPicHeight;
		int sizeU = pictures_[i].iStride[1] * ((pictures_[i].iPicHeight + 1) / 2);
		int sizeV = pictures_[i].iStride[2] * ((pictures_[i].iPicHeight + 1) / 2);
		std::unique_ptr<uint8_t[]> pHostFrame(new uint8_t[sizeY + sizeU + sizeV]);
		memcpy(pHostFrame.get(), pictures_[i].pData[0], sizeY);
		memcpy(pHostFrame.get() + sizeY, pictures_[i].pData[1], sizeU);
		memcpy(pHostFrame.get() + sizeY + sizeU, pictures_[i].pData[2], sizeV);
		// Copy the input frame to GPU for encoding
		NvEncoderCuda::CopyToDeviceFrame(contexts_[i], pHostFrame.get(), 0, (CUdeviceptr)encoderInputFrame->inputPtr,
										(int)encoderInputFrame->pitch, 
										pictures_[i].iPicWidth,
										pictures_[i].iPicHeight,
										CU_MEMORYTYPE_HOST,
										encoderInputFrame->bufferFormat,
										encoderInputFrame->chromaOffsets,
										encoderInputFrame->numChromaPlanes);
		std::vector<std::vector<uint8_t>> encOutBuf;

		// Encode!
		RTC_TS << "NVENC Start encoding, frame id: " << input_frame.id() 
			<< ", shape: " << configurations_[i].width << " x " << configurations_[i].height
			<< ", bitrate: " << configurations_[i].target_bps / 1024 << " kbps"
			<< ", key frame: " << send_key_frame
			<< ", fps: " << configurations_[i].max_frame_rate;
		if (OBS_SOCKET_FD != -1) {
			rtc::ObsVideoEncoding obs{
				.ts = (uint64_t) TS(),
				.frame_id = input_frame.id(),
				.height = (uint32_t) configurations_[i].height,
				.bitrate = configurations_[i].target_bps / 1024,
				.key_frame = send_key_frame,
				.fps = (uint8_t) configurations_[i].max_frame_rate,
			};
			uint8_t* data = reinterpret_cast<uint8_t*>(&obs);
			send(OBS_SOCKET_FD, data, sizeof(obs), 0);
		}
		NV_ENC_PIC_PARAMS pPicParams = {};
		if (send_key_frame) {
			pPicParams.encodePicFlags = NV_ENC_PIC_FLAG_FORCEIDR | NV_ENC_PIC_FLAG_OUTPUT_SPSPPS;
			pPicParams.pictureType = NV_ENC_PIC_TYPE_IDR;
			configurations_[i].key_frame_request = false;
		} else {
			pPicParams.pictureType = NV_ENC_PIC_TYPE_P;
		}
		encoders_[i]->EncodeFrame(encOutBuf, &pPicParams);
		if (encOutBuf.size() > 0) {
			RTC_INFO << "Encoded size: " << encOutBuf.size() << " x " << encOutBuf[0].size();
		} else {
			RTC_INFO << "Encoded size: " << encOutBuf.size();
		}

		int required_capacity = 0;
		for (uint layer = 0; layer < encOutBuf.size(); ++layer) {
			required_capacity += encOutBuf[layer].size();
		}
		auto buffer = EncodedImageBuffer::Create(required_capacity);
  		encoded_images_[i].SetEncodedData(buffer);
  		const uint8_t start_code[4] = {0, 0, 0, 1};
		encoded_images_[i].set_size(0);
  		for (uint layer = 0; layer < encOutBuf.size(); ++layer) {
      		RTC_DCHECK_GE(encOutBuf[layer].size(), 4);
			RTC_DCHECK_EQ(encOutBuf[layer][0], start_code[0]);
			RTC_DCHECK_EQ(encOutBuf[layer][1], start_code[1]);
			RTC_DCHECK_EQ(encOutBuf[layer][2], start_code[2]);
			RTC_DCHECK_EQ(encOutBuf[layer][3], start_code[3]);
			int layer_len = encOutBuf[layer].size();
			memcpy(buffer->data() + encoded_images_[i].size(), &encOutBuf[layer][0], layer_len);
			encoded_images_[i].set_size(encoded_images_[i].size() + layer_len);
		}

		encoded_images_[i]._encodedWidth = configurations_[i].width;
		encoded_images_[i]._encodedHeight = configurations_[i].height;
		encoded_images_[i].SetTimestamp(input_frame.timestamp());
		encoded_images_[i].SetColorSpace(input_frame.color_space());
		encoded_images_[i]._frameType = VideoFrameType::kEmptyFrame;
		encoded_images_[i].SetSpatialIndex(configurations_[i].simulcast_idx);
		encoded_images_[i].frame_id = input_frame.id();

		// Encoder can skip frames to save bandwidth in which case
		// `encoded_images_[i]._length` == 0.
		if (encoded_images_[i].size() > 0) {
			// Parse QP.
			h264_bitstream_parser_.ParseBitstream(encoded_images_[i]);
			// Reset the frame type with information extracted from the stream.
			encoded_images_[i]._frameType = h264_bitstream_parser_.IsKeyFrame() ? \
				VideoFrameType::kVideoFrameKey : VideoFrameType::kVideoFrameDelta;
			encoded_images_[i].qp_ =
				h264_bitstream_parser_.GetLastSliceQp().value_or(-1);

			// Deliver encoded image.
			CodecSpecificInfo codec_specific;
			codec_specific.codecType = kVideoCodecH264;
			codec_specific.codecSpecific.H264.packetization_mode =
				packetization_mode_;
			codec_specific.codecSpecific.H264.temporal_idx = kNoTemporalIdx;
			codec_specific.codecSpecific.H264.idr_frame = h264_bitstream_parser_.IsKeyFrame();
			codec_specific.codecSpecific.H264.base_layer_sync = false;
			if (configurations_[i].num_temporal_layers > 1) {
				const uint8_t tid = info.sLayerInfo[0].uiTemporalId;
				codec_specific.codecSpecific.H264.temporal_idx = tid;
				codec_specific.codecSpecific.H264.base_layer_sync =
					tid > 0 && tid < tl0sync_limit_[i];
				if (codec_specific.codecSpecific.H264.base_layer_sync) {
					tl0sync_limit_[i] = tid;
				}
				if (tid == 0) {
					tl0sync_limit_[i] = configurations_[i].num_temporal_layers;
				}
			}
			RTC_TS << "Finish encoding, frame id: " << input_frame.id()
				<< ", frame type: " << static_cast<int>(encoded_images_[i]._frameType)
				<< ", frame shape: " << encoded_images_[i]._encodedWidth << "x" << encoded_images_[i]._encodedHeight
				<< ", frame size: " << encoded_images_[i].size()
				<< ", is key: " << int(encoded_images_[i]._frameType == VideoFrameType::kVideoFrameKey)
				<< ", qp: " << encoded_images_[i].qp_;
			if (OBS_SOCKET_FD != -1) {
				rtc::ObsVideoEncoded obs {
					.ts = (uint64_t) TS(),
					.frame_id = input_frame.id(),
					.height = (uint32_t) encoded_images_[i]._encodedHeight,
					.size = (uint32_t) encoded_images_[i].size(),
					.is_key = encoded_images_[i]._frameType == VideoFrameType::kVideoFrameKey,
					.qp = (uint16_t) encoded_images_[i].qp_,
				};
				auto data = reinterpret_cast<uint8_t*>(&obs);
				send(OBS_SOCKET_FD, data, sizeof(obs), 0);
			}
			encoded_image_callback_->OnEncodedImage(encoded_images_[i],
													&codec_specific);
    	} else {
			RTC_TS << "Finish encoding, frame id: " << input_frame.id()
				<< ", frame type: " << static_cast<int>(encoded_images_[i]._frameType)
				<< ", frame shape: " << encoded_images_[i]._encodedWidth << "x" << encoded_images_[i]._encodedHeight
				<< ", frame size: " << encoded_images_[i].size()
				<< ", is key: " << int(encoded_images_[i]._frameType == VideoFrameType::kVideoFrameKey)
				<< ", qp: " << encoded_images_[i].qp_;
			if (OBS_SOCKET_FD != -1) {
				rtc::ObsVideoEncoded obs {
					.ts = (uint64_t) TS(),
					.frame_id = input_frame.id(),
					.height = (uint32_t) encoded_images_[i]._encodedHeight,
					.size = (uint32_t) encoded_images_[i].size(),
					.is_key = encoded_images_[i]._frameType == VideoFrameType::kVideoFrameKey,
					.qp = (uint16_t) encoded_images_[i].qp_,
				};
				auto data = reinterpret_cast<uint8_t*>(&obs);
				send(OBS_SOCKET_FD, data, sizeof(obs), 0);
			}
		}

	}
  	return WEBRTC_VIDEO_CODEC_OK;
}

void NvEncoder::ReportInit() 
{
	if (has_reported_init_)
		return;
	RTC_HISTOGRAM_ENUMERATION("WebRTC.Video.NvEncoder.Event",
							kH264EncoderEventInit, kH264EncoderEventMax);
	has_reported_init_ = true;
}

void NvEncoder::ReportError() 
{
	if (has_reported_error_)
		return;
	RTC_HISTOGRAM_ENUMERATION("WebRTC.Video.NvEncoder.Event",
							kH264EncoderEventError, kH264EncoderEventMax);
	has_reported_error_ = true;
}

VideoEncoder::EncoderInfo NvEncoder::GetEncoderInfo() const 
{
	EncoderInfo info;
	info.supports_native_handle = false;
	info.implementation_name = "NvEnc";
	info.scaling_settings =
		VideoEncoder::ScalingSettings(kLowH264QpThreshold, kHighH264QpThreshold);
	info.is_hardware_accelerated = true;
	info.supports_simulcast = false;
	info.preferred_pixel_formats = {VideoFrameBuffer::Type::kI420};
	return info;
}

void NvEncoder::LayerConfig::SetStreamState(bool send_stream) 
{
	if (send_stream && !sending) {
		// Need a key frame if we have not sent this stream before.
		RTC_TS << "Set key frame request";
		key_frame_request = true;
	}
	sending = send_stream;
}

}  // namespace webrtc
