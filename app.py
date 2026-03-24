import streamlit as st
from transformers import pipeline
import pandas as pd
import os
import re
import html
import requests

# 🎤 Voice + Image + Translation
import speech_recognition as sr
from PIL import Image, ImageDraw, ImageFont
from googletrans import Translator

# 🎬 Video libs
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import numpy as np

st.set_page_config(page_title="AI Smart Cooking Assistant", page_icon="🍳", layout="wide")
st.markdown("""
<style>

/* 🔥 MAKE SIDEBAR WIDER */
[data-testid="stSidebar"] {
    min-width: 500px !important;
    max-width: 500px !important;
    background: linear-gradient(180deg, #1b263b, #0d1b2a);
}

/* Remove scroll */
[data-testid="stSidebar"] {
    height: 100vh;
    overflow: hidden !important;
}

/* Container spacing */
[data-testid="stSidebar"] .block-container {
    padding-top: 15px;
    padding-bottom: 10px;
}

/* 🔥 HEADINGS */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-size: 50px;
    font-weight: 1000;
    color: #ffffff;
    letter-spacing: 0.5px;
}

/* 🔥 LABELS */
[data-testid="stSidebar"] label {
    font-size: 30px;
    font-weight: 800;
    color: #e0e1dd;
}

/* 🔥 INPUT FIELDS */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] select {
    font-size: 30px;
    color: white !important;
    background-color: #415a77 !important;
    border-radius: 8px;
    padding: 6px;
}

/* 🔥 PLACEHOLDER TEXT */
::placeholder {
    color: #cbd5e1 !important;
    opacity: 1;
}

/* 🔥 BUTTONS */
[data-testid="stSidebar"] .stButton>button {
    padding: 8px;
    font-size: 40px;
    font-weight: 800;
    background: linear-gradient(135deg, #ffb74d, #ffa726);
    color: black;
    border-radius: 10px;
    border: none;
    transition: 0.3s ease;
}

/* Hover effect */
[data-testid="stSidebar"] .stButton>button:hover {
    transform: scale(1.03);
    background: linear-gradient(135deg, #ffa726, #fb8c00);
}

/* 🔥 CHECKBOX */
[data-testid="stSidebar"] .stCheckbox label {
    font-size: 30px;
    color: #e0e1dd;
}

/* 🔥 COLUMN GAP */
[data-testid="stSidebar"] .stColumns {
    gap: 8px !important;
}

/* 🔥 FILE UPLOADER */
[data-testid="stSidebar"] .stFileUploader {
    background-color: #1b3b5a;
    border-radius: 10px;
    padding: 10px;
}

/* 🔥 DIVIDER */
hr {
    border: 0.5px solid #415a77;
}

</style>
""", unsafe_allow_html=True)
st.title("🍳 AI Smart Cooking Assistant")

translator = Translator()

# ---------- LOAD MODEL ----------
@st.cache_resource
def load_model():
    return pipeline("text2text-generation", model="google/flan-t5-small")

generator = load_model()

@st.cache_resource
def load_image_model():
    return pipeline("image-classification", model="nateraw/food")

# ---------- FUNCTIONS ----------

def get_voice_input():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎤 Speak now...")
        audio = r.listen(source)
    try:
        return r.recognize_google(audio)
    except:
        return ""

def recognize_food(image):
    model = load_image_model()
    try:
        return model(image)[0]['label']
    except:
        return "food"

def translate_text(text, lang):
    try:
        return translator.translate(text, dest=lang).text
    except:
        return text

def filter_allergy(recipe, allergies):
    if not allergies.strip():
        return "✅ No allergy specified"

    found = []
    for item in allergies.split(","):
        item = item.strip().lower()
        if item and item in recipe.lower():
            found.append(item)

    if found:
        return f"⚠️ Contains: {', '.join(found)}"
    return "✅ Safe"

def family_adjustment(recipe, members):
    return recipe + f"\n\n👨‍👩‍👧 Serves: {members} people"

def disease_diet(disease):
    diets = {
        "diabetes": "low sugar, high fiber",
        "bp": "low salt",
        "heart": "low fat",
        "weight loss": "high protein, low carbs"
    }
    return diets.get(disease.lower(), "balanced diet")

def ayurveda_mode():
    return "\n\n🌿 Ayurveda Tip: Use turmeric, cumin, and cook in ghee."

def extract_steps(recipe):
    steps = re.findall(r"\d+\.\s*(.*)", recipe)
    return steps if steps else [recipe]

