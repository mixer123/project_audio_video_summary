
import os
import streamlit as st
from pathlib import Path
from dotenv import dotenv_values
from openai import OpenAI
import textwrap
from pydub import AudioSegment
import karaoke_utils

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

def get_openai_client():
    path = Path('dot_env')
    env = dotenv_values(path / ".env")
    return OpenAI(api_key=env["OPEN_AI_KEY"])


def transcribe_mp4_bytes(file: bytes, filename: str):
    if len(file) > MAX_FILE_SIZE:
        st.error("❌ Plik przekracza limit 25 MB (API Whisper).")
        return

    try:
        client = get_openai_client()
        with open("temp_video.mp4", "wb") as temp:
            temp.write(file)

        with open("temp_video.mp4", "rb") as f:
            transcript = client.audio.transcriptions.create(
                file=f,
                model="whisper-1"
            )

        st.markdown("### 📄 Transkrypcja:")
        st.markdown(transcript.text)

        save_path = Path("transcription") / f"{Path(filename).stem}.txt"
        wrapped_text = textwrap.fill(transcript.text, width=80)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(wrapped_text)
        st.success(f"Notatka zapisana jako: {save_path.name}")
    except Exception as e:
        st.error(f"Błąd podczas transkrypcji: {e}")


def transcribe_and_save(file_path, filename, show_karaoke_mode=False):
    try:
        client = get_openai_client()
        with open(file_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                file=f,
                model="whisper-1",
                response_format="verbose_json"
            )

        text = transcript.text
        segments = transcript.segments
        karaoke_lines = [(seg.start, seg.end, seg.text) for seg in segments]

        # Zapisz tekst
        wrapped_text = textwrap.fill(text, width=80)
        save_path = Path("transcription") / f"{Path(filename).stem}.txt"
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(wrapped_text)

        # Pokazuj
        if show_karaoke_mode:
            from karaoke_utils import show_karaoke
            show_karaoke(karaoke_lines, file_path)
        else:
            st.markdown("### 📄 Transkrypcja:")
            st.markdown(wrapped_text)

        st.success(f"Notatka zapisana jako: {save_path.name}")
    except Exception as e:
        st.error(f"Błąd podczas transkrypcji: {e}")



# === Konfiguracja strony ===
st.set_page_config(page_title="Transcript MP3 and MP4", layout="centered")
st.title("🎶 Transcript MP3 and MP4")

# === Zakładki ===
tab_names = ["Upload MP3/MP4", "Lista MP3", "Lista MP4", "Lista transkrypcji"]
if "active_tab" not in st.session_state:
    st.session_state.active_tab = tab_names[0]

with st.sidebar:
    selected_tab = st.radio("Wybierz zakładkę:", tab_names, index=tab_names.index(st.session_state.active_tab))

# === Katalogi ===
save_dir_mp3 = "uploads_mp3"
save_dir_mp4 = "uploads_mp4"
save_dir_transcription = "transcription"

os.makedirs(save_dir_mp3, exist_ok=True)
os.makedirs(save_dir_mp4, exist_ok=True)
os.makedirs(save_dir_transcription, exist_ok=True)

# === ZAKŁADKA 1: Upload ===
if selected_tab == tab_names[0]:
    st.session_state.active_tab = tab_names[0]
    st.subheader("📁 Wgraj plik MP3/MP4")
    uploaded_file = st.file_uploader("Wybierz plik MP3/MP4:", type=["mp3", "mp4"])
    if uploaded_file is not None:
        extension = os.path.splitext(uploaded_file.name)[1].lower()
        if extension == '.mp3':
            file_path = os.path.join(save_dir_mp3, uploaded_file.name)
        elif extension == '.mp4':
            file_path = os.path.join(save_dir_mp4, uploaded_file.name)
        else:
            st.error("Nieobsługiwany format pliku.")
            st.stop()

        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())
        st.success(f"✅ Plik zapisano jako: {uploaded_file.name}")
        st.rerun()

# === ZAKŁADKA 2: Lista MP3 ===
elif selected_tab == tab_names[1]:
    st.session_state.active_tab = tab_names[1]
    st.subheader("📂 Lista zapisanych plików MP3")

    try:
        files = [f for f in os.listdir(save_dir_mp3) if f.lower().endswith(".mp3")]
        if not files:
            st.info("Brak plików MP3.")
        else:
            for file in files:
                st.write(f"🔊 **{file}**")
                file_path = os.path.join(save_dir_mp3, file)
                st.audio(file_path)

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"📝 Twórz notatkę: {file}", key=f"note_mp3_{file}"):
                        with st.spinner("⏳ Trwa transkrypcja..."):
                            transcribe_and_save(file_path, file)
                with col2:
                    with st.expander(f"Usuń {file}"):
                         confirm = st.checkbox("Potwierdzam usunięcie pliku", key=f"confirm_del_{file}")
                         if confirm:
                            if st.button("Usuń plik", key=f"confirm_btn_del_{file}"):
                                os.remove(file_path)
                                st.success(f"Usunięto plik: {file}")
                                st.rerun()

                                   
                if st.button(f"🎤 Karaoke: {file}", key=f"karaoke_mp3_{file}"):
                        with st.spinner("⏳ Trwa karaoke..."):
                            transcribe_and_save(file_path, file, show_karaoke_mode=True)

               
    except FileNotFoundError:
        st.warning("Folder uploads_mp3 nie istnieje.")

# === ZAKŁADKA 3: Lista MP4 ===
elif selected_tab == tab_names[2]:
    st.session_state.active_tab = tab_names[2]
    st.subheader("📂 Lista zapisanych plików MP4")

    try:
        files = [f for f in os.listdir(save_dir_mp4) if f.lower().endswith(".mp4")]
        if not files:
            st.info("Brak plików MP4.")
        else:
            for file in files:
                st.write(f"🎥 **{file}**")
                file_path = os.path.join(save_dir_mp4, file)
                st.video(file_path)

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"📝 Twórz notatkę: {file}", key=f"note_mp4_{file}"):
                        with open(file_path, "rb") as f:
                            file_bytes = f.read()
                        if len(file_bytes) <= MAX_FILE_SIZE:
                            with st.spinner("⏳ Trwa transkrypcja..."):
                                transcribe_mp4_bytes(file_bytes, file)
                        else:
                            st.warning("⚠️ Plik MP4 przekracza 25 MB – używam metody bezpośredniej.")
                            with st.spinner("⏳ Trwa transkrypcja..."):
                                transcribe_and_save(file_path, file)
                with col2:
                    if st.button(f"🗑️ Usuń {file}", key=f"del_mp4_{file}"):
                        os.remove(file_path)
                        st.success(f"Usunięto plik: {file}")
                        st.rerun()
    except FileNotFoundError:
        st.warning("Folder uploads_mp4 nie istnieje.")

# === ZAKŁADKA 4: Lista transkrypcji ===
elif selected_tab == tab_names[3]:
    st.session_state.active_tab = tab_names[3]
    st.subheader("📄 Lista transkrypcji tekstowych")

    try:
        files = [f for f in os.listdir(save_dir_transcription) if f.lower().endswith(".txt")]
        if not files:
            st.info("Brak transkrypcji.")
        else:
            for file in files:
                st.write(f"📝 **{file}**")
                file_path = os.path.join(save_dir_transcription, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                with st.expander("Podgląd"):
                    st.text(content)
                if st.download_button("📥 Pobierz", data=content, file_name=file):
                    st.success(f"Pobrano plik: {file}")
    except FileNotFoundError:
        st.warning("Folder transcription nie istnieje.")
