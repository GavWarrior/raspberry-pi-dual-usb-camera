"""
Flask application to serve video streams from two USB cameras on a Raspberry Pi.

The application uses OpenCV to capture frames from two separate USB cameras and
exposes two MJPEG HTTP endpoints for streaming the live images. A simple web
interface (see `templates/index.html`) embeds the video streams side by side and
provides sliders to adjust the exposure settings on each camera. When the user
moves a slider the new exposure value is sent back to the server using a
JavaScript `fetch` call, which updates the exposure on the corresponding
`cv2.VideoCapture` object.

Usage:
    python app.py

By default the server binds to 0.0.0.0 on port 5000 so it is reachable from
other devices on the same network. You can override the host and port by
exporting the environment variables ``FLASK_RUN_HOST`` and ``FLASK_RUN_PORT``.

Note: this script assumes two USB cameras are available at ``/dev/video0`` and
``/dev/video1``. If your cameras appear at different device indices you can
override ``CAMERA_INDICES`` below.
"""

import os
import threading
from typing import Generator

from flask import Flask, Response, render_template, request, jsonify
import cv2
import numpy as np

# Indices of the two cameras. Change these if your cameras are at different
# device nodes.
CAMERA_INDICES = [0, 1]

# Default exposure settings for each camera. On many UVC webcams running under
# Linux, the exposure value can be set to an integer representing the
# integration time in units of one hundredth of a second (for example 100
# corresponds to 1 s exposure). On Windows the values can be negative. Feel
# free to adjust these defaults to suit your particular cameras.
DEFAULT_EXPOSURES = [50, 50]

app = Flask(__name__)


class Camera:
    """Wrap a cv2.VideoCapture object and expose thread‑safe frame capture.

    Captures frames from a camera in a dedicated thread so that blocking I/O
    operations don’t interfere with the Flask request/response cycle. The
    latest frame is cached and returned to clients streaming the feed. This
    class also exposes a simple method for updating the exposure value via
    OpenCV.
    """

    def __init__(self, index: int, exposure: int) -> None:
        self.index = index
        self.capture = cv2.VideoCapture(index)
        # Try to set sensible defaults: MJPEG encoding and 640×480 resolution.
        self.capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        # Set initial exposure.
        self.set_exposure(exposure)
        self.lock = threading.Lock()
        self.frame = None  # type: ignore[assignment]
        self.running = False

    def start(self) -> None:
        """Start the background thread for reading frames."""
        if self.running:
            return
        self.running = True
        threading.Thread(target=self._update, daemon=True).start()

    def _update(self) -> None:
        """Read frames in a loop and store the most recent frame."""
        while self.running:
            ret, frame = self.capture.read()
            if not ret:
                continue
            with self.lock:
                self.frame = frame

    def get_frame(self) -> bytes:
        """Return the most recent frame encoded as JPEG bytes."""
        with self.lock:
            if self.frame is None:
                # Return a blank image while the camera warms up.
                blank = 255 * np.ones((480, 640, 3), dtype=np.uint8)
                ret, buffer = cv2.imencode(".jpg", blank)
                return buffer.tobytes()
            # Encode the current frame as JPEG.
            ret, buffer = cv2.imencode(".jpg", self.frame)
            return buffer.tobytes()

    def set_exposure(self, value: float) -> None:
        """Set the exposure for this camera via OpenCV.

        Some cameras may require auto‑exposure to be disabled before a manual
        value takes effect. You can experiment with `CAP_PROP_AUTO_EXPOSURE` if
        setting the exposure does not work for your hardware. See
        https://www.kurokesu.com/main/2020/05/22/uvc-camera-exposure-timing-in-opencv/
        for details on UVC exposure control under Linux and Windows.
        """
        # Attempt to turn off auto exposure: for CAP_V4L2 the value 1 means
        # manual mode and 3 means auto mode.
        self.capture.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
        self.capture.set(cv2.CAP_PROP_EXPOSURE, float(value))

    def release(self) -> None:
        """Release the underlying VideoCapture object."""
        self.running = False
        self.capture.release()


# Create global camera instances
cameras = [Camera(idx, exp) for idx, exp in zip(CAMERA_INDICES, DEFAULT_EXPOSURES)]

# Start capturing on all cameras
for cam in cameras:
    cam.start()


@app.route('/')
def index() -> str:
    """Render the main page with the video feeds."""
    return render_template('index.html')


def generate_frames(cam: Camera) -> Generator[bytes, None, None]:
    """Yield MJPEG frames from a given Camera instance."""
    while True:
        frame = cam.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed/<int:cam_id>')
def video_feed(cam_id: int) -> Response:
    """Serve the MJPEG stream for the specified camera.

    Args:
        cam_id: 1 for the first camera, 2 for the second.

    Returns:
        A Flask Response streaming the MJPEG frames.
    """
    # Convert 1‑based index from URL to 0‑based index in list
    idx = cam_id - 1
    if idx < 0 or idx >= len(cameras):
        return Response(status=404)
    return Response(generate_frames(cameras[idx]),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/set_exposure/<int:cam_id>', methods=['POST'])
def set_exposure_endpoint(cam_id: int) -> Response:
    """API endpoint to update the exposure of a camera.

    Expects a form field named `exposure` containing a numeric value. This
    handler sets the exposure on the specified camera and returns JSON to
    acknowledge the update.
    """
    idx = cam_id - 1
    if idx < 0 or idx >= len(cameras):
        return jsonify({'error': 'Camera not found'}), 404
    try:
        value = float(request.form.get('exposure', ''))
    except ValueError:
        return jsonify({'error': 'Invalid exposure value'}), 400
    cameras[idx].set_exposure(value)
    return jsonify({'status': 'ok', 'exposure': value})


@app.route('/exposure/<int:cam_id>')
def get_exposure(cam_id: int) -> Response:
    """Return the current exposure value for a camera (read‑only).

    Note: OpenCV does not provide a reliable method to read back the current
    exposure value on all systems. This endpoint returns the value stored in
    memory, which may diverge from the actual camera setting if the hardware
    ignores the request. Use this endpoint as a heuristic rather than a
    definitive source.
    """
    idx = cam_id - 1
    if idx < 0 or idx >= len(cameras):
        return jsonify({'error': 'Camera not found'}), 404
    # Attempt to read the current exposure property
    exposure = cameras[idx].capture.get(cv2.CAP_PROP_EXPOSURE)
    return jsonify({'exposure': exposure})


if __name__ == '__main__':
    # Read host/port from environment variables for convenience when deploying.
    host = os.environ.get('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_RUN_PORT', '5000'))
    try:
        app.run(host=host, port=port, threaded=True, debug=False)
    finally:
        # Cleanly release resources when the server stops.
        for cam in cameras:
            cam.release()
