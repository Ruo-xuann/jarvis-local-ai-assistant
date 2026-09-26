# Jarvis

A local AI assistant built with Python, Tkinter, Ollama, and Qwen.

Jarvis runs locally on your computer and connects to Ollama for AI responses. Conversation memory is stored locally on the user's machine.

## Version

**v0.1.0**

This is the first public release of Jarvis.

## Features

* Local AI chat
* Ollama integration
* Qwen 2.5 Coder 7B support
* Conversation history
* Local memory
* Automatic safe-memory storage
* Private-memory confirmation
* Basic sensitive-information protection
* Markdown-style bold text
* OLED-style dark interface
* Command system

## Requirements

### For the compiled Windows release

* Windows 10 or newer
* Ollama
* Qwen 2.5 Coder 7B
* Internet connection for the initial Ollama/model download

Python is **not required** to run the compiled `Jarvis.exe`.

### For running from source

* Python 3
* Ollama
* Qwen 2.5 Coder 7B
* Python package listed in `requirements.txt`

## Ollama Setup

Install Ollama from:

https://ollama.com/

After installing Ollama, open PowerShell and download the model:

```powershell
ollama pull qwen2.5-coder:7b
```

Verify that the model is installed:

```powershell
ollama list
```

You should see:

```text
qwen2.5-coder:7b
```

Jarvis connects to the local Ollama API at:

```text
http://localhost:11434
```

## Running the Release

Download the latest release from the GitHub Releases section.

For **v0.1.0**, download:

```text
Jarvis-v0.1.0.zip
```

Extract the ZIP and open the folder:

```text
Jarvis-v0.1.0/
├── Jarvis.exe
├── README.txt
├── SETUP.txt
└── requirements.txt
```

Make sure Ollama is installed and the Qwen model has been downloaded.

Then run:

```text
Jarvis.exe
```

## Running From Source

Clone the repository:

```powershell
git clone https://github.com/Ruo-xuann/qwen-local-assistant.git
```

Enter the project:

```powershell
cd qwen-local-assistant
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the Python dependency:

```powershell
pip install -r requirements.txt
```

Make sure Ollama is running and the model is installed:

```powershell
ollama pull qwen2.5-coder:7b
```

Run Jarvis:

```powershell
python gui.py
```

## Commands

Jarvis supports the following commands:

| Command   | Description                    |
| --------- | ------------------------------ |
| `/help`   | Show available commands        |
| `/memory` | Show saved memory              |
| `/clear`  | Clear the current conversation |
| `/forget` | Delete saved memory            |
| `/exit`   | Exit Jarvis                    |
| `/quit`   | Exit Jarvis                    |

## Memory

Jarvis can save useful information as memory.

Memory is stored locally in:

```text
memory.json
```

`memory.json` is intentionally excluded from Git using `.gitignore`.

Some potentially private information requires confirmation before being saved.

Sensitive information such as passwords, API keys, tokens, and similar credentials is blocked from memory storage.

## Project Structure

```text
qwen-local-assistant/
├── .gitignore
├── gui.py
├── main.py
├── requirements.txt
└── README.md
```

Generated files and local data such as the following are excluded from Git:

```text
.venv/
memory.json
__pycache__/
build/
dist/
*.spec
Jarvis-v0.1.0/
```

## Release

### v0.1.0

Initial public release.

The compiled Windows release is available through the GitHub Releases page.

The AI model is **not bundled** with Jarvis. Users must install Ollama and download the required model separately.

## License

This project is currently provided for personal and educational use.

## Status

Jarvis is an early-stage project.

Future versions may add additional AI model support, improved configuration, expanded security features, and further UI improvements.
