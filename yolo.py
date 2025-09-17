import streamlit as st
from PIL import Image, ImageFilter
import numpy as np
import mediapipe as mp
from ultralytics import YOLO

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=True)
model = YOLO("yolov8n-pose.pt")  

def mediapipe_feet_check(image_pil):
    gray = image_pil.convert("L").filter(ImageFilter.FIND_EDGES)
    if np.var(np.array(gray)) < 100:
        return False, "❌ Image too blurry"
    np_image = np.array(image_pil)
    results = pose.process(np_image)
    if not results.pose_landmarks:
        return None, "⚠️ Not clear"
    lm = results.pose_landmarks.landmark
    def is_clear(idx): return lm[idx].visibility > 0.6
    ankle = lm[mp_pose.PoseLandmark.LEFT_ANKLE]
    if not is_clear(mp_pose.PoseLandmark.LEFT_ANKLE) or ankle.y > 0.95:
        return False, "Not Allowed ❌"
    return True, "Allowed ✅"

def detect_body(image):
    image_np = np.array(image)
    results = model.predict(image_np, save=False, verbose=False)
    result = results[0]
    if result.boxes is None or result.keypoints is None:
        return "No person or keypoints detected - Not allowed", 0.0
    boxes = result.boxes
    keypoints = result.keypoints
    if boxes.cls is None or not hasattr(keypoints, "xy") or not hasattr(keypoints, "conf"):
        return "Missing detection data - Not allowed", 0.0
    classes = boxes.cls.cpu().numpy()
    boxes_xyxy = boxes.xyxy.cpu().numpy()
    keypoints_list = keypoints.xy
    keypoint_scores = keypoints.conf
    if len(classes) != len(keypoints_list):
        return "Mismatch in detections - Not allowed", 0.0
    image_height = image.height
    min_box_height_ratio = 0.5
    for cls, box, kp_xy, kp_conf in zip(classes, boxes_xyxy, keypoints_list, keypoint_scores):
        if cls != 0:
            continue
        y1, y2 = box[1], box[3]
        box_height = abs(y2 - y1)
        if box_height < image_height * min_box_height_ratio:
            continue
        kp = kp_xy.cpu().numpy()
        conf = kp_conf.cpu().numpy()
        if kp.shape[0] < 17:
            continue
        threshold = 0.5
        legs_valid = all(conf[i] > threshold for i in [13, 14, 15, 16])
        upper_valid = all(conf[i] > threshold for i in [5, 6])
        if legs_valid and upper_valid:
            return "man in full body", 1.0
    return "Not full body - Not allowed", 0.0

st.title("Upload Image for Body Detection")

file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])

if file:
    img = Image.open(file).convert("RGB")
    st.image(img, caption="Uploaded Image")

    result1, msg1 = mediapipe_feet_check(img)
    result2, score2 = detect_body(img)

    st.write("Mediapipe Check:", msg1)
    st.write("YOLOv8 Check:", result2, f"(score: {score2:.2f})")
