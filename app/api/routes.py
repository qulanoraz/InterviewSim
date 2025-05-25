# API routes will be defined here 

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from io import BytesIO
import os

from app.services import deepgram_service, agent_logic, cv_parser_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

api_bp = Blueprint('api', __name__)

# Temp storage for CV data for simplicity in this phase. 
# In a real app, this would be tied to a user session or database.
# This is NOT suitable for concurrent users or production.
cv_data_store = {}
current_conversation_id_HACK = "default_user" # HACK for single user testing

ALLOWED_CV_EXTENSIONS = {'txt', 'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_CV_EXTENSIONS

@api_bp.route('/interview', methods=['POST'])
def interview_endpoint():
    logger.critical("--- /api/interview endpoint CALLED ---")
    logger.info(f"Received request for /api/interview. Method: {request.method}")
    
    # HACK: Using a global conversation ID for now
    session_id = current_conversation_id_HACK 
    if session_id not in cv_data_store:
        cv_data_store[session_id] = {
            "cv_skills": None, 
            "cv_experience_summary": None,
            "previous_questions": [],
            "previous_answers": [],
            "previous_scores": [],
            "current_difficulty": "normal"
        }
    
    conversation_state = cv_data_store[session_id]

    # Try to get data as JSON first (for subsequent calls with audio)
    # And from form-data (for initial call with CV + role + audio, or just CV + role)
    data = {}
    role = None
    audio_base64 = None
    cv_file = None

    if request.content_type.startswith('application/json'):
        data = request.get_json()
        role = data.get('role')
        audio_base64 = data.get('audio')
        logger.debug(f"Request JSON data: { {key: (value[:20] + '...' if isinstance(value, str) and len(value) > 20 else value) for key, value in data.items()} }")
    elif request.content_type.startswith('multipart/form-data'):
        role = request.form.get('role')
        # Audio might also come as a file in form-data, or as base64 in form field
        # For now, assuming audio comes as base64 in form field if CV is also present
        audio_base64 = request.form.get('audio') 
        if 'cv' in request.files:
            cv_file = request.files['cv']
            logger.info(f"CV file received: {cv_file.filename}")
        logger.debug(f"Request form data: role='{role}', cv_file='{cv_file.filename if cv_file else None}', audio_base64_present={'Yes' if audio_base64 else 'No'}")
    else:
        logger.warning(f"Unsupported Content-Type: {request.content_type}")
        return jsonify({"error": "Unsupported Content-Type. Must be application/json or multipart/form-data"}), 415

    if not role or not isinstance(role, str):
        logger.error("Missing or invalid 'role' in request.")
        return jsonify({"error": "Missing or invalid 'role'. It must be a string."}), 400

    # CV Processing (if a CV file is provided and not already processed)
    if cv_file and cv_file.filename != '' and allowed_file(cv_file.filename):
        if conversation_state["cv_skills"] is None: # Process only if not already done
            filename = secure_filename(cv_file.filename)
            logger.info(f"Processing CV file: {filename}")
            try:
                file_stream = BytesIO(cv_file.read())
                cv_text = cv_parser_service.extract_text_from_cv(filename, file_stream)
                if cv_text:
                    logger.info(f"CV text extracted (length: {len(cv_text)}). Now extracting skills/experience.")
                    extracted_info = cv_parser_service.extract_skills_and_experience(cv_text)
                    conversation_state["cv_skills"] = extracted_info.get("skills")
                    conversation_state["cv_experience_summary"] = extracted_info.get("experience_summary")
                    logger.info(f"CV skills extracted: {conversation_state['cv_skills']}")
                    logger.info(f"CV experience summary: {conversation_state['cv_experience_summary'][:100]}...")
                else:
                    logger.error(f"Could not extract text from CV: {filename}")
                    # Optionally, inform the user in the response that CV processing failed
            except Exception as e:
                logger.error(f"Error processing CV file '{filename}': {e}")
                # Optionally, inform the user in the response that CV processing failed
        else:
            logger.info("CV data already processed for this session.")
    elif cv_file and cv_file.filename != '' and not allowed_file(cv_file.filename):
        logger.warning(f"CV file extension not allowed: {cv_file.filename}")
        # Optionally return an error, or just ignore the CV, or inform user

    # --- MODIFIED AUDIO REQUIREMENT LOGIC START ---
    if not audio_base64:
        # Audio can be omitted if:
        # 1. A CV file is part of the current request, and it's for the first question (implies skills might be processed now or were just processed).
        # 2. No CV file is part of the current request, and it's the very first question (no prior questions asked).
        
        is_first_ever_question = not conversation_state["previous_questions"]

        if cv_file and is_first_ever_question:
            logger.info("CV is present in the request, and it's for the first question. Audio is optional here.")
            # Proceed without audio, CV will be processed, then first question generated.
        elif not cv_file and is_first_ever_question:
            logger.info("No CV in the request, and it's the first question. Audio is optional here.")
            # Proceed without audio, first question will be generated based on role.
        else:
            # Audio is missing, and we are past the point where it can be omitted (e.g., subsequent questions).
            logger.error("Missing 'audio' in request. Audio is required for ongoing interview turns if not an initial CV submission for the first question.")
            return jsonify({"error": "Missing 'audio' in request payload for an ongoing interview turn."}), 400
    # --- MODIFIED AUDIO REQUIREMENT LOGIC END ---
    
    transcript = "" 
    if audio_base64 and isinstance(audio_base64, str):
        logger.info("Transcribing audio...")
        transcript_result = deepgram_service.transcribe_audio(audio_base64)
        if transcript_result is None:
            logger.error("Audio transcription failed.")
            return jsonify({"error": "Audio transcription failed. Check logs for details."}), 500
        transcript = transcript_result 
        logger.info(f"Transcription successful: '{transcript[:50]}...'")
        # Store answer only if it corresponds to a previous question
        if conversation_state["previous_questions"]:
            conversation_state["previous_answers"].append(transcript)
        else:
            # This might be an initial audio without a prior question (e.g. if CV was processed in a separate step not yet implemented)
            logger.info("Transcript received, but no prior question in state. Storing as first answer.")
            conversation_state["previous_answers"].append(transcript) # Or handle as an unexpected state
            
    elif not audio_base64 and cv_file and conversation_state["cv_skills"] is not None:
        logger.info("CV processed (or was already processed), no audio in this request. Preparing first question based on CV if available.")
    
    evaluation = None
    if transcript and conversation_state["previous_questions"]:
        # Only evaluate if there's a transcript AND a question it's an answer to.
        # Ensure we have a question to evaluate against. current_question_for_state might be from a *previous* turn if this is an audio-only submission.
        question_to_evaluate = conversation_state["previous_questions"][-1] 
        # if len(conversation_state["previous_answers"]) == len(conversation_state["previous_questions"]):
        #     question_to_evaluate = conversation_state["previous_questions"][-1]
        # else:
            # This case might mean an answer was stored but question for it wasn't, or logic error
            # logger.warning("Mismatch between previous answers and questions count during evaluation setup.")
            # For now, assume the last question is the one being answered.

        logger.info(f"Evaluating answer for question: '{question_to_evaluate}'")
        evaluation = agent_logic.evaluate_answer(
            question=question_to_evaluate, 
            transcript=transcript, 
            conversation_state=conversation_state # Pass full state
        ) 
        if evaluation is None:
            logger.error("Failed to evaluate answer (agent_logic returned None unexpectedly).")
            evaluation = {"score": 0, "feedback": "Evaluation failed unexpectedly.", "refusal": True, "raw_llm_response": "Agent logic returned None"}
        else:
            logger.info(f"Evaluation result: {evaluation}")
            # Only append score if it was a valid evaluation (not a refusal or a forced error score)
            if not evaluation.get("refusal", False) and isinstance(evaluation.get("score"), (int, float)) and evaluation.get('score') > 0:
                conversation_state["previous_scores"].append(evaluation["score"])
            elif evaluation.get("refusal", False):
                logger.info("Evaluation was a refusal. Score not recorded.")
            else:
                logger.info(f"Invalid or zero score not recorded: {evaluation.get('score')}")
    
    logger.info(f"Generating interview question for role: {role}, using conversation state.")
    generated_question = agent_logic.generate_interview_question(
        role=role, 
        conversation_state=conversation_state # Pass full state
    )
    
    if generated_question is None:
        logger.error("Failed to generate interview question.")
        return jsonify({"error": "Failed to generate interview question. Check logs for details."}), 500
    logger.info(f"Generated question: '{generated_question}'")
    conversation_state["previous_questions"].append(generated_question)

    response_payload = {
        "question": generated_question,
        "transcript": transcript if transcript else ("N/A (CV processed, awaiting first answer)" if conversation_state.get("cv_skills") else "N/A"),
        "evaluation": evaluation if evaluation else ("N/A (CV processed or no audio/prior question for evaluation)" if conversation_state.get("cv_skills") or not transcript else ("N/A (no audio for evaluation)")),
        "cv_summary_debug": {"skills": conversation_state.get("cv_skills"), "experience": conversation_state.get("cv_experience_summary")}
    }
    logger.info(f"Sending response: {response_payload}")
    return jsonify(response_payload), 200

# Example of a simple health check endpoint for the API blueprint
@api_bp.route('/health', methods=['GET'])
def health_check():
    logger.info("API health check successful")
    return jsonify({"status": "API is healthy"}), 200 