import streamlit as st
import boto3
import os
from dotenv import load_dotenv
from PIL import Image
import numpy as np
import mediapipe as mp
from ultralytics import YOLO

# Load environment
load_dotenv()

# -------------------- Streamlit Page Config --------------------
st.set_page_config(page_title="Attire Detection AI", page_icon="🧥", layout="wide")
st.markdown("""
    <style>
    .reportview-container {
        background: #f5f6fa;
        font-family: 'Segoe UI', sans-serif;
    }
    h1, h2, h3 {
        color: #2d3436;
    }
    .stButton>button {
        color: white;
        background: linear-gradient(to right, #6a89cc, #b8e994);
        border: none;
        padding: 0.5rem 1.5rem;
        font-size: 1rem;
        border-radius: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------- AWS Setup --------------------
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_REGION = "ap-southeast-2"

rekognition = boto3.client(
    "rekognition",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

# -------------------- Clothing Categories --------------------
UPPER_CLOTHING = {
    "shirt", "t-shirt", "dress shirt", "blouse", "long sleeve", "sleeve", "jersey", "polo",
    "coat", "cape", "robe", "vest", "sweater", "hood", "jacket", "lab coat",
    "overcoat", "trench coat", "poncho", "tuxedo", "blazer", "suit", "formal wear",
    "collar", "woman", "female", "girl"
}
LOWER_CLOTHING = {"pants", "jeans", "khaki", "shorts", "skirt", "pajamas"}
FOOTWEAR = {
    "shoe", "sneaker", "boot", "high heel", "riding boot", "clogs", "running shoe",
    "sandal", "cowboy boot", "flip-flop", "wedge", "ski boot", "barefoot"
}

formal_upper = {"coat", "blazer", "jacket", "long sleeve", "sleeve", "shirt", "suit", "sweater", "overcoat",
                "dress shirt", "formal wear", "polo", "collar"}
casual_upper = {"robe", "T-Shirt", "jersey", "cape", "vest", "hood", "poncho"}

formal_lower = {"pants", "khaki"}
casual_lower = {"jeans", "shorts", "skirt", "pajamas"}

formal_foot = {"shoe", "boot", "high heel", "ski boot", "cowboy boot"}
casual_foot = {"sneaker", "flip-flop", "ski boot", "barefoot", "running shoe", "sandal", "clogs"}

# -------------------- Mediapipe + YOLO --------------------
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=True)
yolo_model = YOLO("yolov8n-pose.pt")

def mediapipe_feet_check(image_pil):
    gray = image_pil.convert("L")
    np_image = np.array(gray)
    if np.var(np_image) < 100:
        return False, "❌ Image too blurry"
    results = pose.process(np.array(image_pil))
    if not results.pose_landmarks:
        return None, "⚠️ Pose not clear"
    lm = results.pose_landmarks.landmark
    ankle = lm[mp_pose.PoseLandmark.LEFT_ANKLE]
    if ankle.visibility < 0.6 or ankle.y > 0.95:
        return False, "Not Allowed ❌"
    return True, "Allowed ✅"

def detect_body(image):
    image_np = np.array(image)
    results = yolo_model.predict(image_np, save=False, verbose=False)
    result = results[0]
    if result.boxes is None or result.keypoints is None:
        return "No person detected - Not allowed", 0.0
    boxes = result.boxes
    keypoints = result.keypoints
    if boxes.cls is None:
        return "Missing detection data - Not allowed", 0.0
    classes = boxes.cls.cpu().numpy()
    boxes_xyxy = boxes.xyxy.cpu().numpy()
    keypoints_list = keypoints.xy
    keypoint_scores = keypoints.conf
    image_height = image.height
    for cls, box, kp_xy, kp_conf in zip(classes, boxes_xyxy, keypoints_list, keypoint_scores):
        if cls != 0:
            continue
        box_height = abs(box[3] - box[1])
        if box_height < image_height * 0.5:
            continue
        kp = kp_xy.cpu().numpy()
        conf = kp_conf.cpu().numpy()
        if kp.shape[0] < 17:
            continue
        legs_valid = all(conf[i] > 0.5 for i in [13, 14, 15, 16])
        upper_valid = all(conf[i] > 0.5 for i in [5, 6])
        if legs_valid and upper_valid:
            return "Full body detected ✅", 1.0
    return "Not full body - Not allowed", 0.0

# -------------------- Attire Evaluation --------------------
def evaluate_pants_section(detected_items, present_footwear, formal_present_footwear):
    if "pants" in detected_items and detected_items["pants"] > 50:
        if "shorts" in detected_items and detected_items["shorts"] >= 60:
            return "Casual Lower ❌1"
        elif len(formal_present_footwear) >= 3:
            return "Formal Dress ✅"
        elif "shoe" not in detected_items:
            return "Casual Footwear ❌"
        else:
            return "Formal Dress ✅"
    else:
        return "Casual Lower ❌"

def get_attire_result(detected_items):
    footwear_items = {"sneaker", "sandal", "flip-flop", "barefoot", "running shoe"}
    formal_footwear_items = {"shoe", "boot", "high heel", "cowboy boot"}
    present_footwear = [item for item in footwear_items if item in detected_items]
    formal_present_footwear = [item for item in formal_footwear_items if item in detected_items]

    if "formal wear" in detected_items and detected_items["formal wear"] >= 48:
        return evaluate_pants_section(detected_items, present_footwear, formal_present_footwear)
    elif "t-shirt" in detected_items:
        return "Casual Upper ❌"
    elif "shirt" in detected_items and detected_items["shirt"] >= 50:
        return evaluate_pants_section(detected_items, present_footwear, formal_present_footwear)
    else:
        return "Casual Upper ❌"

def display_items(formal_items, casual_items, category_icon, category_name):
    st.markdown(f"<h3 style='color:#6c5ce7;'>{category_icon} {category_name}</h3>", unsafe_allow_html=True)
    subcol1, subcol2 = st.columns(2)
    with subcol1:
        st.markdown("🟩 <b>Formal:</b>", unsafe_allow_html=True)
        if formal_items:
            for item, conf in formal_items.items():
                st.markdown(f"<span style='color:#00b894;'>• {item.title()} ({conf:.2f}%)</span>", unsafe_allow_html=True)
        else:
            st.markdown("<i style='color:#636e72;'>None</i>", unsafe_allow_html=True)
    with subcol2:
        st.markdown("🟥 <b>Casual:</b>", unsafe_allow_html=True)
        if casual_items:
            for item, conf in casual_items.items():
                st.markdown(f"<span style='color:#d63031;'>• {item.title()} ({conf:.2f}%)</span>", unsafe_allow_html=True)
        else:
            st.markdown("<i style='color:#636e72;'>None</i>", unsafe_allow_html=True)

# -------------------- Streamlit Workflow --------------------
st.markdown("<h2 style='color:#6c5ce7;'>📂 Upload Images for Attire Detection</h2>", unsafe_allow_html=True)
uploaded_files = st.file_uploader("Upload images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files:
    os.makedirs("uploads", exist_ok=True)

    for uploaded_file in uploaded_files:
        image_path = os.path.join("uploads", uploaded_file.name)
        with open(image_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.image(image_path, caption=f"📸 Uploaded Image: {uploaded_file.name}", width=500)

        # --- Run YOLO + Mediapipe Checks ---
        img = Image.open(image_path).convert("RGB")
        result1, msg1 = mediapipe_feet_check(img)
        result2, score2 = detect_body(img)

        st.write("Mediapipe Check:", msg1)
        st.write("YOLOv8 Check:", result2, f"(score: {score2:.2f})")

        if not result1 or score2 < 0.8:
            st.error("❌ Image not suitable for attire detection")
            continue

        # --- AWS Rekognition Step ---
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()

        response = rekognition.detect_labels(Image={"Bytes": image_bytes}, MaxLabels=100, MinConfidence=0.1)
        detected_items = {label["Name"].lower(): label["Confidence"] for label in response.get("Labels", [])}

        upper_items = {item: conf for item, conf in detected_items.items() if item in UPPER_CLOTHING}
        lower_items = {item: conf for item, conf in detected_items.items() if item in LOWER_CLOTHING}
        foot_items = {item: conf for item, conf in detected_items.items() if item in FOOTWEAR}

        formal_upper_items = {item: conf for item, conf in upper_items.items() if item in formal_upper}
        casual_upper_items = {item: conf for item, conf in upper_items.items() if item in casual_upper or item not in formal_upper}
        formal_lower_items = {item: conf for item, conf in lower_items.items() if item in formal_lower}
        casual_lower_items = {item: conf for item, conf in lower_items.items() if item in casual_lower or item not in formal_lower}
        formal_foot_items = {item: conf for item, conf in foot_items.items() if item in formal_foot}
        casual_foot_items = {item: conf for item, conf in foot_items.items() if item in casual_foot or item not in formal_foot}

        col1, col2, col3 = st.columns(3)
        with col1: display_items(formal_upper_items, casual_upper_items, "👕", "Upper")
        with col2: display_items(formal_lower_items, casual_lower_items, "👖", "Lower")
        with col3: display_items(formal_foot_items, casual_foot_items, "👟", "Footwear")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h3 style='color:#0984e3;'>🧠 Final Attire Analysis</h3>", unsafe_allow_html=True)

        final_result = get_attire_result(detected_items)
        if final_result.startswith("Formal"):
            st.success(final_result)
        else:
            st.warning(final_result)
