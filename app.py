# app.py
import streamlit as st
import os
import time
import tempfile
from gtts import gTTS
import base64
import logging

from interview_manager import InterviewManager
from stt_worker import InterviewSTT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="🎙️ Live AI Interview System",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Custom CSS
def load_css():
    st.markdown(
        """
    <style>
    .main-header {
        font-size: 3rem;
        background: linear-gradient(45deg, #FF6B6B, #4ECDC4, #45B7D1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .interview-container {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 25px;
        margin: 15px 0;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .question-bubble {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 25px 25px 25px 5px;
        margin: 15px 0;
        max-width: 85%;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    .answer-bubble {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 20px;
        border-radius: 25px 25px 5px 25px;
        margin: 15px 0;
        margin-left: 15%;
        max-width: 85%;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    .analysis-bubble {
        background: linear-gradient(135deg, #FFA62E, #FF7B25);
        color: white;
        padding: 15px;
        border-radius: 15px;
        margin: 10px 0;
        max-width: 80%;
        font-style: italic;
    }
    .status-listening {
        background: linear-gradient(135deg, #FF416C, #FF4B2B);
        color: white;
        padding: 15px;
        border-radius: 15px;
        text-align: center;
        margin: 10px 0;
        animation: pulse 2s infinite;
    }
    .status-analyzing {
        background: linear-gradient(135deg, #f46b45, #eea849);
        color: white;
        padding: 15px;
        border-radius: 15px;
        text-align: center;
        margin: 10px 0;
    }
    .status-speaking {
        background: linear-gradient(135deg, #36D1DC, #5B86E5);
        color: white;
        padding: 15px;
        border-radius: 15px;
        text-align: center;
        margin: 10px 0;
    }
    .question-display {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        margin: 20px 0;
        font-size: 18px;
        font-weight: bold;
        text-align: center;
        border: 2px solid rgba(255, 255, 255, 0.3);
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    .stButton button {
        border-radius: 15px;
        padding: 10px 20px;
        font-weight: bold;
        border: none;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
    }
    .technical-help {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .silence-warning {
        background: linear-gradient(135deg, #FFD93D, #FF9A3D);
        color: #856404;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border: 1px solid #FFC107;
        animation: pulse 2s infinite;
    }
    .silence-terminated {
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        color: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin: 15px 0;
        border: 2px solid #FF4757;
        animation: pulse 1s infinite;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def autoplay_audio(file_path):
    """Auto-play audio file with error handling"""
    try:
        if not file_path or not os.path.exists(file_path):
            return False

        with open(file_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            md = f"""
                <audio autoplay controls style="display: none;">
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>
                """
            st.markdown(md, unsafe_allow_html=True)
            return True
    except Exception as e:
        logger.error(f"Audio playback error: {e}")
        return False


def speak_text(text):
    """Convert text to speech and return file path"""
    try:
        if not text or len(text.strip()) == 0:
            return None

        tts = gTTS(text=text, lang="en", slow=False)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(temp_file.name)
        logger.info(f"✅ TTS generated: {text[:50]}...")
        return temp_file.name
    except Exception as e:
        logger.error(f"Text-to-speech error: {e}")
        return None


def initialize_session_state():
    """Initialize session state variables"""
    defaults = {
        "interview_started": False,
        "current_question": "",
        "conversation_history": [],
        "analysis_history": [],
        "waiting_for_answer": False,
        "stt_engine": None,
        "interview_manager": None,
        "interview_ended": False,
        "current_audio_file": None,
        "processing_answer": False,
        "answer_submitted": False,
        "last_action_time": time.time(),
        "questions_asked": [],
        "current_question_index": 0,
        "max_questions": 10,
        "technical_issues": False,
        # Silence detection variables
        "silence_warnings": 0,
        "max_silence_warnings": 3,
        "show_silence_alert": False,
        "silence_alert_message": "",
        "interview_terminated": False,
        # UI state tracking
        "last_silence_check": time.time(),
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def setup_silence_callbacks():
    """Setup callback functions for silence detection"""
    try:
        if (
            st.session_state.interview_started
            and "stt_engine" in st.session_state
            and st.session_state.stt_engine
            and not st.session_state.interview_ended
        ):
            # Set callback for silence warnings
            st.session_state.stt_engine.on_silence_warning = handle_silence_warning
            st.session_state.stt_engine.on_interview_terminate = (
                handle_interview_termination
            )
            logger.info("✅ Silence callbacks setup successfully")
    except Exception as e:
        logger.error(f"❌ Error setting up silence callbacks: {e}")


def handle_silence_warning(warning_count, max_warnings):
    """Handle silence warning callback"""
    try:
        st.session_state.silence_warnings = warning_count
        st.session_state.max_silence_warnings = max_warnings
        st.session_state.show_silence_alert = True

        if warning_count == 1:
            st.session_state.silence_alert_message = "🔇 First Warning: Please start speaking. We haven't heard you in 10 seconds."
        elif warning_count == 2:
            st.session_state.silence_alert_message = "🔇 Second Warning: We still haven't heard your response. Please speak now."
        elif warning_count == 3:
            st.session_state.silence_alert_message = "🔇 Final Warning: This is your last chance to respond. The interview will end if no response is detected."

        # Force UI update
        st.session_state.last_action_time = time.time()
        logger.info(f"🔇 Silence warning {warning_count}/{max_warnings} triggered")
    except Exception as e:
        logger.error(f"❌ Error in silence warning handler: {e}")


def handle_interview_termination():
    """Handle interview termination due to silence - SAFE VERSION"""
    try:
        # Set termination flag first
        st.session_state.interview_terminated = True
        st.session_state.show_silence_alert = True
        st.session_state.silence_alert_message = "❌ Interview terminated due to prolonged silence. No response detected after 3 warnings."

        # IMPORTANT: Stop STT engine immediately to prevent further transcription
        if "stt_engine" in st.session_state and st.session_state.stt_engine:
            st.session_state.stt_engine.stop_all_activities()

        # Stop the interview safely
        safe_end_interview()

        # Force UI update
        st.session_state.last_action_time = time.time()
        logger.info("🔇 Interview terminated via silence detection")

    except Exception as e:
        logger.error(f"❌ Error in termination handler: {e}")


def safe_end_interview():
    """Safely end interview without assuming session state exists"""
    try:
        # Clean up STT engine if it exists - STOP ALL ACTIVITIES FIRST
        if "stt_engine" in st.session_state and st.session_state.stt_engine:
            st.session_state.stt_engine.stop_all_activities()
            # Give it a moment to stop
            time.sleep(0.2)
            st.session_state.stt_engine.cleanup()

        # Update interview state safely
        st.session_state.interview_ended = True
        st.session_state.waiting_for_answer = False
        st.session_state.processing_answer = False
        st.session_state.interview_terminated = True

        # Update last action time safely
        if "last_action_time" in st.session_state:
            st.session_state.last_action_time = time.time()

        logger.info("🏁 Interview ended safely")

    except Exception as e:
        logger.error(f"❌ Error in safe_end_interview: {e}")


def check_silence_status():
    """Check for silence warnings and termination from STT engine"""
    try:
        if (
            st.session_state.interview_started
            and not st.session_state.interview_ended
            and not st.session_state.interview_terminated
            and "stt_engine" in st.session_state
            and st.session_state.stt_engine
        ):
            silence_status = st.session_state.stt_engine.get_silence_status()

            # Check if we should show a warning
            if silence_status["warning_active"] and silence_status["warning_message"]:
                st.session_state.show_silence_alert = True
                st.session_state.silence_alert_message = silence_status[
                    "warning_message"
                ]
                st.session_state.silence_warnings = silence_status["warning_count"]
                st.session_state.max_silence_warnings = silence_status["max_warnings"]
                st.session_state.last_action_time = time.time()

            # Check if we should terminate
            if (
                silence_status["should_terminate"]
                and not st.session_state.interview_terminated
            ):
                logger.info("🔄 Silence termination detected via status check")
                handle_interview_termination()

    except Exception as e:
        logger.error(f"❌ Error checking silence status: {e}")


def display_silence_alerts():
    """Display silence warnings and termination messages"""
    if st.session_state.show_silence_alert and st.session_state.silence_alert_message:
        # Different styling based on severity
        if st.session_state.interview_terminated:
            st.markdown(
                f"""
                <div class="silence-terminated">
                    <h3>❌ Interview Terminated</h3>
                    <p>{st.session_state.silence_alert_message}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Add restart option
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button(
                    "🔄 Start New Interview",
                    use_container_width=True,
                    key="restart_terminated",
                ):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()

        else:
            # Warning style
            st.markdown(
                f"""
                <div class="silence-warning">
                    <strong>⚠️ Attention Required</strong><br>
                    {st.session_state.silence_alert_message}<br>
                    <small>Warning {st.session_state.silence_warnings}/{st.session_state.max_silence_warnings}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Auto-hide alert after 5 seconds (unless it's the final warning)
            if (
                time.time() - st.session_state.last_action_time > 5
                and st.session_state.silence_warnings
                < st.session_state.max_silence_warnings
            ):
                st.session_state.show_silence_alert = False
                # Clear the warning in STT engine
                if "stt_engine" in st.session_state and st.session_state.stt_engine:
                    st.session_state.stt_engine.clear_warning()


def reset_silence_alert():
    """Reset silence alert when user starts speaking"""
    if (
        st.session_state.show_silence_alert
        and "stt_engine" in st.session_state
        and st.session_state.stt_engine
        and not st.session_state.stt_engine.is_silent
    ):
        st.session_state.show_silence_alert = False
        st.session_state.last_action_time = time.time()
        # Clear the warning in STT engine
        st.session_state.stt_engine.clear_warning()


def start_interview_session(job_role, candidate_name):
    """Start the interview session"""
    try:
        logger.info(
            f"🚀 Starting interview for {job_role}, candidate: {candidate_name}"
        )

        # Initialize interview manager
        st.session_state.interview_manager = InterviewManager(job_role, candidate_name)

        # Get opening question
        opening_question = st.session_state.interview_manager.get_opening_question()
        st.session_state.current_question = opening_question
        st.session_state.questions_asked.append(opening_question)
        st.session_state.conversation_history.append(
            ("AI Interviewer", opening_question)
        )

        # Initialize STT engine
        st.session_state.stt_engine = InterviewSTT(
            st.session_state.interview_manager.interview_id
        )

        # Start recording
        st.session_state.stt_engine.start_recording()
        st.session_state.stt_engine.start_video_recording()

        # Setup silence detection callbacks
        setup_silence_callbacks()

        # Convert opening to speech
        audio_file = speak_text(opening_question)
        if audio_file:
            st.session_state.current_audio_file = audio_file

        # Start listening for answer
        st.session_state.stt_engine.start_listening()
        st.session_state.waiting_for_answer = True
        st.session_state.interview_started = True
        st.session_state.current_question_index = 1
        st.session_state.last_action_time = time.time()

        st.success("🎉 Interview started! AI is asking the first question...")
        logger.info("✅ Interview session started successfully")

    except Exception as e:
        logger.error(f"❌ Error starting interview: {str(e)}")
        st.error(f"Failed to start interview: {str(e)}")


def submit_answer(use_typed_fallback=None):
    """Process the submitted answer and generate next question"""
    if not st.session_state.waiting_for_answer:
        st.warning("Not currently waiting for an answer.")
        return

    if not st.session_state.stt_engine:
        st.error("Speech recognition engine not available.")
        return

    if not st.session_state.interview_manager:
        st.error("Interview manager not available.")
        return

    st.session_state.processing_answer = True
    st.session_state.answer_submitted = True

    try:
        # Reset silence tracking when answer is submitted
        if st.session_state.stt_engine:
            st.session_state.stt_engine.reset_silence_tracker()
            st.session_state.show_silence_alert = False

        # Get final transcription
        if use_typed_fallback and "typed_answer" in st.session_state:
            final_answer = st.session_state.typed_answer
        else:
            final_answer = st.session_state.stt_engine.stop_listening()

        logger.info(f"🎤 Captured answer: {final_answer}")

        if not final_answer or not final_answer.strip():
            final_answer = "The candidate did not provide a verbal answer."
            st.warning("No speech detected in the recording.")

        # Add candidate's answer to conversation
        st.session_state.conversation_history.append(("Candidate", final_answer))

        # Process the Q&A pair and generate next question
        qa_data, next_question = st.session_state.interview_manager.add_qa_pair(
            st.session_state.current_question, final_answer, final_answer
        )

        # Store the analysis
        if "analysis" in qa_data:
            st.session_state.analysis_history.append(qa_data["analysis"])
            st.session_state.conversation_history.append(
                ("AI Analysis", qa_data["analysis"])
            )

        # Check if interview should end
        current_count = len(st.session_state.questions_asked)
        if current_count >= st.session_state.max_questions:
            end_interview()
            return

        # Update with the new question
        st.session_state.current_question = next_question
        st.session_state.questions_asked.append(next_question)
        st.session_state.conversation_history.append(("AI Interviewer", next_question))
        st.session_state.current_question_index += 1

        # Convert to speech
        audio_file = speak_text(next_question)
        if audio_file:
            st.session_state.current_audio_file = audio_file

        # Resume listening for next answer
        st.session_state.stt_engine.start_listening()
        st.session_state.waiting_for_answer = True

        # Clear typed answer if used
        if use_typed_fallback:
            st.session_state.typed_answer = ""

        st.success(
            f"✅ Question {st.session_state.current_question_index}/{st.session_state.max_questions} generated!"
        )
        logger.info(f"✅ Next question generated: {next_question}")

    except Exception as e:
        logger.error(f"❌ Error processing answer: {str(e)}")
        st.error(f"Error processing answer: {str(e)}")

        # Restart listening and silence tracking
        if st.session_state.stt_engine:
            st.session_state.stt_engine.start_listening()
            st.session_state.stt_engine.reset_silence_tracker()
    finally:
        st.session_state.processing_answer = False
        st.session_state.answer_submitted = False
        st.session_state.last_action_time = time.time()


def end_interview():
    """End the interview session"""
    try:
        # Stop STT engine first
        if "stt_engine" in st.session_state and st.session_state.stt_engine:
            st.session_state.stt_engine.stop_all_activities()
            time.sleep(0.2)  # Give it time to stop
            st.session_state.stt_engine.cleanup()

        if (
            "interview_manager" in st.session_state
            and st.session_state.interview_manager
        ):
            final_feedback = st.session_state.interview_manager.end_interview()
            st.session_state.conversation_history.append(
                ("AI Interviewer", f"Interview completed! {final_feedback}")
            )

        st.session_state.interview_ended = True
        st.session_state.waiting_for_answer = False
        st.session_state.processing_answer = False
        st.session_state.last_action_time = time.time()

        logger.info("🏁 Interview ended successfully")

    except Exception as e:
        logger.error(f"❌ Error ending interview: {str(e)}")


def display_technical_help():
    """Display technical troubleshooting guide"""
    with st.expander("🔧 Having Technical Issues? Click here for help"):
        st.markdown("""
        **Common Solutions:**
        
        🎤 **Microphone Not Working:**
        - Check browser microphone permissions
        - Ensure no other app is using the microphone
        - Try using headphones with built-in mic
        
        🔊 **Can't Hear Questions:**
        - Check your volume settings  
        - Use headphones for better audio
        - Questions are displayed on screen for reference
        
        🖥️ **System Issues:**
        - Refresh the page and restart
        - Try a different browser (Chrome recommended)
        - Ensure stable internet connection
        
        🗣️ **Speech Recognition Issues:**
        - Speak clearly and at a moderate pace
        - Ensure you're in a quiet environment
        - Use the typing fallback if speech continues to fail
        
        ⚠️ **Silence Detection:**
        - System will warn you after 10 seconds of silence
        - 3 warnings will result in interview termination
        - Keep speaking naturally to avoid warnings
        """)

        if st.button("🔄 Restart Interview Session", key="restart_tech"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


def display_current_question():
    """Display the current question prominently"""
    if st.session_state.current_question:
        st.markdown(
            f'<div class="question-display">'
            f"<h3>📋 Question {st.session_state.current_question_index}/{st.session_state.max_questions}</h3>"
            f"<p>{st.session_state.current_question}</p>"
            f"</div>",
            unsafe_allow_html=True,
        )


def display_interview_status():
    """Display current interview status with silence warnings"""
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        if st.session_state.interview_terminated:
            st.markdown(
                '<div class="status-analyzing">❌ Interview Terminated - No Response</div>',
                unsafe_allow_html=True,
            )
        elif st.session_state.processing_answer:
            st.markdown(
                '<div class="status-analyzing">🔍 Analyzing your answer...</div>',
                unsafe_allow_html=True,
            )
        elif st.session_state.waiting_for_answer:
            # Show silence warning status
            if st.session_state.show_silence_alert:
                st.markdown(
                    '<div class="status-listening" style="background: linear-gradient(135deg, #FFD93D, #FF9A3D);">⚠️ Waiting for Response - Warning Active</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="status-listening">🎤 Listening for your answer...</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="status-speaking">🤖 AI is speaking...</div>',
                unsafe_allow_html=True,
            )

    with col2:
        st.metric(
            "Questions",
            f"{st.session_state.current_question_index}/{st.session_state.max_questions}",
        )

    with col3:
        answers_count = len(st.session_state.analysis_history)
        st.metric("Answers", answers_count)

    with col4:
        # Show silence warning count
        if st.session_state.silence_warnings > 0:
            st.metric(
                "Warnings",
                f"{st.session_state.silence_warnings}/{st.session_state.max_silence_warnings}",
                delta="Silence Alert" if st.session_state.show_silence_alert else None,
                delta_color="inverse",
            )


def display_conversation_history():
    """Display the conversation history with analysis"""
    st.subheader("💬 Live Conversation with Analysis")

    if not st.session_state.conversation_history:
        st.info("💬 Conversation will appear here...")
    else:
        for speaker, text in st.session_state.conversation_history:
            if speaker == "AI Interviewer":
                st.markdown(
                    f'<div class="question-bubble"><strong>🤖 {speaker}:</strong> {text}</div>',
                    unsafe_allow_html=True,
                )
            elif speaker == "AI Analysis":
                st.markdown(
                    f'<div class="analysis-bubble"><strong>📊 {speaker}:</strong> {text}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="answer-bubble"><strong>👤 {speaker}:</strong> {text}</div>',
                    unsafe_allow_html=True,
                )


def handle_audio_playback():
    """Handle audio file playback and cleanup"""
    if st.session_state.current_audio_file and os.path.exists(
        st.session_state.current_audio_file
    ):
        if autoplay_audio(st.session_state.current_audio_file):
            try:
                os.unlink(st.session_state.current_audio_file)
                st.session_state.current_audio_file = None
            except Exception as e:
                logger.warning(f"Could not delete audio file: {e}")


def display_welcome_screen():
    """Display the interview welcome and instructions screen"""
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        ## 🤖 Welcome to AI Interviewer
        
        **Smart Interview Features:**
        ✅ **Adaptive Questions** - Questions evolve based on your responses  
        ✅ **Real-time Transcription** - Speak naturally, get transcribed instantly  
        ✅ **Answer Analysis** - AI analyzes each answer before generating next question  
        ✅ **Multiple Input Methods** - Speech recognition with typing fallback  
        ✅ **Silence Detection** - Automatic warnings after 10 seconds of silence
        ✅ **Auto-Termination** - Interview ends after 3 silence warnings
        
        **How it works:**
        1. **Start** the interview and allow microphone access
        2. **Listen** to the AI question (also displayed on screen)  
        3. **Speak** your answer clearly within 10 seconds
        4. **Submit** to get the next question
        5. **Complete** all 10 questions for full assessment
        
        **⚠️ Important:**
        - You'll get warnings after 10 seconds of silence
        - 3 warnings will automatically end the interview
        - Use typing fallback if speech recognition fails
        """)

    with col2:
        st.markdown(
            """
            <div style='text-align: center; padding: 20px;'>
                <div style='font-size: 80px;'>🎯</div>
                <h3>AI Interviewer</h3>
                <p>Professional • Adaptive • Intelligent</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.info("""
        **💡 Pro Tip:** 
        - Find a quiet location
        - Use a good microphone
        - Speak clearly and naturally
        - Respond within 10 seconds to avoid warnings
        - Use typing if speech recognition fails
        """)


def display_interview_in_progress():
    """Display the main interview interface"""
    st.markdown('<div class="interview-container">', unsafe_allow_html=True)

    # Status indicator
    display_interview_status()

    # Current question display
    display_current_question()

    # Conversation display
    display_conversation_history()

    # Audio playback
    handle_audio_playback()

    st.markdown("</div>", unsafe_allow_html=True)


def display_interview_complete():
    """Display interview completion screen"""
    if not st.session_state.interview_terminated:
        st.balloons()

    st.markdown(
        """
        <div style='
            background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%);
            padding: 40px;
            border-radius: 15px;
            text-align: center;
            margin: 20px 0;
        '>
            <h2 style='color: #2E7D32;'>🎉 Interview Completed Successfully!</h2>
            <p style='font-size: 18px;'>Thank you for completing the interview.</p>
        </div>
        """
        if not st.session_state.interview_terminated
        else """
        <div style='
            background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
            padding: 40px;
            border-radius: 15px;
            text-align: center;
            margin: 20px 0;
        '>
            <h2 style='color: #c62828;'>❌ Interview Terminated</h2>
            <p style='font-size: 18px;'>The interview was ended due to prolonged silence.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Show summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Questions", st.session_state.current_question_index)
    with col2:
        st.metric("Answers Analyzed", len(st.session_state.analysis_history))
    with col3:
        if st.session_state.silence_warnings > 0:
            st.metric("Silence Warnings", st.session_state.silence_warnings)

    if st.button("🔄 Start New Interview", type="primary", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


def main():
    load_css()
    initialize_session_state()

    # Header
    st.markdown(
        '<h1 class="main-header">🎙️ Live AI Interview System</h1>',
        unsafe_allow_html=True,
    )

    # Check for silence status updates - THIS IS THE KEY FIX
    check_silence_status()

    # Setup silence detection callbacks
    try:
        if st.session_state.interview_started:
            setup_silence_callbacks()
    except Exception as e:
        logger.error(f"❌ Error in main silence setup: {e}")

    # Display silence alerts if any
    try:
        display_silence_alerts()
    except Exception as e:
        logger.error(f"❌ Error displaying silence alerts: {e}")

    # Reset alert when speech is detected
    try:
        reset_silence_alert()
    except Exception as e:
        logger.error(f"❌ Error resetting silence alert: {e}")

    # Technical help
    display_technical_help()

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Interview Controls")

        if not st.session_state.interview_started:
            st.subheader("Start New Interview")
            job_role = st.selectbox(
                "Select Job Role",
                ["Data Scientist", "Software Engineer", "Product Manager", "Other"],
            )

            if job_role == "Other":
                job_role = st.text_input("Enter Job Role")

            candidate_name = st.text_input(
                "Candidate Name", placeholder="Enter your name"
            )

            if st.button(
                "🚀 Start Interview", use_container_width=True, type="primary"
            ):
                if job_role:
                    with st.spinner("Initializing interview session..."):
                        start_interview_session(job_role, candidate_name)
                    st.rerun()
                else:
                    st.error("Please enter a job role")

        else:
            # Interview in progress controls
            st.subheader("Interview Progress")

            progress = st.session_state.current_question_index
            total = st.session_state.max_questions

            # SAFE access to interview_manager
            job_role_display = "N/A"
            candidate_name_display = "N/A"
            if (
                "interview_manager" in st.session_state
                and st.session_state.interview_manager
            ):
                job_role_display = st.session_state.interview_manager.job_role
                candidate_name_display = (
                    st.session_state.interview_manager.candidate_name
                )

            st.write(f"**Role:** {job_role_display}")
            st.write(f"**Candidate:** {candidate_name_display}")
            st.write(f"**Progress:** {progress}/{total} questions")

            # Progress bar
            st.progress(progress / total)

            st.divider()

            # Answer submission button - with safety checks
            if (
                st.session_state.waiting_for_answer
                and not st.session_state.processing_answer
                and not st.session_state.interview_ended
                and not st.session_state.interview_terminated
            ):
                if st.button(
                    "✅ Submit Answer & Get Next Question",
                    use_container_width=True,
                    type="primary",
                    key="submit_answer_btn",
                ):
                    submit_answer()

                # Typing fallback
                st.subheader("📝 Type Answer (Fallback)")
                typed_answer = st.text_area(
                    "If speech recognition fails, type your answer here:",
                    height=100,
                    key="typed_answer",
                )
                if st.button("Submit Typed Answer", key="submit_typed"):
                    if typed_answer.strip():
                        submit_answer(use_typed_fallback=True)
                    else:
                        st.warning("Please type an answer first.")

            # End interview button - with safety check
            if (
                st.button(
                    "⏹️ End Interview", use_container_width=True, key="end_interview_btn"
                )
                and not st.session_state.interview_terminated
            ):
                safe_end_interview()
                st.rerun()

            # Live transcription preview - with safety checks
            if (
                st.session_state.waiting_for_answer
                and st.session_state.stt_engine
                and not st.session_state.processing_answer
                and not st.session_state.interview_ended
                and not st.session_state.interview_terminated
            ):
                current_text = st.session_state.stt_engine.get_current_transcription()
                if current_text:
                    st.subheader("🎤 Live Transcription")
                    st.text_area(
                        "Current Answer Preview",
                        value=current_text,
                        height=100,
                        label_visibility="collapsed",
                        key="transcription_preview",
                    )

    # Main content area
    if not st.session_state.interview_started:
        # Welcome screen
        display_welcome_screen()
    else:
        # Interview in progress
        display_interview_in_progress()

    # Interview ended screen
    if st.session_state.interview_ended or st.session_state.interview_terminated:
        display_interview_complete()

    # Auto-refresh logic - with safety checks
    if (
        st.session_state.interview_started
        and not st.session_state.interview_ended
        and not st.session_state.interview_terminated
        and not st.session_state.processing_answer
        and time.time() - st.session_state.last_action_time > 1
    ):  # Faster refresh rate (1 second)
        st.session_state.last_action_time = time.time()
        st.rerun()


if __name__ == "__main__":
    main()
