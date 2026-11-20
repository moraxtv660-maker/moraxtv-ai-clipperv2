import io
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np
import streamlit as st
import yt_dlp

# Install Deno for YouTube support
deno_dir = Path.home() / ".deno"
deno_bin = deno_dir / "bin"
deno_path = deno_bin / "deno"

if not deno_path.exists():
    deno_dir.mkdir(parents=True, exist_ok=True)
    deno_env = os.environ.copy()
    deno_env["DENO_INSTALL"] = str(deno_dir)

    subprocess.run(
        ["sh", "-c", "curl -fsSL https://deno.land/install.sh | sh"],
        check=True,
        env=deno_env,
    )

os.environ["PATH"] = str(deno_bin) + os.pathsep + os.environ.get("PATH", "")
# PO Token Provider setup
pot_dir = Path("/tmp/bgutil-ytdlp-pot-provider")

if not (pot_dir / "server" / "node_modules").exists():
    if not pot_dir.exists():
        subprocess.run(
            [
                "git", "clone",
                "--single-branch",
                "--branch", "2.0.2",
                "https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git",
                str(pot_dir),
            ],
            check=True,
        )

    subprocess.run(
        ["deno", "install", "--allow-scripts=npm:canvas", "--frozen"],
        cwd=pot_dir / "server",
        check=True,
    )
