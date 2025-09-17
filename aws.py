import streamlit as st
import boto3
import os
from dotenv import load_env
load_env()

# Streamlit page config
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

AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_REGION = "ap-southeast-2" 

# AWS Rekognition Setup
rekognition = boto3.client(
    "rekognition",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

# Clothing Categories
UPPER_CLOTHING = {
    "shirt", "t-shirt", "dress shirt", "blouse", "long sleeve", "sleeve", "jersey", "polo",
    "coat", "cape", "robe", "vest", "sweater", "hood", "jacket", "lab coat",
    "overcoat", "trench coat", "poncho", "tuxedo", "blazer", "suit","formal wear","collar","woman","female","girl"
}
LOWER_CLOTHING = {
    "pants", "jeans", "khaki", "shorts", "skirt", "pajamas"
}
FOOTWEAR = {
    "shoe", "sneaker", "boot", "high heel", "riding boot", "clogs", "running shoe", "sandal",
    "cowboy boot", "flip-flop", "wedge", "ski boot", "barefoot"
}

# Formal vs Casual Definitions


formal_upper = {"coat", "blazer", "jacket", "long sleeve", "sleeve", "shirt", "suit", "sweater", "overcoat",
                "dress shirt","formal wear","polo","collar",}
casual_upper = {"robe", "T-Shirt", "jersey", "cape", "vest", "hood", "poncho"}

formal_lower = {"pants", "khaki"}
casual_lower = {"jeans", "shorts", "skirt", "pajamas"}

formal_foot = {"shoe", "boot", "high heel", "ski boot", "cowboy boot"}
casual_foot = {"sneaker", "flip-flop", "ski boot", "Barefoot", "running shoe", "Sandal", "clogs"}

def is_high_confidence(label, data, threshold):
    return label in data and data[label] >= threshold


# ---------------------------------------------------------------------------------------------------------------------
def evaluate_pants_section(detected_items, present_footwear, formal_present_footwear):
    if "pants" in detected_items and detected_items["pants"] > 50:
        if "shorts" in detected_items and detected_items["shorts"] >= 60:
            return "Casual Lower ❌1"
        # elif "jeans" in detected_items and detected_items["jeans"] >= 90:
        #     return "Casual Lower ❌"
        elif "sandal" in detected_items and detected_items["sandal"] <= 50 and "barefoot" in detected_items and detected_items["barefoot"] <= 20 and "sneaker" in detected_items and detected_items["sneaker"] <= 50:
            return "Casual Footwear ❌1"
        elif "boot" in detected_items and detected_items["boot"] <= 70 and "sandal" in detected_items and detected_items["sandal"] <= 60:
            return "Formal Dress ✅"
      
        elif len(formal_present_footwear) >= 3:
            return "Formal Dress ✅"
        elif (("sneaker" in detected_items and detected_items["sneaker"] < 56) or ("sandal" in detected_items and detected_items["sandal"] < 52)) and "shoe" in detected_items and "flip-flop" not in detected_items:
            return "Formal Dress ✅"
        elif "shoe" in detected_items and any(x in detected_items for x in ["boot", "high heel"]):
            return "Formal Dress ✅"
        elif (("sneaker" in detected_items and detected_items["sneaker"] <= 55) or ("sandal" in detected_items and detected_items["sandal"] <= 55)) and "shoe" in detected_items and "flip-flop" in detected_items and detected_items["flip-flop"] <= 50:
            return "Formal Dress ✅"
        elif (("sneaker" in detected_items and detected_items["sneaker"] <= 51) and ("sandal" in detected_items and detected_items["sandal"] <= 51)) and "flip-flop" not in detected_items:
            return "Formal Dress ✅"
        elif any(all(x in detected_items for x in group) for group in [["barefoot", "sandal", "riding boot"], ["clogs", "sandal", "running shoe"], ["flip-flop", "sandal", "riding boot"]]):
            return "Casual Footwear ❌2"
        elif len(present_footwear) >= 3:
            return "Casual Footwear ❌3"
        elif "shoe" not in detected_items:
            return "Casual Footwear ❌4"
        else:
            return "Casual Footwear ❌5" 
    elif detected_items == ["pants"] or set(detected_items) == {"pants"}:
        if "shoe" in detected_items and any(x in detected_items for x in ["boot", "cowboy boot", "high heel"]):
            return "Formal Dress ✅"
        else:
            return "Casual Lower ❌2"   
    else:
        return "Casual Lower ❌3"


def get_attire_result(detected_items):
    footwear_items = {"sneaker", "sandal", "flip-flop", "barefoot", "running shoe"}
    formal_footwear_items = {"shoe", "boot", "high heel", "cowboy boot"}
    present_footwear = [item for item in footwear_items if item in detected_items]
    formal_present_footwear = [item for item in formal_footwear_items if item in detected_items]

    if "female" in detected_items and detected_items["female"] > 80 and (
        ("woman" in detected_items and detected_items["woman"] > 80) or
        ("girl" in detected_items and detected_items["girl"] > 80)
    ):
        return "Formal Dress ✅"

    elif "t-shirt" in detected_items and "shirt" in detected_items and detected_items["t-shirt"] > detected_items["shirt"]:
        if (
            "polo" in detected_items or "collar" in detected_items or
            ("sleeve" in detected_items and detected_items["sleeve"] > 48 and (
                "long sleeve" not in detected_items or detected_items.get("long sleeve", 0) > 45))
        ) and "jersey" not in detected_items:
            return evaluate_pants_section(detected_items, present_footwear, formal_present_footwear)
        else:
            return "Casual Upper ❌"

    elif "t-shirt" in detected_items and "shirt" not in detected_items:
        return "Casual Upper ❌"

    else:
        if (
            ("formal wear" in detected_items and detected_items["formal wear"] >= 48.55) or
            ("shirt" in detected_items and detected_items["shirt"] >= 49)
        ):
            return evaluate_pants_section(detected_items, present_footwear, formal_present_footwear)

        elif any(x in detected_items for x in ["shorts", "vest", "t-shirt", "undershirt"]):
            return "Casual Upper❌"
        elif "t-shirt" in detected_items and detected_items["t-shirt"] > 50:
            return "Casual Upper❌"
       
        else:
            return "Casual Upper ❌"



  
# --------------------------------------------------------------------------------------------------------------------

def display_items(formal_items, casual_items, category_icon, category_name):
    st.markdown(
        f"<h3 style='color:#6c5ce7;'>{category_icon} {category_name}</h3>", 
        unsafe_allow_html=True
    )
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


st.markdown("<h2 style='color:#6c5ce7;'>📂 Upload Images for Attire Detection</h2>", unsafe_allow_html=True)

uploaded_files = st.file_uploader("Upload images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files:
    os.makedirs("uploads", exist_ok=True)

    for uploaded_file in uploaded_files:
        image_path = os.path.join("uploads", uploaded_file.name)
        with open(image_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.image(image_path, caption=f"📸 Uploaded Image: {uploaded_file.name}", width=500)

        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()

        response = rekognition.detect_labels(Image={"Bytes": image_bytes}, MaxLabels=100, MinConfidence=0.1)
        detected_items = {label["Name"].lower(): label["Confidence"] for label in response.get("Labels", [])}

        upper_items = {item: conf for item, conf in detected_items.items() if item in UPPER_CLOTHING}
        lower_items = {item: conf for item, conf in detected_items.items() if item in LOWER_CLOTHING}
        foot_items = {item: conf for item, conf in detected_items.items() if item in FOOTWEAR}

        formal_upper_items = {item: conf for item, conf in upper_items.items() if item in formal_upper}
        casual_upper_items = {item: conf for item, conf in upper_items.items() if
                              item in casual_upper or item not in formal_upper}

        formal_lower_items = {item: conf for item, conf in lower_items.items() if item in formal_lower}
        casual_lower_items = {item: conf for item, conf in lower_items.items() if
                              item in casual_lower or item not in formal_lower}

        formal_foot_items = {item: conf for item, conf in foot_items.items() if item in formal_foot}
        casual_foot_items = {item: conf for item, conf in foot_items.items() if
                             item in casual_foot or item not in formal_foot}

        col1, col2, col3 = st.columns(3)
        with col1:
            display_items(formal_upper_items, casual_upper_items, "👕", "Upper")
        with col2:
            display_items(formal_lower_items, casual_lower_items, "👖", "Lower")
        with col3:
            display_items(formal_foot_items, casual_foot_items, "👟", "Footwear")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h3 style='color:#0984e3;'>🧠 Final Attire Analysis</h3>", unsafe_allow_html=True)

        final_result = get_attire_result(detected_items)

        if final_result and final_result.startswith("✅"):
            st.markdown(f"<div style='background-color:#dff9fb;padding:15px;border-radius:10px;border-left:6px solid #00b894;'><strong style='color:#00b894;'>{final_result}</strong></div>", unsafe_allow_html=True)

        elif final_result and final_result.startswith("❌"):
            st.markdown(f"<div style='background-color:#ffeaa7;padding:15px;border-radius:10px;border-left:6px solid #d63031;'><strong style='color:#d63031;'>{final_result}</strong></div>", unsafe_allow_html=True)

        else:
            st.markdown(f"<div style='background-color:#dfe6e9;padding:15px;border-radius:10px;border-left:6px solid #fdcb6e;'><strong style='color:#2d3436;'>{final_result}</strong></div>", unsafe_allow_html=True)

        st.markdown("<hr><center style='color:#b2bec3;'></center>", unsafe_allow_html=True)



