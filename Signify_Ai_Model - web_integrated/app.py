#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import copy
import argparse
import itertools
import time

import cv2 as cv
import numpy as np
import mediapipe as mp

from flask import Flask, Response, jsonify
from flask_cors import CORS

from utils import CvFpsCalc
from model import KeyPointClassifier

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

app = Flask(__name__)
CORS(app)

# =========================
# GLOBAL STATE
# =========================
current_text = ""
camera_active = False
newline_count = 0

stable_letter = ""
stable_start_time = None
current_pose_accepted = False

no_hand_start_time = None
no_hand_space_added = False

delete_lock = False

HOLD_SECONDS = 1
NO_HAND_SPACE_SECONDS = 0.8
MESSAGE_BREAK_TOKEN = "<MSG_BREAK>"

NEWLINE_COMMANDS = {
    "newline",
    "new line",
    "new-line",
    "new_line",
    "nextmessage",
    "next message",
    "messagebreak",
    "message break",
    "msgbreak",
    "msg break",
}

DELETE_COMMANDS = {
    "delete",
    "del",
    "backspace",
    "back space",
    "remove",
    "erase",
    "حذف",
}


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--width", help="cap width", type=int, default=640)
    parser.add_argument("--height", help="cap height", type=int, default=480)

    parser.add_argument("--use_static_image_mode", action="store_true")
    parser.add_argument("--min_detection_confidence", type=float, default=0.7)
    parser.add_argument("--min_tracking_confidence", type=float, default=0.5)

    args, _ = parser.parse_known_args()
    return args


def normalize_label(label):
    if label is None:
        return ""
    return str(label).strip()


def normalize_command_key(label):
    if label is None:
        return ""
    return (
        str(label)
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )


def is_newline_command(label):
    return normalize_command_key(label) in NEWLINE_COMMANDS


def is_delete_command(label):
    return normalize_command_key(label) in DELETE_COMMANDS


def is_command_label(label):
    return is_newline_command(label) or is_delete_command(label)


def append_message_break():
    global current_text, newline_count

    current_text = current_text.rstrip()

    # ما نضيف MSG_BREAK إذا النص فاضي
    # وما نكررها إذا كانت موجودة آخر النص
    if current_text != "" and not current_text.endswith(MESSAGE_BREAK_TOKEN):
        current_text += MESSAGE_BREAK_TOKEN
        newline_count += 1


def delete_last_character():
    global current_text, newline_count

    if current_text:
        current_text = current_text.rstrip()

        if current_text.endswith(MESSAGE_BREAK_TOKEN):
            current_text = current_text[:-len(MESSAGE_BREAK_TOKEN)]

            if newline_count > 0:
                newline_count -= 1

        elif current_text:
            current_text = current_text[:-1]


def append_recognized_item(label):
    global current_text

    clean_label = normalize_label(label)

    if clean_label == "" or clean_label.lower() == "unknown":
        return

    # حركة الحذف
    if is_delete_command(clean_label):
        delete_last_character()
        return

    # حركة New Message / Newline
    if is_newline_command(clean_label):
        append_message_break()
        return

    # حرف عادي
    current_text += clean_label


def reset_recognition_state(clear_text=False):
    global current_text, newline_count
    global stable_letter, stable_start_time, current_pose_accepted
    global no_hand_start_time, no_hand_space_added
    global delete_lock

    if clear_text:
        current_text = ""
        newline_count = 0

    stable_letter = ""
    stable_start_time = None
    current_pose_accepted = False

    no_hand_start_time = None
    no_hand_space_added = False

    delete_lock = False