st.set_page_config(
    page_title="Moraxtv AI Clipper 2.0",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Inter:wght@400;600;700;800;900&display=swap');
.stApp {background: radial-gradient(ellipse at 15% 0%, #21163d 0%, #0a0b14 42%, #080910 100%); color:#f5f6ff;}
.block-container {max-width: 1050px; padding-top: 2rem; padding-bottom: 3rem;}
h1,h2,h3,p,div,span,label {font-family: Inter, sans-serif;}
.hero {text-align:center; padding: 2.2rem 0 1.6rem;}
.kicker {color:#65e6ef; font:11px 'DM Mono',monospace; letter-spacing:2px;}
.hero h1 {font-size: clamp(2.5rem,7vw,4.6rem); line-height:.98; font-weight:900; letter-spacing:-3px; margin:.8rem 0;}
.gradient {background:linear-gradient(90deg,#b9a3ff,#70e4eb);-webkit-background-clip:text;background-clip:text;color:transparent;}
.sub {color:#a3a7ba;font-size:1rem;}
.panel {background:linear-gradient(145deg,rgba(23,25,43,.96),rgba(13,15,26,.97)); border:1px solid #292d43; border-radius:18px; padding:1.3rem; margin: .7rem 0 1rem;}
div.stButton > button, div.stDownloadButton > button {border:0; border-radius:10px; font-weight:800; min-height:2.8rem;}
div.stButton > button[kind="primary"] {background:linear-gradient(100deg,#9a7af1,#54d5df); color:#080a12;}
div[data-testid="stFileUploader"] {background:#111321;border:1px dashed #575078;border-radius:12px;padding:1rem;}
.small-note {font-size:.8rem;color:#9b9fb1;line-height:1.55;}
.metric-card {background:#0b0d18;border:1px solid #25283a;border-radius:12px;padding:1rem;}
footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
 <div class="kicker">YOUR GAMEPLAY. THE BEST MOMENTS.</div>
 <h1>MORAXTV AI CLIPPER<br><span class="gradient">VERSION 2.0</span></h1>
 <div class="sub">MAKE EVERY MOMENT COUNT. · VIRAL MOMENTS EDITION</div>
</div>
""", unsafe_allow_html=True)

def ffmpeg():
    return imageio_ffmpeg.get_ffmpeg_exe()

def get_duration(video_path):
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    if fps <= 0 or frames <= 0:
        raise RuntimeError("Could not read video duration or frames.")
    return frames / fps

def extract_audio_energy(video_path, duration):
    ff = ffmpeg()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name
    try:
        cmd = [ff, "-y", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "8000",
               "-t", str(duration), "-f", "wav", wav_path]
        run = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if run.returncode != 0:
            return np.zeros(max(1, int(duration)), dtype=np.float32)
        import wave
        with wave.open(wav_path, "rb") as wf:
            samples = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        return np.array([
            np.sqrt(np.mean(samples[i:i+8000] ** 2)) if len(samples[i:i+8000]) else 0
            for i in range(0, len(samples), 8000)
        ], dtype=np.float32)
    finally:
        try: os.remove(wav_path)
        except OSError: pass

def visual_signals(video_path, duration):
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    step = max(1, int(fps / 2))
    times, motion, cuts = [], [], []
    previous = None
    frame_index = 0
    while True:
        ok, frame = cap.read()
        if not ok: break
        if frame_index % step == 0:
            small = cv2.resize(frame, (160, 90))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            if previous is not None:
                diff = cv2.absdiff(gray, previous)
                times.append(frame_index / fps)
                motion.append(float(np.mean(diff) / 255))
                cuts.append(float(np.mean(diff > 45)))
            previous = gray
        frame_index += 1
    cap.release()
    return np.asarray(times), np.asarray(motion), np.asarray(cuts)

def normalize(values):
    if len(values) == 0: return values
    low, high = np.percentile(values, 10), np.percentile(values, 95)
    return np.clip((values-low)/(high-low+1e-8), 0, 1)

def make_clips(video_path, output_dir, clip_seconds, max_clips):
    duration = get_duration(video_path)
    if duration < 3: raise RuntimeError("The video is too short.")
    audio = extract_audio_energy(video_path, duration)
    times, motion, cuts = visual_signals(video_path, duration)
    if len(times) == 0: raise RuntimeError("Could not analyze video frames.")

    seconds = np.arange(max(1, int(duration)), dtype=float)
    a = np.array([audio[min(int(s), len(audio)-1)] if len(audio) else 0 for s in seconds])
    m = np.interp(seconds, times, motion, left=0, right=0)
    c = np.interp(seconds, times, cuts, left=0, right=0)
    score = .45*normalize(a) + .40*normalize(m) + .15*normalize(c)
    if len(score) >= 3: score = np.convolve(score, np.ones(3)/3, mode="same")

    half = clip_seconds / 2
    candidates = []
    last_center = int(max(half, duration-half))
    for center in range(int(half), last_center + 1, 2):
        start = max(0, min(duration-clip_seconds, center-half))
        left, right = int(start), min(len(score), max(int(start)+1, int(np.ceil(start+clip_seconds))))
        if right > left:
            candidates.append((float(np.mean(score[left:right])), start))
    candidates.sort(reverse=True)
    selected = []
    for val, start in candidates:
        if all(abs(start-old_start) >= clip_seconds*.75 for _,old_start in selected):
            selected.append((val,start))
        if len(selected) >= max_clips: break

    outputs = []
    for idx,(val,start) in enumerate(sorted(selected,key=lambda x:x[1]),1):
        target = output_dir / f"moraxtv_clip_{idx}.mp4"
        cmd = [ffmpeg(), "-y", "-ss", f"{start:.3f}", "-i", str(video_path),
               "-t", str(min(clip_seconds,duration-start)), "-map", "0:v:0", "-map", "0:a?",
               "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
               "-c:a", "aac", "-movflags", "+faststart", str(target)]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
        if proc.returncode != 0:
            raise RuntimeError("FFmpeg could not cut a clip: " + proc.stderr.decode(errors="ignore")[-700:])
        outputs.append({"path":target,"score":val*100,"start":start,
                        "duration":min(clip_seconds,duration-start)})
    return outputs

def download_youtube(url, folder):
    if not re.match(r"^https?://(www\.)?(youtube\.com|youtu\.be)/", url.strip(), re.I):
        raise ValueError("Please paste a valid YouTube URL.")
    outtmpl = str(folder / "youtube_source.%(ext)s")
    opts = {
    "format": "best",
    
"extractor_args": {
    "youtube": {
        "player_client": ["web_safari"]
    },
    "youtubepot-bgutilscript": {
        "server_home": [str(pot_dir / "server")]
    }
},        
    "outtmpl": outtmpl,
    "noplaylist": True,
    "max_filesize": 200 * 1024 * 1024,
    "quiet": True,
    "no_warnings": True,
    "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url.strip()])
    found = [p for p in folder.glob("youtube_source.*") if p.is_file()]
    if not found: raise RuntimeError("YouTube did not provide a downloadable video.")
    return found[0]

def zip_clips(clips):
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in clips:
            zf.write(item["path"], item["path"].name)
    mem.seek(0)
    return mem.getvalue()

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown("### 01 / VIDEO SOURCE")
source_tab, youtube_tab = st.tabs(["📤 Upload video", "▶ YouTube link"])
with source_tab:
    uploaded = st.file_uploader("Choose gameplay video", type=["mp4","mov","mkv","webm","avi","m4v"],
                               help="Streamlit Cloud upload limits apply. Keep files reasonably small.")
with youtube_tab:
    youtube_url = st.text_input("YouTube video URL", placeholder="https://www.youtube.com/watch?v=...")
    st.markdown('<div class="small-note">Only process videos you own or have permission to download. Availability depends on YouTube restrictions and regional access.</div>', unsafe_allow_html=True)

c1,c2 = st.columns(2)
with c1: clip_length = st.selectbox("CLIP LENGTH", [15,30,45,60], index=1, format_func=lambda x:f"{x} seconds")
with c2: max_clips = st.selectbox("NUMBER OF CLIPS", [3,5,8,10], index=1)
process = st.button("✦  DETECT VIRAL MOMENTS", type="primary", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown("### 02 / VIRAL MOMENT DETECTOR")
cols = st.columns(4)
for col, symbol, title, detail in [
    (cols[0],"♫","Audio peaks","Loudness & excitement"),
    (cols[1],"◈","Gameplay motion","Fast visual movement"),
    (cols[2],"▧","Scene changes","Sudden visual transitions"),
    (cols[3],"✧","Highlight ranking","Combined signal score"),
]:
    with col:
        st.markdown(f'<div class="metric-card"><div style="font-size:1.5rem;color:#65e6ef">{symbol}</div><b>{title}</b><div class="small-note">{detail}</div></div>',unsafe_allow_html=True)
st.markdown('<p class="small-note">Honest AI note: this detector ranks potentially exciting sections using audio and visual activity. It does not truly understand game events, so it cannot reliably identify kills, headshots, wins or jokes. A high score is not a guarantee of virality.</p>',unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

if process:
    if not uploaded and not youtube_url.strip():
        st.error("Upload a gameplay video or paste a YouTube URL.")
    else:
        try:
            with st.spinner("Preparing your video and scanning for exciting moments..."):
                with tempfile.TemporaryDirectory() as temp:
                    work = Path(temp)
                    if uploaded:
                        source = work / (Path(uploaded.name).name or "gameplay.mp4")
                        source.write_bytes(uploaded.getvalue())
                    else:
                        source = download_youtube(youtube_url, work)
                    output_dir = work / "clips"
                    output_dir.mkdir()
                    results = make_clips(source, output_dir, clip_length, max_clips)
                    # Keep results in session state as bytes so temp files can be cleaned safely.
                    st.session_state["moraxtv_results"] = [
                        {"name":r["path"].name,"data":r["path"].read_bytes(),
                         "score":r["score"],"start":r["start"],"duration":r["duration"]}
                        for r in results
                    ]
            st.success(f"Generated {len(st.session_state['moraxtv_results'])} clips.")
        except Exception as exc:
            st.error(f"Could not process this video: {exc}")

if st.session_state.get("moraxtv_results"):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("### 03 / YOUR HIGHLIGHTS")
    clips = st.session_state["moraxtv_results"]
    zip_mem = io.BytesIO()
    with zipfile.ZipFile(zip_mem,"w",zipfile.ZIP_DEFLATED) as zf:
        for clip in clips: zf.writestr(clip["name"],clip["data"])
    st.download_button("⬇  DOWNLOAD ALL CLIPS (ZIP)",zip_mem.getvalue(),
                       file_name="moraxtv-highlights.zip",mime="application/zip",
                       type="primary",use_container_width=True)
    for i,clip in enumerate(clips,1):
        st.markdown(f"**Highlight {i}** · Signal score: {clip['score']:.1f}%")
        st.caption(f"Starts at {clip['start']:.1f}s · Duration {clip['duration']:.1f}s")
        st.video(clip["data"])
        st.download_button(f"Download clip {i}",clip["data"],file_name=clip["name"],
                           mime="video/mp4",key=f"download_{i}")
    st.markdown('</div>',unsafe_allow_html=True)

st.markdown('<div style="text-align:center;color:#777d91;font:10px monospace;letter-spacing:1px;padding:1rem">MORAXTV AI CLIPPER 2.0 · BUILT FOR THE MOMENTS THAT MATTER</div>',unsafe_allow_html=True)
