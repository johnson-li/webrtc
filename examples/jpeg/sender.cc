#include <iostream>
#include <stdio.h>
#include <stdlib.h>
#include <linux/ioctl.h>
#include <linux/types.h>
#include <linux/v4l2-common.h>
#include <linux/v4l2-controls.h>
#include <linux/videodev2.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <string.h>
#include <fstream>
#include <string>
#include <jpeglib.h>
#include "base/debug/stack_trace.h"

using namespace std;
int HEIGHT = 1920;
int WIDTH = 1280;
int PADDING = 4;
int DOWN_SCALE = 1;
int QUALITY = 90;

void export_file(int buffer_size, char *buffer) {
	ofstream outFile;
	outFile.open("webcam_output.jpeg", ios::binary| ios::app);

	int bufPos = 0, outFileMemBlockSize = 0;  
    int remainingBufferSize = buffer_size; 
	char* outFileMemBlock = NULL;  
	int itr = 0; 
	while(remainingBufferSize > 0) {
		bufPos += outFileMemBlockSize;  

		outFileMemBlockSize = 1024 * 1024;    
		outFileMemBlock = new char[sizeof(char) * outFileMemBlockSize];

		memcpy(outFileMemBlock, buffer+bufPos, outFileMemBlockSize);
		outFile.write(outFileMemBlock,outFileMemBlockSize);

		if(outFileMemBlockSize > remainingBufferSize)
			outFileMemBlockSize = remainingBufferSize;

		remainingBufferSize -= outFileMemBlockSize;

		cout << "[Export jpeg] " << itr++ << " Remaining bytes: "<< remainingBufferSize << endl;

		delete outFileMemBlock;
	}

	outFile.close();
}

uint8_t* encode(char *buffer, int width, int height, long capture_ts, unsigned long *outlen) {
    long start_ts = capture_ts;
    struct jpeg_compress_struct cinfo;
    struct jpeg_error_mgr jerr;

    uint8_t* outbuffer = NULL;

    cinfo.err = jpeg_std_error(&jerr);
    jpeg_create_compress(&cinfo);
    jpeg_mem_dest(&cinfo, &outbuffer, outlen);

    // jrow is a libjpeg row of samples array of 1 row pointer
    cinfo.image_width = width / DOWN_SCALE;
    cinfo.image_height = height / DOWN_SCALE;
    cinfo.input_components = 3;
    cinfo.in_color_space = JCS_YCbCr; //libJPEG expects YUV 3bytes, 24bit

    jpeg_set_defaults(&cinfo);
    jpeg_set_quality(&cinfo, QUALITY, TRUE);
    jpeg_start_compress(&cinfo, TRUE);

    uint8_t rowbuf[cinfo.image_height][cinfo.image_width * 3];
    int i, j;
    for (unsigned h = 0; h < cinfo.image_height; h++) {
        for (i = 0, j = 0; i < width * 2; i += 4 * DOWN_SCALE, j += 6) { //input strides by 4 bytes, output strides by 6 (2 pixels)
            int offset = h * DOWN_SCALE * width * 2;
            rowbuf[h][j + 0] = buffer[offset + i * DOWN_SCALE + 0]; // Y (unique to this pixel)
            rowbuf[h][j + 1] = buffer[offset + i * DOWN_SCALE + 1]; // U (shared between pixels)
            rowbuf[h][j + 2] = buffer[offset + i * DOWN_SCALE + 3]; // V (shared between pixels)
            rowbuf[h][j + 3] = buffer[offset + i * DOWN_SCALE + 2]; // Y (unique to this pixel)
            rowbuf[h][j + 4] = buffer[offset + i * DOWN_SCALE + 1]; // U (shared between pixels)
            rowbuf[h][j + 5] = buffer[offset + i * DOWN_SCALE + 3]; // V (shared between pixels)
        }
    }
    long ts = base::debug::Logger::getLogger()->getTimestampMs();
    cout << "Array copy costed " << ts - start_ts << " ms." << endl;
    start_ts = ts;

    JSAMPROW row_pointer[height];
    for (i = 0; i < height; i++) {
        row_pointer[i] = &rowbuf[i][0];
    }
    jpeg_write_scanlines(&cinfo, row_pointer, height);

    jpeg_finish_compress(&cinfo);
    jpeg_destroy_compress(&cinfo);
    ts = base::debug::Logger::getLogger()->getTimestampMs();
    cout << "JPEG encoding produced " << *outlen << " bytes, costed " << ts - start_ts << " ms." << endl;
    return outbuffer;
}

