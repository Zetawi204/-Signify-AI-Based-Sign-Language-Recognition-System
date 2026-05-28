
=====================
|| Signify AI Model ||
=====================


Project Overview
----------------
Signify is an AI-based Arabic sign language recognition system. It uses the camera to detect hand gestures in real time, processes hand landmarks using MediaPipe, and classifies gestures using a trained TensorFlow Lite model. The recognized text is sent to the web dashboard through a local Flask server.


Requirements
------------
- Python 3.12 64-bit
- Camera
- Internet connection for the first installation
- Required libraries listed in requirements.txt


Important Notes
---------------
- Do not copy the .venv folder from another computer.
- Create a new virtual environment on each device.
- Open the terminal inside the AI model project folder.
- Installing requirements may take several minutes. Wait until the process finishes completely.
- Keep the terminal open while the model server is running.


How to Run
----------
1. Create a virtual environment:

   py -3.12 -m venv .venv

2. Activate it:

   .\.venv\Scripts\activate

3. Upgrade pip:

   python -m pip install --upgrade pip

4. Install requirements:

   pip install -r requirements.txt

5. Test the main libraries:

   python -c "import tensorflow as tf; import mediapipe as mp; import cv2; import numpy as np; print('TensorFlow:', tf.__version__); print('MediaPipe:', mp.__version__); print('MediaPipe solutions:', hasattr(mp, 'solutions')); print('OpenCV:', cv2.__version__); print('NumPy:', np.__version__)"

6. Run the server:

   python app.py

7. Open:

   http://127.0.0.1:5000

8. Test camera stream:

   http://127.0.0.1:5000/video_feed

9. Test recognized text:

   http://127.0.0.1:5000/get_text


Main API Endpoints
------------------
/video_feed    Provides the live camera stream.
/get_text      Returns the recognized text.
/reset_text    Clears the recognized text.
/delete_last   Deletes the last character.
/stop_camera   Stops the camera.


Recommended requirements.txt
----------------------------
tensorflow==2.16.2
mediapipe==0.10.21
numpy==1.26.4
opencv-python==4.9.0.80
flask==3.0.3
flask-cors==4.0.1
pandas==2.2.2
seaborn==0.13.2
matplotlib==3.8.4
scikit-learn==1.4.2
pillow==10.3.0
arabic-reshaper==3.0.0
python-bidi==0.4.2
protobuf==4.25.3


Troubleshooting
---------------
- If /video_feed shows a white page, check the terminal for errors and make sure no other app is using the camera.
- If this error appears: module 'mediapipe' has no attribute 'solutions', use the MediaPipe version listed in requirements.txt.
- If the virtual environment does not activate, run:

  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

- If the dashboard does not show the camera, make sure Flask is running and the website uses:

  http://127.0.0.1:5000


Notes
-----
- The model server must run before using the live translation page.
- The project uses keypoint_classifier.tflite for real-time prediction.
- The .hdf5 and .keras files are kept as training evidence.