def generate_frames():
    global current_text, camera_active
    global stable_letter, stable_start_time, current_pose_accepted
    global no_hand_start_time, no_hand_space_added
    global delete_lock

    args = get_args()

    cap_device = args.device
    cap_width = args.width
    cap_height = args.height

    use_static_image_mode = args.use_static_image_mode
    min_detection_confidence = args.min_detection_confidence
    min_tracking_confidence = args.min_tracking_confidence


    cap = cv.VideoCapture(cap_device)
    cap.set(cv.CAP_PROP_FRAME_WIDTH, cap_width)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, cap_height)

    if not cap.isOpened():
        camera_active = False
        print("Camera could not be opened")
        return

    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=use_static_image_mode,
        max_num_hands=1,
        min_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence,
    )

    keypoint_classifier = KeyPointClassifier()

    with open(
        "model/keypoint_classifier/keypoint_classifier_label.csv",
        encoding="utf-8-sig",
    ) as f:
        keypoint_classifier_labels = [row[0] for row in csv.reader(f)]

    cv_fps_calc = CvFpsCalc(buffer_len=10)
    display_fps = 0
    last_fps_update_time = time.time()
    camera_active = True

    try:
        while camera_active:
            fps = cv_fps_calc.get()
            if time.time() - last_fps_update_time >= 0.25:
                display_fps = fps
                last_fps_update_time = time.time()

            ret, image = cap.read()
            if not ret:
                break

            image = cv.flip(image, 1)
            image = cv.resize(image, (480, 360))
            debug_image = copy.deepcopy(image)

            image_rgb = cv.cvtColor(image, cv.COLOR_BGR2RGB)
            image_rgb.flags.writeable = False
            results = hands.process(image_rgb)
            image_rgb.flags.writeable = True

            detected_hand = False

            if results.multi_hand_landmarks is not None:
                for hand_landmarks, handedness in zip(
                    results.multi_hand_landmarks,
                    results.multi_handedness
                ):
                    if handedness.classification[0].label != "Right":
                        continue

                    detected_hand = True

                    landmark_list = calc_landmark_list(debug_image, hand_landmarks)

                    pre_processed_landmark_list = pre_process_landmark(landmark_list)
                    hand_sign_id = keypoint_classifier(pre_processed_landmark_list)

                    raw_hand_sign_text = (
                        keypoint_classifier_labels[hand_sign_id]
                        if 0 <= hand_sign_id < len(keypoint_classifier_labels)
                        else "Unknown"
                    )

                    hand_sign_text = normalize_label(raw_hand_sign_text)
                    print("Hand Sign:", hand_sign_text)

                    now = time.time()

                    if delete_lock and hand_sign_text != stable_letter:
                        delete_lock = False
                    
                    detected_text = ""

                    if hand_sign_text != "" and hand_sign_text.lower() != "unknown":
                        detected_text = hand_sign_text

                    if detected_text != "":
                        if stable_letter != detected_text:
                            stable_letter = detected_text
                            stable_start_time = now
                            current_pose_accepted = False
                        else:
                            if stable_start_time is not None:
                                elapsed = now - stable_start_time

                                if elapsed >= HOLD_SECONDS and not current_pose_accepted:
                                    append_recognized_item(stable_letter)
                                    current_pose_accepted = True

                                    if is_delete_command(stable_letter):
                                        delete_lock = True
                    else:
                        stable_letter = ""
                        stable_start_time = None
                        current_pose_accepted = False

                    no_hand_start_time = None
                    no_hand_space_added = False

                    debug_image = draw_landmarks(debug_image, landmark_list)
                    debug_image = draw_info_text(
                        debug_image,
                        hand_sign_text,
                    )

                    if (
                        stable_letter != ""
                        and stable_start_time is not None
                        and not current_pose_accepted
                    ):
                        progress = min(
                            (time.time() - stable_start_time) / HOLD_SECONDS,
                            1.0
                        )
                        debug_image = draw_progress_circle(
                            debug_image,
                            center=(240, 95),
                            radius=28,
                            progress=progress,
                        )

                    break

            if not detected_hand:
                now = time.time()

                stable_letter = ""
                stable_start_time = None
                current_pose_accepted = False

                delete_lock = False
            
                if no_hand_start_time is None:
                    no_hand_start_time = now
                else:
                    if (
                        (now - no_hand_start_time) >= NO_HAND_SPACE_SECONDS
                        and not no_hand_space_added
                    ):
                        if (
                            len(current_text) > 0
                            and not current_text.endswith(" ")
                            and not current_text.endswith(MESSAGE_BREAK_TOKEN)
                        ):
                            current_text += " "
                        no_hand_space_added = True

            debug_image = draw_info(debug_image, display_fps)

            ok, buffer = cv.imencode(".jpg", debug_image)
            if not ok:
                continue

            frame = buffer.tobytes()

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )

    finally:
        camera_active = False
        cap.release()
        hands.close()


