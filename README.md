# Jarvis

A local AI assistant built with Python, Tkinter, Ollama, and support for flexible AI models and providers.

Jarvis runs locally on your computer and provides a desktop chat interface with conversation memory, configurable AI providers, and local settings.

## Version

**v0.1.0**

This is the first public release of Jarvis.

## Features

* Local AI chat
* Flexible AI model support
* Ollama integration
* OpenAI-compatible provider support
* Configurable AI model
* Configurable API endpoint
* Configurable API key
* AI connection testing
* Conversation history
* Recent interactions sidebar
* Automatic conversation titles
* Inline conversation renaming
* Conversation deletion with confirmation
* New chat system
* Local memory
* Automatic safe-memory storage
* Private-memory confirmation
* Basic sensitive-information protection
* Markdown-style bold text
* OLED-style dark interface
* In-app settings panel
* Enter to send messages
* `Shift + Enter` for new lines
* `Ctrl + Enter` to send
* Automatic chat scrolling
* Command system

## AI Providers

Jarvis is designed to avoid being locked to a single AI model or provider.

The default configuration uses Ollama:

```text
Provider: Ollama
Model: qwen2.5-coder:7b
Base URL: http://localhost:11434/v1