/**
 * buffer is in the format of YUYV and is of the shape ((HEIGHT + PADDING) * 2 X WIDTH )
 */
void handle_frame(char *buffer, int buffer_size) {
    // export_file(buffer_size, buffer);
    unsigned char *padded = (unsigned char *) buffer + WIDTH * HEIGHT * 2;
    int index = padded[0] << 24 | padded[2] << 16 | padded[4] << 8 | padded[6];
    if (index == 0) {
        return;
    }
    auto capture_ts = base::debug::Logger::getLogger()->getTimestampMs();
    cout << "Got frame #" << index << " at " << capture_ts << endl;
    unsigned long encoded_size = 0;
    encode(buffer, WIDTH, HEIGHT, capture_ts, &encoded_size);
}

int main(int argc, char* argv[]) {
    int fd, type;
    fd = open("/dev/video1",O_RDWR);
    if(fd < 0){
        perror("Failed to open device, OPEN");
        return 1;
    }

    v4l2_capability capability;
    if(ioctl(fd, VIDIOC_QUERYCAP, &capability) < 0){
        perror("Failed to get device capabilities, VIDIOC_QUERYCAP");
        return 1;
    }

    while (1) {
        v4l2_requestbuffers requestBuffer = {0};
        requestBuffer.count = 1; // one request buffer
        requestBuffer.type = V4L2_BUF_TYPE_VIDEO_CAPTURE; 
        requestBuffer.memory = V4L2_MEMORY_MMAP;

        if(ioctl(fd, VIDIOC_REQBUFS, &requestBuffer) < 0){
            perror("Could not request buffer from device, VIDIOC_REQBUFS");
            return 1;
        }

        v4l2_buffer queryBuffer = {0};
        queryBuffer.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        queryBuffer.memory = V4L2_MEMORY_MMAP;
        queryBuffer.index = 0;
        if(ioctl(fd, VIDIOC_QUERYBUF, &queryBuffer) < 0){
            perror("Device did not return the buffer information, VIDIOC_QUERYBUF");
            return 1;
        }
        char* buffer = (char*)mmap(NULL, queryBuffer.length, PROT_READ | PROT_WRITE, MAP_SHARED,
                fd, queryBuffer.m.offset);
        memset(buffer, 0, queryBuffer.length);

        v4l2_buffer bufferinfo;
        memset(&bufferinfo, 0, sizeof(bufferinfo));
        bufferinfo.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        bufferinfo.memory = V4L2_MEMORY_MMAP;
        bufferinfo.index = 0;

        type = bufferinfo.type;
        if(ioctl(fd, VIDIOC_STREAMON, &type) < 0){
            perror("Could not start streaming, VIDIOC_STREAMON");
            return 1;
        }

        if(ioctl(fd, VIDIOC_QBUF, &bufferinfo) < 0){
            perror("Could not queue buffer, VIDIOC_QBUF");
            return 1;
        }

        if(ioctl(fd, VIDIOC_DQBUF, &bufferinfo) < 0){
            perror("Could not dequeue the buffer, VIDIOC_DQBUF");
            return 1;
        }

        handle_frame(buffer, bufferinfo.bytesused);
    }


    // end streaming
    if(ioctl(fd, VIDIOC_STREAMOFF, &type) < 0){
        perror("Could not end streaming, VIDIOC_STREAMOFF");
        return 1;
    }

    close(fd);
    return 0;
}
