Folder architecture
====

```
.
├──{machine name}
│  ├──{intermediate data}
│  │  ├──{data with timestamp}
│  │  └──{data.finish}
│  └──logs
│     └──{program}
|        ├──{log in cleartext}
│        └──{log in binary format}
```

The first level is the machine names, including:
- **lab7**, laptop, on the vehicle
- **mobix**, MEC1, on PLMN1
- **lab6**, coordinator, at Aalto cloud
- **lab4**, MEC2, on PLMN2

The second level container intermediate data and program logs.

Intermediate data is the output data of the programs, which is also the input of some other programs. It includes:
- **gps**, logs the gps location on every 1 second
- **bts**, logs the segmentation result for each frame
- **frames**, logs each video frame that the video stream server receives
- **interface**, logs the HDMap result for each frame, i.e., the location of detected traffic signs
- **yolo**, logs the object detection result by YOLO for each frame

Program logs trace the internal state of the programs, especially the timestamp.They include:
- **webrtc**, for video streaming, including the sending and receving timestamp of each packet, as well as its associated frame number
- **eatw**, for coordination, including the timestamp of service start, migration and termination actions
- **dns**, for service discovery, including response of DNS queries, as well as the timestamps

The third level and afterwards is the log files.