# ---------- VIDEO CREATION ----------
def create_video(recipe, ingredients_list):
    try:
        steps = extract_steps(recipe)
        clips = []

        for i, step in enumerate(steps):
            # 🎤 Generate audio
            tts = gTTS(step)
            audio_file = f"step_{i}.mp3"
            tts.save(audio_file)
            audio = AudioFileClip(audio_file)

            # 🖼️ Create collage of ingredient images
            imgs = []
            for ing in ingredients_list:
                img_url = f"https://source.unsplash.com/400x300/?{ing}"
                try:
                    img = Image.open(requests.get(img_url, stream=True).raw).convert("RGB")
                    imgs.append(img)
                except:
                    continue

            if not imgs:
                # fallback to blank image
                img = Image.new("RGB", (1280, 720), color=(50, 50, 50))
                imgs = [img]

            # combine horizontally
            widths, heights = zip(*(im.size for im in imgs))
            total_width = sum(widths)
            max_height = max(heights)
            collage = Image.new("RGB", (total_width, max_height))
            x_offset = 0
            for im in imgs:
                collage.paste(im, (x_offset, 0))
                x_offset += im.width

            # overlay step text
            draw = ImageDraw.Draw(collage)
            try:
                font = ImageFont.truetype("arial.ttf", 40)
            except:
                font = ImageFont.load_default()
            draw.text((10, 10), f"Step {i+1}: {step}", fill=(255, 255, 255), font=font)

            frame = np.array(collage)
            clip = ImageClip(frame).set_duration(audio.duration).set_audio(audio)
            clips.append(clip)

        final = concatenate_videoclips(clips)
        final.write_videofile("recipe_video.mp4", fps=24)
        return "recipe_video.mp4"

    except Exception as e:
        st.error(f"Video Error: {e}")
        return None

# ---------- SESSION ----------
if "recipe" not in st.session_state:
    st.session_state.recipe = ""

# ---------- SIDEBAR ----------
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.markdown("---")

    # Row 1 (Cuisine + Mode)
    col1, col2 = st.columns(2)
    with col1:
        cuisine = st.selectbox("Cuisine", ["Indian", "Italian", "Chinese"])
    with col2:
        mode = st.selectbox("Mode", ["Normal", "Disease", "Ayurveda"])

    # Ingredients
    ingredients = st.text_area("Ingredients", height=70)

    # Row 2 (Disease + Allergies)
    col1, col2 = st.columns(2)
    with col1:
        disease = st.text_input("Disease")
    with col2:
        allergies = st.text_input("Allergies")

    # Row 3 (Family + Language)
    col1, col2 = st.columns(2)
    with col1:
        family_size = st.number_input("Family", 1, 10, 1)
    with col2:
        language = st.selectbox("Lang", ["en", "hi", "kn", "ta"])

    # Video toggle
    generate_video = st.checkbox("🎬 Video")

    # Upload
    uploaded_image = st.file_uploader("📸 Image", label_visibility="collapsed")

    # Buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎤 Voice"):
            ingredients = get_voice_input()
    with col2:
        generate = st.button("🚀 Generate")

# ---------- MAIN ----------
st.info("👈 Enter ingredients and click Generate")

if generate:

    # Detect ingredient from image
    if uploaded_image:
        img = Image.open(uploaded_image)
        detected = recognize_food(img)
        ingredients = detected
        st.success(f"Detected: {detected}")

    if not ingredients:
        st.warning("Enter ingredients")
        st.stop()

    ingredients_list = [i.strip() for i in ingredients.split(",") if i.strip()]

    # Build prompt
    prompt = f"""
You are a professional chef.

Create a realistic {cuisine} recipe using: {ingredients}.

Rules:
- Proper recipe name
- Ingredients with quantities
- Cooking time
- 6 clear steps
- No repetition

Format:

Recipe Name:
Ingredients:
Cooking Time:
Instructions:
1.
2.
3.
4.
5.
6.
"""

    if mode == "Disease":
        prompt += f"\nMake it suitable for {disease} diet: {disease_diet(disease)}"

    with st.spinner("🍳 Cooking..."):
        result = generator(prompt, max_length=300, temperature=0.6)

    recipe_text = result[0]['generated_text'].strip()

    # fallback
    if len(recipe_text) < 50 or "Recipe Name" not in recipe_text:
        recipe_text = f"""
Recipe Name: Simple {ingredients} Curry

Ingredients:
- {ingredients}
- 2 tbsp oil
- 1 onion
- 1 tomato
- spices

Cooking Time: 20 minutes

Instructions:
1. Heat oil.
2. Add onion and cook.
3. Add tomato and spices.
4. Add {ingredients}.
5. Cook well.
6. Serve hot.
"""

    if mode == "Ayurveda":
        recipe_text += ayurveda_mode()

    recipe_text = family_adjustment(recipe_text, family_size)
    recipe_text = translate_text(recipe_text, language)

    st.session_state.recipe = recipe_text

# ---------- DISPLAY ----------
if st.session_state.recipe:

    st.success("✅ Recipe Ready!")

    safe_text = html.escape(st.session_state.recipe)
    st.markdown(f"""
    <div style="background-color:#1e1e1e;padding:20px;border-radius:10px">
    <pre>{safe_text}</pre>
    </div>
    """, unsafe_allow_html=True)

    st.write(filter_allergy(st.session_state.recipe, allergies))

    # Show ingredient images grid
    cols = st.columns(len(ingredients_list))
    for i, ing in enumerate(ingredients_list):
        cols[i].image(f"https://source.unsplash.com/400x300/?{ing}", caption=ing)

    # Generate video
    if generate_video:
        with st.spinner("🎬 Creating video..."):
            vid = create_video(st.session_state.recipe, ingredients_list)
        if vid:
            st.video(vid)

    # SAVE recipe
    df = pd.DataFrame({
        "Ingredients":[ingredients],
        "Recipe":[st.session_state.recipe]
    })

    if os.path.exists("recipes.csv"):
        old = pd.read_csv("recipes.csv")
        df = pd.concat([old, df], ignore_index=True)

    df.to_csv("recipes.csv", index=False)