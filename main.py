# ------------------------
# Importing Required Libraries
# ------------------------
from flask import Flask, request, render_template_string, jsonify, Response
import os
import logging
import uuid
import datetime
import whisper
from pydub import AudioSegment
import threading
import time

# ------------------------
# Logging Configuration
# ------------------------
class ReverseFileHandler(logging.FileHandler):
    def emit(self, record):
        with open(self.baseFilename, 'r+') as file:
            old_content = file.read()
            file.seek(0, 0)
            file.write(self.format(record) + '\n' + old_content)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger()
reverse_handler = ReverseFileHandler('error_log.txt')
logger.addHandler(reverse_handler)

# ------------------------
# Constants and Global Variables
# ------------------------
MODEL = whisper.load_model("base")
UPLOAD_FOLDER = 'uploads'
TRANSCRIPTS_FOLDER = 'transcripts'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRANSCRIPTS_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Setting the maximum content length to None to remove upload limits
app.config['MAX_CONTENT_LENGTH'] = None

# Store transcription progress and results in memory
transcription_data = {}

# ------------------------
# Helper Functions
# ------------------------

# Function to save the transcript as a text file
def save_transcript_as_txt(transcript, filename):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(TRANSCRIPTS_FOLDER, f"{timestamp}_{filename}.txt")

    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(transcript)
        logging.debug(f"Transcript saved to {file_path}.")
        return file_path
    except Exception as e:
        logging.error(f"Error saving transcript: {e}")
        return None

# Function to split audio into 15-second chunks
def split_audio(file_path, chunk_length_ms=15000):
    audio = AudioSegment.from_file(file_path)
    chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
    return chunks

# Function to handle the transcription process with polling
def transcribe_file(file_path, filename, job_id):
    try:
        audio_chunks = split_audio(file_path)
        total_chunks = len(audio_chunks)
        transcript = ""
        start_time = time.time()

        for i, chunk in enumerate(audio_chunks):
            chunk_file = f"{file_path}_chunk_{i}.wav"
            chunk.export(chunk_file, format="wav")

            # Transcribe the chunk
            result = MODEL.transcribe(chunk_file)
            chunk_transcript = result.get("text", "")
            transcript += chunk_transcript + "\n"

            elapsed_time = time.time() - start_time
            remaining_time = elapsed_time * (total_chunks - i - 1) / (i + 1)

            logging.debug(f"Chunk {i+1}/{total_chunks} transcribed. Transcript so far: {chunk_transcript}")

            # Update progress in the global dictionary
            transcription_data[job_id] = {
                'progress': (i + 1) / total_chunks * 100,
                'transcript': transcript,
                'total_chunks': total_chunks,
                'processed_chunks': i + 1,
                'elapsed_time': elapsed_time,
                'remaining_time': remaining_time,
                'complete': False
            }

        # Save the full transcript to a file
        save_transcript_as_txt(transcript, filename)

        # Mark transcription as complete
        transcription_data[job_id]['complete'] = True

    except Exception as e:
        logging.error(f"Error during transcription: {e}")
        transcription_data[job_id]['error'] = str(e)

# Route: Upload and Start Transcription
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            job_id = str(uuid.uuid4())
            filename = f"{job_id}_{file.filename}"
            file_path = os.path.join(UPLOAD_FOLDER, filename)

            with open(file_path, 'wb') as f:
                while chunk := file.stream.read(4096):
                    f.write(chunk)

            logging.debug(f"File uploaded to {file_path}. Beginning transcription.")

            # Start transcription in a background thread
            threading.Thread(target=transcribe_file, args=(file_path, filename, job_id)).start()

            return jsonify({'job_id': job_id}), 202

    return render_template_string('''
        <form method="post" enctype="multipart/form-data">
            Upload Video/Audio File: <input type="file" name="file" accept="audio/*,video/*"><br>
            <input type="submit" value="Upload and Transcribe">
        </form>
        <div id="spinner" style="display:none;">
            <p>Transcribing... <span id="time-info"></span></p>
        </div>
        <div id="progress-bar" style="width: 100%; background-color: #f3f3f3; height: 30px; display:none;">
            <div id="progress" style="width: 0%; height: 100%; background-color: #4caf50;"></div>
        </div>
        <div id="status"></div>
        <pre id="transcript"></pre>
        <button onclick="copyToClipboard()" style="display:none;">Copy to Clipboard</button>
        <script>
            function copyToClipboard() {
                var text = document.getElementById("transcript").innerText;
                navigator.clipboard.writeText(text).then(function() {
                    alert("Transcript copied to clipboard!");
                }, function() {
                    alert("Failed to copy transcript to clipboard.");
                });
            }

            document.querySelector('form').onsubmit = function(event) {
                event.preventDefault();
                var formData = new FormData(this);
                var xhr = new XMLHttpRequest();
                xhr.open('POST', '/', true);

                xhr.onload = function() {
                    if (xhr.status == 202) {
                        var job_id = JSON.parse(xhr.responseText).job_id;
                        document.getElementById('progress-bar').style.display = 'block';
                        document.getElementById('spinner').style.display = 'block';
                        pollProgress(job_id);
                    } else {
                        console.error("Failed to start transcription, status: " + xhr.status);
                    }
                };

                xhr.onerror = function() {
                    console.error("Request failed");
                };

                xhr.send(formData);
            };

            function pollProgress(job_id) {
                var xhr = new XMLHttpRequest();
                xhr.open('GET', '/progress/' + job_id, true);
                xhr.onload = function() {
                    if (xhr.status == 200) {
                        var data = JSON.parse(xhr.responseText);
                        document.getElementById('progress').style.width = data.progress + '%';
                        document.getElementById('status').innerText = 'Processing chunk ' + data.processed_chunks + ' of ' + data.total_chunks + ' (' + Math.round(data.elapsed_time) + 's elapsed, ' + Math.round(data.remaining_time) + 's remaining)';
                        document.getElementById('transcript').innerText = data.transcript;

                        if (!data.complete) {
                            setTimeout(function() {
                                pollProgress(job_id);
                            }, 1000);
                        } else {
                            document.getElementById('spinner').style.display = 'none';
                            document.querySelector('button').style.display = 'block';
                        }
                    } else {
                        console.error("Failed to load progress, status: " + xhr.status);
                    }
                };
                xhr.send();
            }
        </script>
    ''')

# Route: Check Progress
@app.route('/progress/<job_id>')
def progress(job_id):
    return jsonify(transcription_data.get(job_id, {'error': 'Job not found'}))

# Entry point for running the Flask application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
