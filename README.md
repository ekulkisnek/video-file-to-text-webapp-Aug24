
# Audio/Video Transcription Web App

A Flask-based web application that transcribes audio and video files using OpenAI's Whisper model.

## Features

- Upload and transcribe audio/video files
- Real-time transcription progress tracking
- Copy transcripts to clipboard
- Save transcripts as text files
- Support for multiple file formats
- Chunk-based processing for large files
- Reverse chronological logging

## Requirements

- Python 3.10+
- OpenAI Whisper
- Flask
- PyDub
- ffmpeg (for audio processing)

## Setup

1. Fork this template on Replit
2. The dependencies will be automatically installed via Poetry
3. Click Run to start the application
4. Open the web interface in your browser

## Usage

1. Access the web interface
2. Click "Choose File" to select an audio/video file
3. Click "Upload and Transcribe" to start transcription
4. Monitor progress in real-time
5. Copy completed transcript using the "Copy to Clipboard" button
6. Find saved transcripts in the `/transcripts` folder

## Project Structure

```
├── transcripts/          # Saved transcript files
├── uploads/             # Temporary storage for uploads
├── main.py             # Main application code
├── error_log.txt       # Application logs
└── README.md           # This file
```

## Configuration

The application uses the following default settings:

- Port: 8080
- Host: 0.0.0.0
- Chunk length: 15 seconds
- Whisper model: "base"

## Technical Details

- Uses OpenAI's Whisper model for transcription
- Implements chunked processing for memory efficiency
- Provides real-time progress updates via polling
- Stores transcription data in memory
- Uses threading for background processing

## Logging

The application uses a custom ReverseFileHandler for logging, which prepends new log entries to the log file. This makes it easier to see the most recent events first.

## License

This project is open source and available under the MIT License.