# =========================
# FLASK ROUTES / API
# =========================

@app.route("/status")
def status():
    return jsonify({
        "success": True,
        "model": "online",
        "camera_active": camera_active,
        "text": current_text,
        "newline_count": newline_count
    })


@app.route("/")
def home():
    return jsonify({
        "success": True,
        "message": "Signify model server is running",
        "model": "online",
        "camera_active": camera_active,
        "newline_count": newline_count
    })


@app.route("/video_feed")
def video_feed():
    global camera_active

    camera_active = True

    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/get_text")
def get_text():
    global current_text, newline_count

    return jsonify({
        "success": True,
        "text": current_text,
        "newline_count": newline_count
    })


@app.route("/get_messages")
def get_messages():
    global current_text, newline_count

    messages = [
        msg.strip()
        for msg in current_text.split(MESSAGE_BREAK_TOKEN)
        if msg.strip()
    ]

    return jsonify({
        "success": True,
        "messages": messages,
        "raw_text": current_text,
        "newline_count": newline_count
    })


@app.route("/reset_text", methods=["POST"])
def reset_text():
    reset_recognition_state(clear_text=True)

    return jsonify({
        "success": True,
        "status": "success",
        "text": current_text,
        "newline_count": newline_count
    })


@app.route("/delete_last", methods=["POST"])
def delete_last():
    global current_text, newline_count
    global stable_letter, stable_start_time, current_pose_accepted
    global delete_lock
    global no_hand_start_time, no_hand_space_added

    delete_last_character()

    stable_letter = ""
    stable_start_time = None
    current_pose_accepted = False

    no_hand_start_time = None
    no_hand_space_added = False

    delete_lock = True

    return jsonify({
        "success": True,
        "status": "success",
        "text": current_text,
        "newline_count": newline_count
    })


@app.route("/stop_camera", methods=["POST"])
def stop_camera():
    global camera_active

    camera_active = False
    reset_recognition_state(clear_text=True)

    return jsonify({
        "success": True,
        "status": "success",
        "message": "Camera stopped",
        "text": current_text,
        "newline_count": newline_count
    })


def calc_landmark_list(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]
    landmark_point = []

    for landmark in landmarks.landmark:
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)
        landmark_point.append([landmark_x, landmark_y])

    return landmark_point


def pre_process_landmark(landmark_list):
    temp_landmark_list = copy.deepcopy(landmark_list)

    base_x, base_y = 0, 0

    for index, landmark_point in enumerate(temp_landmark_list):
        if index == 0:
            base_x, base_y = landmark_point[0], landmark_point[1]

        temp_landmark_list[index][0] -= base_x
        temp_landmark_list[index][1] -= base_y

    temp_landmark_list = list(itertools.chain.from_iterable(temp_landmark_list))
    max_value = max(list(map(abs, temp_landmark_list)))

    def normalize_(n):
        return n / max_value if max_value != 0 else 0

    temp_landmark_list = list(map(normalize_, temp_landmark_list))

    return temp_landmark_list


