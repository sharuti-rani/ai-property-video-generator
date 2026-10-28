# AI Property Video Generator

A simple web app that turns property details and photos into a short
promotional MP4 video.

The user enters property information, uploads photos, and clicks
**Generate Video**. The app creates captions and a script, arranges the
photos into scenes, optionally adds voice narration, and exports a
video.

## 1. What does this project do?

-   Collects property details such as name, location, price, type,
    features, and contact information.
-   Accepts property photos.
-   Creates a short script and captions using Google Gemini when an API
    key is configured.
-   Uses built-in templates if Gemini is not configured or cannot be
    used.
-   Creates an MP4 video with image movement, text overlays, and
    transitions.
-   Can add voice narration if the user enables it.
-   Lets the user preview and download the generated video.

## 2. What you need before starting

Install these first:

1.  **Python 3.10 or newer**
2.  **FFmpeg** --- MoviePy uses it to create MP4 files.
3.  **VS Code** or another code editor (recommended).

### Install FFmpeg on Windows

If you have `winget`, open PowerShell and run:

``` powershell
winget install Gyan.FFmpeg
```

After installation, close and reopen the terminal. Check that FFmpeg is
available:

``` powershell
ffmpeg -version
```

If Windows says the command is not recognised, FFmpeg may not be
installed correctly or may not be in your PATH.

## 3. Install and run the project

Open the project folder in VS Code. Open **Terminal → New Terminal**,
then run these commands from the project folder.

### Windows PowerShell

``` powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation, you can use Command
Prompt and run:

``` bat
venv\Scripts\activate.bat
```

Then start the app:

``` powershell
python app.py
```

When Flask starts successfully, open this address in your browser:

**http://127.0.0.1:5000/**

Keep the terminal open while using the app. To stop the server, press
`Ctrl + C` in the terminal.

> **Important:** Open the app through the Flask address above. Do not
> open `templates/index.html` directly or use VS Code Live Server on
> port `5500`; the form needs to send requests to the Flask backend.

## 4. How to use the app

1.  Open **http://127.0.0.1:5000/**.
2.  Enter the property details. Add only information you know is
    correct.
3.  Upload property photos. The project guide recommends 4--8 images.
4.  Choose whether to include voice narration.
5.  Click **Generate Video** and wait for processing to finish.
6.  Preview the result and download the MP4.

For a quick test, use **Load Sample Data** and create sample images if
needed:

``` powershell
python generate_samples.py
```

The generated sample images should be placed in `sample_data/images/`.
If sample data does not load or images are missing, check the project
folders and the terminal for errors.

## 5. Gemini API key: what is it, and do you need one?

The Gemini API key lets the app send the property details to Google's
Gemini model so it can write a more natural promotional script and scene
captions.

**You only need this key for Gemini-powered script generation.**
According to the project design, the app can use its built-in
template-based script generator when no Gemini key is configured. The
API key is not what creates the MP4 itself; the video is assembled by
the project's video-generation code.

  -----------------------------------------------------------------------
  Without a Gemini API key            With a Gemini API key
  ----------------------------------- -----------------------------------
  Uses the built-in script templates  Can ask Gemini to create a more
                                      natural script

  No Gemini API key is needed         Requires a valid key and internet
                                      access

  Video generation can still work,    Gemini may improve the wording, but
  subject to the other dependencies   video generation still depends on
                                      the local app and its dependencies
  -----------------------------------------------------------------------

The project README identifies the Gemini model as `gemini-2.0-flash`.
The actual model and API integration are configured in the source code,
so check `script_generator.py` and `config.py` if the model name or
setup has changed.

### How to get a Gemini API key

1.  Visit [Google AI Studio -- API
    keys](https://aistudio.google.com/apikey).
2.  Sign in with your Google account.
3.  Create an API key, following Google's instructions.
4.  Keep the key private. Do not post it in a public repository or share
    it in screenshots.

### How to add the key on Windows

In the same PowerShell terminal that you will use to start the app, run:

``` powershell
$env:GEMINI_API_KEY = "PASTE_YOUR_API_KEY_HERE"
python app.py
```

Replace `PASTE_YOUR_API_KEY_HERE` with your real key. Keep the key
inside the quotation marks. This sets the key for that terminal session;
if you open a new terminal, set it again.

For macOS or Linux, use:

``` bash
export GEMINI_API_KEY="PASTE_YOUR_API_KEY_HERE"
python app.py
```

The application must read the key from the `GEMINI_API_KEY` environment
variable for this method to work. If Gemini is not being used even after
setting the key, check how `script_generator.py` reads the key and look
for error messages in the terminal.

### Keep the API key safe

-   Never paste your real key into `app.py`, `script_generator.py`,
    `README.md`, or frontend JavaScript.
-   Never commit your API key to GitHub.
-   If you accidentally publish a key, revoke it and create a new one in
    Google AI Studio.
-   API usage may be subject to Google's quotas, availability, and
    pricing terms. Check Google's current terms before relying on it.

## 6. Project folder guide

``` text
AI VID GEN/
├── app.py                    # Starts Flask and handles web requests
├── config.py                 # Application settings
├── script_generator.py       # Gemini script generation and template fallback
├── video_generator.py        # Builds the MP4 video
├── generate_samples.py       # Creates sample images for testing
├── requirements.txt          # Python package dependencies
├── README.md                 # This guide
├── templates/
│   └── index.html            # Web form and browser-side JavaScript
├── sample_data/
│   ├── sample_property.json  # Example property details
│   └── images/               # Sample property images
├── uploads/                  # Uploaded images (created/used by the app)
├── output/                   # Generated MP4 files
└── assets/                   # Optional assets such as background music or fonts
```

Some folders may be created automatically when the app runs. If a folder
is absent, check the code before creating or deleting anything.

## 7. Main technologies

-   **Python** --- application logic
-   **Flask** --- local web server and API routes
-   **HTML, CSS, JavaScript** --- web interface
-   **Google Gemini API (optional)** --- generates the script and
    captions
-   **MoviePy and FFmpeg** --- compose and export the MP4 video
-   **Pillow** --- draws readable text on images
-   **gTTS (optional narration)** --- converts script text into speech
    and requires internet access

Install Python packages using `pip install -r requirements.txt`.

## 8. Common problems

### The page opens, but Generate Video fails with a JSON error

1.  Make sure you started the app with `python app.py`.
2.  Open **http://127.0.0.1:5000/**, not the Live Server address on port
    `5500`.
3.  Click Generate Video again.
4.  Check the terminal running Flask. Python errors shown there often
    explain the real cause.
5.  If it still fails, inspect the browser's Developer Tools → Console
    and Network tabs, and check the response from `/api/generate`.

A message such as `Unexpected end of JSON input` means the browser
expected JSON but received an empty or invalid response. It is a
symptom, not the underlying cause by itself.

### `ModuleNotFoundError`

Make sure the virtual environment is activated and install dependencies
again:

``` powershell
pip install -r requirements.txt
```

### FFmpeg error or MP4 export fails

Check that FFmpeg is installed and available:

``` powershell
ffmpeg -version
```

Restart the terminal after installing FFmpeg.

### Gemini errors

-   Check that `GEMINI_API_KEY` is set in the same terminal before
    starting Flask.
-   Confirm the key is valid and has access to the model configured by
    the project.
-   Check the terminal for quota, network, authentication, or model-name
    errors.
-   Try the template fallback if Gemini is not essential.

### Narration does not work

The README describes gTTS as an internet-based service. Check your
internet connection, or turn off narration and try again.

## 9. Files to check when making changes

-   Change form fields or page layout: `templates/index.html`
-   Change backend request handling: `app.py`
-   Change Gemini prompts or fallback scripts: `script_generator.py`
-   Change video scenes, text, transitions, or export:
    `video_generator.py`
-   Change application settings: `config.py`
-   Add or update Python dependencies: `requirements.txt`



## License

The original project README specifies the MIT License. If distributing
the project, include the appropriate `LICENSE` file if one is present or
required.
