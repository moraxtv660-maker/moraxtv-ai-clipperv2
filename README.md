# Moraxtv AI Clipper 2.0 — Streamlit Edition

This version runs as a website on Streamlit Community Cloud. You do **not** need to install Python locally. GitHub stores the project; Streamlit Cloud builds and hosts it.

## Files
- `app.py` — Streamlit website and video processing pipeline
- `requirements.txt` — packages installed by Streamlit Cloud
- `.streamlit/config.toml` — app theme and upload configuration

## Deploy using only your phone/browser

### 1. Create a GitHub repository
1. Open https://github.com and sign in or create an account.
2. Tap **New repository**.
3. Name it `moraxtv-ai-clipper`.
4. Set it to **Public** (simplest for Streamlit Community Cloud) or Private if your Streamlit plan supports it.
5. Create the repository.

### 2. Upload the project files
1. Open the new repository.
2. Choose **Add file → Upload files**.
3. Upload `app.py`, `requirements.txt`, and the `.streamlit` folder (containing `config.toml`).
4. Commit the changes.

### 3. Deploy on Streamlit Cloud
1. Open https://share.streamlit.io/
2. Sign in with GitHub and authorize access.
3. Select **Create app**.
4. Choose repository `moraxtv-ai-clipper`, branch `main`, and main file path `app.py`.
5. Press **Deploy**.
6. Wait for the build to finish. Streamlit will provide a public website URL.

## How to use
- Open your deployed website.
- Select Upload video or YouTube link.
- Choose clip length and number of clips.
- Press Detect Viral Moments.
- Preview and download individual clips or all clips as a ZIP.

## Important platform limits and notes
- Streamlit Community Cloud has resource, memory, execution-time and upload limits. Large/long videos may fail or run out of memory. Start with short, modest-resolution videos.
- The app currently holds generated clips in the Streamlit session. Refreshing or losing the session clears them.
- YouTube URL import uses `yt-dlp`. YouTube may block downloads or restrict particular videos. Use it only for videos you own or are authorized to download/process, and comply with YouTube's Terms of Service and applicable copyright rules. This app does not bypass DRM, paywalls, login restrictions or access controls.
- This is a heuristic activity detector: audio energy (45%), frame motion (40%) and scene-change signal (15%). It does not understand game semantics and cannot promise viral results or reliably detect kills/headshots/funny moments.
- Public deployment should add user authentication, quotas, storage cleanup, abuse controls and background job processing before being opened to unrestricted traffic.

## Troubleshooting
- If the app fails to build, open **Manage app → Logs** in Streamlit Cloud and check the package error.
- If video processing fails, try a shorter MP4 at 720p or lower.
- If YouTube import fails, test with a video you own and that is publicly accessible. Some YouTube videos are not downloadable through third-party tools.
