# interview_manager.py
import json
import time
from datetime import datetime
from llm_runner import LLMRunner
from config import JOB_ROLE_PROMPTS, INTERVIEW_CONFIG
import logging

logger = logging.getLogger(__name__)


class InterviewManager:
    def __init__(self, job_role, candidate_name=""):
        self.job_role = job_role
        self.candidate_name = candidate_name
        self.llm = LLMRunner()
        self.interview_id = f"{job_role.replace(' ', '_')}_{int(time.time())}"

        # Get job-specific prompts
        job_key = job_role.lower().replace(" ", "_")
        self.prompts = JOB_ROLE_PROMPTS.get(job_key, JOB_ROLE_PROMPTS["default"])

        self.session_data = {
            "job_role": job_role,
            "candidate_name": candidate_name,
            "start_time": datetime.now().isoformat(),
            "questions_asked": [],
            "candidate_answers": [],
            "current_question_index": 0,
            "status": "in_progress",
            "evaluation_notes": [],
            "answer_analysis": [],
            "conversation_history": [],
        }

        # Create session directory
        self.session_dir = f"interview_sessions/{self.interview_id}"
        import os

        os.makedirs(self.session_dir, exist_ok=True)

        logger.info(f"✅ Interview started for {job_role}, Candidate: {candidate_name}")

    def get_opening_question(self):
        """Get the predefined opening question"""
        opening = self.prompts["opening"]
        self.session_data["questions_asked"].append(opening)
        self.session_data["current_question_index"] = 1
        self.session_data["conversation_history"].append(("AI Interviewer", opening))
        self.save_interview_data()
        return opening

    def should_progress_to_next_answer(self, current_answer, current_question):
        """Determine if answer is sufficient to move to next question"""

        relevance_prompt = f"""
        Analyze if this answer for {self.job_role} position is sufficient to move to next question.
        
        QUESTION: {current_question}
        ANSWER: {current_answer}
        
        Criteria for sufficient answer:
        - Directly addresses the question asked
        - Provides relevant information or experience related to {self.job_role}
        - Has reasonable length and detail (not too short/vague)
        - Shows understanding of the topic
        - Contains specific examples or explanations
        
        If the answer meets these criteria and seems complete, respond with YES.
        If the answer is incomplete, irrelevant, or too brief, respond with NO.
        
        Respond with ONLY: YES or NO
        
        Analysis:"""

        try:
            response = self.llm.ask(relevance_prompt)
            logger.info(f"🤖 Answer relevance check: {response.strip()}")
            return "YES" in response.upper().strip()
        except Exception as e:
            logger.error(f"❌ Error checking answer relevance: {e}")
            # Fallback: auto-progress if answer has reasonable length
            return len(current_answer.strip()) > 50

    def analyze_answer_and_generate_question(
        self, current_question, candidate_answer, conversation_history
    ):
        """ANALYZE answer + GENERATE next question in one call"""

        logger.info(f"🔍 Analyzing answer and generating next question...")

        # COMBINED PROMPT: Analysis + Next Question Generation
        combined_prompt = f"""You are conducting a {self.job_role} interview. 

PREVIOUS QUESTION: {current_question}
CANDIDATE'S ANSWER: {candidate_answer}

CONVERSATION HISTORY:
{conversation_history}

INSTRUCTIONS:
1. First, briefly analyze the candidate's answer (2-3 sentences). Focus on:
   - What key information/skills did they reveal?
   - What was the quality of their response?
   - Any notable strengths or areas for follow-up?

2. Then, generate the NEXT interview question that:
   - Builds naturally on the conversation
   - Explores relevant {self.job_role} skills
   - Is professional and clear
   - Moves the interview forward

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
ANALYSIS: [Your analysis here]
NEXT_QUESTION: [Your next question here]

Now process this response:"""

        try:
            response = self.llm.ask(combined_prompt)
            logger.info(f"🤖 LLM Response received")

            # Parse the response
            analysis = ""
            next_question = ""

            if "ANALYSIS:" in response and "NEXT_QUESTION:" in response:
                parts = response.split("NEXT_QUESTION:")
                analysis_part = parts[0].replace("ANALYSIS:", "").strip()
                question_part = parts[1].strip()

                analysis = analysis_part
                next_question = question_part
            else:
                # Fallback parsing
                lines = response.split("\n")
                analysis = lines[0] if lines else "Analysis not available."
                next_question = (
                    "Could you tell me more about your experience in this area?"
                    if len(lines) < 2
                    else lines[1]
                )

            logger.info(f"📊 Analysis generated")
            logger.info(f"🎯 Next Question generated")

            return analysis, next_question

        except Exception as e:
            logger.error(f"❌ Error in analyze_answer_and_generate_question: {e}")
            fallback_analysis = "The candidate provided an answer. Continuing with standard interview questions."
            fallback_question = (
                "Could you tell me more about your experience with that?"
            )
            return fallback_analysis, fallback_question

    def save_interview_data(self):
        """Save interview data to JSON file"""
        try:
            data_file = f"{self.session_dir}/interview_data.json"
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(self.session_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Error saving interview data: {e}")

    def add_qa_pair(self, question, answer, transcription=""):
        """Process answer and generate next question"""
        logger.info("🔄 Processing Q&A pair and generating next question...")

        # Build conversation history for context
        conversation_text = "\n".join(
            [
                f"{speaker}: {text}"
                for speaker, text in self.session_data["conversation_history"]
            ]
        )

        # STEP 1 + STEP 2: Analyze answer AND generate next question
        analysis, next_question = self.analyze_answer_and_generate_question(
            question, answer, conversation_text
        )

        # Save the Q&A pair with analysis
        qa_pair = {
            "question": question,
            "answer": answer,
            "transcription": transcription,
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis,
            "next_question": next_question,
        }

        # Update session data
        self.session_data["candidate_answers"].append(qa_pair)
        self.session_data["answer_analysis"].append(analysis)
        self.session_data["questions_asked"].append(next_question)
        self.session_data["current_question_index"] += 1
        self.session_data["conversation_history"].append(("Candidate", answer))
        self.session_data["conversation_history"].append(
            ("AI Interviewer", next_question)
        )

        self.save_interview_data()

        logger.info(f"✅ Q&A processed. Next question: {next_question}")
        return qa_pair, next_question

    def get_interview_summary(self):
        """Get interview progress summary"""
        total_questions = len(self.session_data["questions_asked"])
        return {
            "total_questions": total_questions,
            "progress": f"{total_questions}/{INTERVIEW_CONFIG['max_questions']}",
            "candidate_name": self.candidate_name,
            "job_role": self.job_role,
        }

    def end_interview(self):
        """End the interview"""
        self.session_data["status"] = "completed"
        self.session_data["end_time"] = datetime.now().isoformat()
        self.save_interview_data()

        logger.info("🏁 Interview ended")
        return "Thank you for completing the interview! Your responses have been recorded and will be reviewed."