def draw_landmarks(image, landmark_point):
    if len(landmark_point) > 0:
        cv.line(image, tuple(landmark_point[2]), tuple(landmark_point[3]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[2]), tuple(landmark_point[3]), (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[3]), tuple(landmark_point[4]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[3]), tuple(landmark_point[4]), (255, 255, 255), 2)

        cv.line(image, tuple(landmark_point[5]), tuple(landmark_point[6]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[5]), tuple(landmark_point[6]), (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[6]), tuple(landmark_point[7]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[6]), tuple(landmark_point[7]), (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[7]), tuple(landmark_point[8]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[7]), tuple(landmark_point[8]), (255, 255, 255), 2)

        cv.line(image, tuple(landmark_point[9]), tuple(landmark_point[10]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[9]), tuple(landmark_point[10]), (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[10]), tuple(landmark_point[11]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[10]), tuple(landmark_point[11]), (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[11]), tuple(landmark_point[12]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[11]), tuple(landmark_point[12]), (255, 255, 255), 2)

        cv.line(image, tuple(landmark_point[13]), tuple(landmark_point[14]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[13]), tuple(landmark_point[14]), (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[14]), tuple(landmark_point[15]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[14]), tuple(landmark_point[15]), (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[15]), tuple(landmark_point[16]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[15]), tuple(landmark_point[16]), (255, 255, 255), 2)

        cv.line(image, tuple(landmark_point[17]), tuple(landmark_point[18]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[17]), tuple(landmark_point[18]), (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[18]), tuple(landmark_point[19]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[18]), tuple(landmark_point[19]), (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[19]), tuple(landmark_point[20]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[19]), tuple(landmark_point[20]), (255, 255, 255), 2)

        cv.line(image, tuple(landmark_point[0]), tuple(landmark_point[1]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[0]), tuple(landmark_point[1]), (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[1]), tuple(landmark_point[2]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[1]), tuple(landmark_point[2]), (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[2]), tuple(landmark_point[5]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[2]), tuple(landmark_point[5]), (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[5]), tuple(landmark_point[9]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[5]), tuple(landmark_point[9]), (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[9]), tuple(landmark_point[13]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[9]), tuple(landmark_point[13]), (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[13]), tuple(landmark_point[17]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[13]), tuple(landmark_point[17]), (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[17]), tuple(landmark_point[0]), (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[17]), tuple(landmark_point[0]), (255, 255, 255), 2)

    for index, landmark in enumerate(landmark_point):
        radius = 8 if index in [4, 8, 12, 16, 20] else 5
        cv.circle(image, (landmark[0], landmark[1]), radius, (255, 255, 255), -1)
        cv.circle(image, (landmark[0], landmark[1]), radius, (0, 0, 0), 1)

    return image


def normalize_arabic_text_for_display(text):
    if text is None:
        return ""

    text = str(text).replace(MESSAGE_BREAK_TOKEN, " ")
    text = " ".join(text.split())

    return text


def reshape_arabic_text(text):
    text = normalize_arabic_text_for_display(text)
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)

    return bidi_text


def put_arabic_text(img, text, position, font_size=32, color=(255, 255, 255)):
    img_rgb = cv.cvtColor(img, cv.COLOR_BGR2RGB)
    img_pil = Image.fromarray(img_rgb)

    draw = ImageDraw.Draw(img_pil)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)

    bidi_text = reshape_arabic_text(text)
    draw.text(position, bidi_text, font=font, fill=color)

    return cv.cvtColor(np.array(img_pil), cv.COLOR_RGB2BGR)


def draw_info_text(image, hand_sign_text):
    # لا تعرض أوامر النظام مثل newline/delete كنص على الكاميرا
    if (
        hand_sign_text != ""
        and hand_sign_text.lower() != "unknown"
        and not is_command_label(hand_sign_text)
    ):
        image = put_arabic_text(
            image,
            hand_sign_text,
            (40, 35),
            60,
            (255, 0, 255),
        )

    return image


def draw_progress_circle(image, center, radius, progress):
    cv.circle(image, center, radius, (255, 255, 255), 2)

    if progress > 0:
        end_angle = int(360 * progress)
        cv.ellipse(
            image,
            center,
            (radius, radius),
            -90,
            0,
            end_angle,
            (255, 0, 255),
            6,
        )

    return image


def draw_info(image, fps):
    cv.putText(
        image,
        "FPS:" + str(fps),
        (10, 30),
        cv.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 0, 0),
        4,
        cv.LINE_AA,
    )

    cv.putText(
        image,
        "FPS:" + str(fps),
        (10, 30),
        cv.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2,
        cv.LINE_AA,
    )

    return image


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)