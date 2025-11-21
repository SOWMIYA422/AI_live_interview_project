import queue
import sounddevice as sd
import json
import time
import os
import wave
import cv2
import threading
from vosk import Model, KaldiRecognizer
from config import VOSK_MODEL_PATH, SAMPLE_RATE, OUTPUT_DIR


class InterviewSTT:
    def __init__(self, interview_id):
        self.interview_id = interview_id
        self.session_dir = f"{OUTPUT_DIR}/{interview_id}"
        os.makedirs(self.session_dir, exist_ok=True)

        # File paths
        self.audio_file = f"{self.session_dir}/audio.wav"
        self.video_file = f"{self.session_dir}/video.avi"
        self.transcript_file = f"{self.session_dir}/transcript.txt"

        # Initialize Vosk
        print("[STT] Loading speech recognition model...")
        if not os.path.exists(VOSK_MODEL_PATH):
            # Create a dummy model path for initial setup
            os.makedirs(VOSK_MODEL_PATH, exist_ok=True)
            print(f"[STT] Please download Vosk model to: {VOSK_MODEL_PATH}")

        try:
            self.model = Model(VOSK_MODEL_PATH)
            self.rec = KaldiRecognizer(self.model, SAMPLE_RATE)
            self.rec.SetWords(True)
        except Exception as e:
            print(f"[STT] Model loading warning: {e}")
            self.model = None
            self.rec = None

        # Audio setup
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.is_listening = False
        self.current_transcription = ""
        self.full_transcription = []

        # Silence detection variables
        self.last_speech_time = time.time()
        self.silence_start_time = None
        self.silence_threshold = 10  # seconds
        self.max_warnings = 3
        self.warning_count = 0
        self.is_silent = False
        self.termination_triggered = False

        # State tracking for UI updates
        self.silence_warning_active = False
        self.current_warning_message = ""
        self.should_terminate = False

        # Thread control
        self._stop_transcription = False
        self._stop_video = False

        # Callback functions
        self.on_silence_warning = None
        self.on_interview_terminate = None

        # Initialize transcript file
        with open(self.transcript_file, "w", encoding="utf-8") as f:
            f.write(f"Interview Transcript - {interview_id}\n")
            f.write("=" * 50 + "\n\n")

    def audio_callback(self, indata, frames, time, status):
        """Callback for audio input"""
        if status:
            print(f"Audio status: {status}")

        if self.is_recording and not self._stop_transcription:
            self.audio_queue.put(bytes(indata))
            if hasattr(self, "wf"):
                self.wf.writeframes(bytes(indata))

    def start_recording(self):
        """Start audio recording"""
        print("[STT] Starting audio recording...")

        # Reset control flags
        self._stop_transcription = False
        self._stop_video = False
        self.silence_warning_active = False
        self.should_terminate = False
        self.warning_count = 0

        # Initialize audio file
        self.wf = wave.open(self.audio_file, "wb")
        self.wf.setnchannels(1)
        self.wf.setsampwidth(2)
        self.wf.setframerate(SAMPLE_RATE)

        self.is_recording = True
        self.termination_triggered = False

        # Start audio stream
        try:
            self.audio_stream = sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=self.audio_callback,
            )
            self.audio_stream.start()
        except Exception as e:
            print(f"[STT] Audio stream error: {e}")
            self.is_recording = False
            return

        # Start transcription thread
        self.transcription_thread = threading.Thread(target=self._transcription_loop)
        self.transcription_thread.daemon = True
        self.transcription_thread.start()

        print("[STT] Recording started")

    def start_video_recording(self):
        """Start video recording in separate thread"""
        self.video_thread = threading.Thread(target=self._video_loop)
        self.video_thread.daemon = True
        self.video_thread.start()

    def _video_loop(self):
        """Video recording loop"""
        print("[Video] Starting video recording...")
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("[Video] Could not open webcam")
                return

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            self.video_out = cv2.VideoWriter(self.video_file, fourcc, 20.0, (640, 480))

            while self.is_recording and not self._stop_video:
                ret, frame = self.cap.read()
                if ret:
                    self.video_out.write(frame)
                time.sleep(0.05)

        except Exception as e:
            print(f"[Video] Recording error: {e}")
        finally:
            if hasattr(self, "cap"):
                self.cap.release()
            if hasattr(self, "video_out"):
                self.video_out.release()
            print("[Video] Video recording stopped")

    def _transcription_loop(self):
        """Process audio for transcription with silence detection"""
        while self.is_recording and self.rec and not self._stop_transcription:
            try:
                if not self.audio_queue.empty():
                    data = self.audio_queue.get()

                    if self.is_listening and self.rec.AcceptWaveform(data):
                        result = json.loads(self.rec.Result())
                        text = result.get("text", "").strip()
                        if text:
                            # Speech detected - reset silence tracking
                            self.last_speech_time = time.time()
                            self.silence_start_time = None
                            self.is_silent = False
                            self.silence_warning_active = False

                            self.current_transcription = text
                            self.full_transcription.append(text)
                            self._save_transcription(text)
                            print(f"[Transcription] {text}")

                    elif self.is_listening:
                        partial = json.loads(self.rec.PartialResult())
                        partial_text = partial.get("partial", "")
                        if partial_text:
                            # Partial speech detected - reset silence
                            self.last_speech_time = time.time()
                            self.silence_start_time = None
                            self.is_silent = False
                            self.silence_warning_active = False
                            self.current_transcription = partial_text

                # Silence detection logic
                if self.is_listening and not self._stop_transcription:
                    self._check_silence()

                time.sleep(0.1)

            except Exception as e:
                if not self._stop_transcription:
                    print(f"[Transcription Error] {e}")
                time.sleep(0.5)

    def _check_silence(self):
        """Check for prolonged silence and trigger warnings"""
        if not self.is_listening or not self.is_recording or self._stop_transcription:
            return

        current_time = time.time()
        time_since_speech = current_time - self.last_speech_time

        # Check if silence threshold is reached
        if time_since_speech >= self.silence_threshold:
            if self.silence_start_time is None:
                self.silence_start_time = current_time
                self.is_silent = True

            silence_duration = current_time - self.silence_start_time

            if silence_duration >= self.silence_threshold:
                if self.warning_count < self.max_warnings:
                    self.warning_count += 1
                    self.silence_start_time = current_time
                    self.silence_warning_active = True

                    # Set warning message
                    if self.warning_count == 1:
                        self.current_warning_message = "🔇 First Warning: Please start speaking. We haven't heard you in 10 seconds."
                    elif self.warning_count == 2:
                        self.current_warning_message = "🔇 Second Warning: We still haven't heard your response. Please speak now."
                    elif self.warning_count == 3:
                        self.current_warning_message = "🔇 Final Warning: This is your last chance to respond. The interview will end if no response is detected."

                    # Trigger callback if available
                    if self.on_silence_warning:
                        try:
                            self.on_silence_warning(
                                self.warning_count, self.max_warnings
                            )
                        except Exception as e:
                            print(f"[Warning Callback Error] {e}")

                    print(
                        f"🔇 Silence Warning {self.warning_count}/{self.max_warnings}"
                    )
                else:
                    # Max warnings reached - terminate interview
                    if not self.termination_triggered:
                        self.termination_triggered = True
                        self.should_terminate = True
                        self.silence_warning_active = True
                        self.current_warning_message = "❌ Interview terminated due to prolonged silence. No response detected after 3 warnings."

                        if self.on_interview_terminate:
                            try:
                                self.on_interview_terminate()
                            except Exception as e:
                                print(f"[Termination Callback Error] {e}")
                        print(
                            "🔇 Interview termination triggered due to prolonged silence"
                        )
        else:
            self.is_silent = False
            self.silence_start_time = None

    def _save_transcription(self, text):
        """Save transcription to file"""
        with open(self.transcript_file, "a", encoding="utf-8") as f:
            timestamp = time.strftime("%H:%M:%S")
            f.write(f"[{timestamp}] {text}\n")

    def start_listening(self):
        """Start actively listening for responses"""
        self.is_listening = True
        self.current_transcription = ""
        self.reset_silence_tracker()
        print("[STT] Started listening for candidate response")

    def stop_listening(self):
        """Stop listening and return transcription"""
        self.is_listening = False
        final_text = self.current_transcription
        self.current_transcription = ""
        print(f"[STT] Stopped listening. Captured: {final_text}")
        return final_text

    def get_current_transcription(self):
        """Get current transcription"""
        return self.current_transcription

    def reset_silence_tracker(self):
        """Reset silence tracking"""
        self.last_speech_time = time.time()
        self.silence_start_time = None
        self.is_silent = False
        self.silence_warning_active = False

    def get_silence_status(self):
        """Get current silence status for UI"""
        return {
            "is_silent": self.is_silent,
            "warning_count": self.warning_count,
            "max_warnings": self.max_warnings,
            "warning_active": self.silence_warning_active,
            "warning_message": self.current_warning_message,
            "should_terminate": self.should_terminate,
            "time_since_speech": time.time() - self.last_speech_time,
        }

    def clear_warning(self):
        """Clear current warning state"""
        self.silence_warning_active = False
        self.current_warning_message = ""

    def stop_all_activities(self):
        """Immediately stop all recording and transcription activities"""
        print("[STT] Stopping all activities...")
        self._stop_transcription = True
        self._stop_video = True
        self.is_recording = False
        self.is_listening = False

    def cleanup(self):
        """Clean up resources"""
        print("[STT] Cleaning up resources...")
        self.stop_all_activities()
        time.sleep(0.5)

        if hasattr(self, "audio_stream"):
            try:
                self.audio_stream.stop()
                self.audio_stream.close()
                print("[STT] Audio stream stopped")
            except Exception as e:
                print(f"[STT] Error stopping audio stream: {e}")

        if hasattr(self, "wf"):
            try:
                self.wf.close()
                print("[STT] Audio file closed")
            except Exception as e:
                print(f"[STT] Error closing audio file: {e}")

        if hasattr(self, "cap"):
            try:
                self.cap.release()
                print("[STT] Video capture released")
            except Exception as e:
                print(f"[STT] Error releasing video capture: {e}")

        if hasattr(self, "video_out"):
            try:
                self.video_out.release()
                print("[STT] Video writer released")
            except Exception as e:
                print(f"[STT] Error releasing video writer: {e}")

        try:
            cv2.destroyAllWindows()
        except:
            pass

        print("[STT] Cleanup completed")
