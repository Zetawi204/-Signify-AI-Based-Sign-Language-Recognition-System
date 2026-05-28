# Signify: AI-Based Sign Language Recognition System

Signify is an AI-based sign language recognition system designed to recognize selected Jordanian Arabic sign language gestures and convert them into readable text in real time. The system uses a standard camera, computer vision, and machine learning without requiring special wearable hardware such as sensor gloves.

The project includes an AI model, a local Flask API, and a web-based dashboard. The AI model recognizes hand gestures, while the web dashboard displays the translated text and provides user features such as login, signup, conversation history, voice output, gesture guide, profile management, and feedback.

---

## Project Features

* Real-time camera-based sign language recognition
* Hand landmark extraction using MediaPipe
* Gesture classification using a trained TensorFlow Lite model
* Web dashboard for live translation
* User signup and login
* Password hashing and password reset
* Conversation history
* Voice output
* Gesture guide
* User profile page
* Feedback feature
* Local API integration between the AI model and the web dashboard

---

## Technologies Used

### AI Model

* Python
* OpenCV
* MediaPipe
* TensorFlow / Keras
* TensorFlow Lite
* NumPy
* Flask
* Flask-CORS

### Web System

* HTML
* CSS
* JavaScript
* PHP
* MySQL
* XAMPP

---

## System Architecture

The system works through the following pipeline:

Camera Input → OpenCV Frame Capture → MediaPipe Hand Detection → Landmark Extraction → Data Preprocessing → TensorFlow Lite Classifier → Gesture Prediction → Flask API → Web Dashboard Output

The AI model runs locally using a Flask server. The web dashboard communicates with this server through API endpoints to display the live camera stream and the recognized text in real time.

---

## AI Model Description

The AI model uses a camera-based computer vision approach. It does not train directly on raw images. Instead, it uses MediaPipe Hands to extract 21 hand landmark points from each detected hand gesture.

Each landmark contains x and y coordinates, so each gesture is represented by 42 numerical values. These values are preprocessed by converting them into relative coordinates using the wrist point as a base point, then normalizing the values.

The model is a neural network classifier based on a Multi-Layer Perceptron (MLP) architecture. It was trained using TensorFlow/Keras and converted into TensorFlow Lite format for real-time prediction.

---

## Main API Endpoints

| Endpoint       | Description                            |
| -------------- | -------------------------------------- |
| `/video_feed`  | Provides the live camera stream        |
| `/get_text`    | Returns the recognized translated text |
| `/reset_text`  | Clears the recognized text             |
| `/delete_last` | Deletes the last character             |
| `/stop_camera` | Stops the camera                       |

---

## AI Model Setup Guide

The detailed instructions for running the AI model server, creating the virtual environment, installing the required libraries, testing the camera stream, and checking the API endpoints are provided in a separate file inside the AI model folder.

For more details, see:

```text
Signify_Ai_Model.../README & RUN_STEPS.txt
```

## How to Run the Web System

1. Open XAMPP.
2. Start Apache and MySQL.
3. Copy the web project folder into:

```text
C:\xampp\htdocs\
```

4. Import the database SQL file into phpMyAdmin.
5. Update the database connection file if needed.
6. Open the project in the browser using localhost, for example:

```text
http://localhost/wiseproject/
```

7. Make sure the AI Flask server is running before opening the live translation dashboard. The AI model running steps are explained in the separate AI model setup file.

---

## Database

The system uses MySQL to store user accounts, login information, conversation history, and feedback data.

Main database features include:

* User registration
* User login
* Password hashing
* Password reset
* Conversation history saving
* User feedback storage

---

## Important Notes

* The AI model server must be running before using the web dashboard.
* The detailed AI model running steps are documented separately inside the AI model folder.
* The project currently runs locally using XAMPP and Flask.
* The current version supports selected gestures only.

---

## Known Limitations

* The system currently supports a selected set of Jordanian Arabic sign language gestures.
* Recognition accuracy may be slightly affected by lighting, camera quality, background, and hand clarity.
* The current version focuses mainly on single-hand gestures.
* The system is currently deployed locally and not yet hosted online.

---

## Future Work

* Expand the gesture dataset.
* Support more Jordanian Arabic sign language gestures.
* Improve recognition accuracy under different lighting cond
* Support dynamic and two-hand gestures.
* Deploy the system online.
* Improve mobile compatibility.
* Test the system with real users.

---

## Team Members

* Khalid Alaa Zetawi
* Hamza Muwaffaq Alsalhi
* Lutfe Zakaria Abu Tahnoon
* Maya Ahmad Alkhataleen


---

## Supervisor

Dr. Abdullah Al-Zaqebah

Faculty of Information Technology
The World Islamic Sciences and Education University

---

## Project Stage

Working Demo
