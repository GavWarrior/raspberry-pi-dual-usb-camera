# Raspberry Pi Dual USB Camera Web Viewer

This project provides a simple web application that streams video from two USB
cameras connected to your Raspberry Pi. The streams are displayed side by side in a
web browser and include sliders for adjusting each camera’s exposure setting
dynamically. The backend is built with [Flask](https://flask.palletsprojects.com)
and uses [OpenCV](https://opencv.org) to access the cameras.

## Features

- Live MJPEG streams from two USB cameras accessible via `/video_feed/1` and
  `/video_feed/2` endpoints.
- Single HTML page (`index.html`) showing both streams and controls for exposure.
- Adjustable exposure values via HTML range sliders; updates are sent to the
  server without reloading the page.
- Default video resolution of 640×480; adjust `app.py` if higher or lower
  resolution is desired.

## Prerequisites

- Two UVC‑compliant USB cameras connected to your Raspberry Pi (e.g. `/dev/video0`
  and `/dev/video1`).
- Python 3.7+.
- Internet access for installing dependencies.

## Installation

1. Clone this repository onto your Raspberry Pi or copy the files into a
   directory of your choice.
2. Run the provided installation script to install system and Python
   dependencies:

   ```bash
   cd raspberry_pi_cameras
   chmod +x install_dependencies.sh
   ./install_dependencies.sh
   ```

   This script uses `apt` and `pip` to install OpenCV, Flask and numpy.

3. Run the Flask application:

   ```bash
   python3 app.py
   ```

   By default the server listens on port 5000 and binds to all network
   interfaces. You can override this by setting the environment variables
   `FLASK_RUN_HOST` and `FLASK_RUN_PORT`.

4. In a web browser on any device on the same network, navigate to
   `http://<raspberry-pi-ip>:5000/`. You should see the two video feeds and
   sliders to control exposure. If the streams do not load, verify the device
   indices in `app.py` (set in the `CAMERA_INDICES` list) match your cameras.

## Notes on Exposure Values

Exposure values are hardware dependent. On Linux, USB cameras typically
represent exposure in units of 1/100 s, so a value of `50` corresponds to a
0.5 s exposure. On Windows the values can be negative (0 for 1 s, −1 for 0.5 s,
 etc.) as described in this [Kurokesu article](https://www.kurokesu.com/main/2020/05/22/uvc-camera-exposure-timing-in-opencv/)【283390783303547†L16-L32】. You may
need to experiment with your cameras to find appropriate ranges. The web page
defaults to a range of 1–200, which works for many UVC webcams on Linux.

## Limitations

- The current implementation reads the latest frame from each camera without
  frame synchronization. There may be slight delays between the two streams.
- Some webcams ignore manual exposure settings or may require additional
  V4L2 controls (`v4l2-ctl`) to disable auto‑exposure. Adjust the `set_exposure`
  method in `app.py` if your hardware behaves differently.
- Running two cameras at high resolutions may tax the Raspberry Pi’s USB
  bandwidth. Reduce the resolution or frame rate if you observe dropped frames.

## License

This project is released under the MIT license. See `LICENSE` if present for
more information.
