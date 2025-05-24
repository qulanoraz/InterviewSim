# API routes will be defined here 

from flask import Blueprint, request, jsonify, current_app
from app.services import deepgram_service, agent_logic
from app.utils.logger import get_logger

logger = get_logger(__name__)

api_bp = Blueprint('api', __name__)

@api_bp.route('/interview', methods=['POST'])
def interview_endpoint():
    """
    Handles the /interview POST request.
    Accepts JSON: {"role": "str", "audio": "base64_wav_str"}
    Returns JSON: {"question": "str", "transcript": "str", "evaluation": {"score": float, "feedback": "str"}}
    """
    logger.info(f"Received request for /api/interview. Method: {request.method}")

    if not request.is_json:
        logger.warning("Request is not JSON")
        return jsonify({"error": "Invalid request: Content-Type must be application/json"}), 415

    data = request.get_json()
    logger.debug(f"Request JSON data (audio snippet): {{'role': '{data.get('role')}', 'audio': '{data.get('audio', '')[:20]}...'}}")

    role = data.get('role')
    audio_base64 = data.get('audio')

    if not role or not isinstance(role, str):
        logger.error("Missing or invalid 'role' in request payload")
        return jsonify({"error": "Missing or invalid 'role' in request payload. It must be a string."}), 400
    
    if not audio_base64 or not isinstance(audio_base64, str):
        logger.error("Missing or invalid 'audio' in request payload")
        return jsonify({"error": "Missing or invalid 'audio' in request payload. It must be a base64 encoded string."}), 400

    logger.info("Transcribing audio...")
    transcript = deepgram_service.transcribe_audio(audio_base64)
    if transcript is None:
        logger.error("Audio transcription failed.")
        return jsonify({"error": "Audio transcription failed. Check logs for details."}), 500
    logger.info(f"Transcription successful: '{transcript[:50]}...'")

    logger.info(f"Generating interview question for role: {role}")
    generated_question = agent_logic.generate_interview_question(role)
    if generated_question is None:
        logger.error("Failed to generate interview question.")
        return jsonify({"error": "Failed to generate interview question. Check logs for details."}), 500
    logger.info(f"Generated question: '{generated_question}'")

    logger.info("Evaluating answer...")
    evaluation = agent_logic.evaluate_answer(question=generated_question, transcript=transcript)
    if evaluation is None:
        logger.error("Failed to evaluate answer.")
        return jsonify({"error": "Failed to evaluate answer. Check logs for details."}), 500
    logger.info(f"Evaluation successful: {evaluation}")

    response_payload = {
        "question": generated_question,
        "transcript": transcript,
        "evaluation": evaluation
    }
    logger.info(f"Sending response: {response_payload}")
    return jsonify(response_payload), 200

# Example of a simple health check endpoint for the API blueprint
@api_bp.route('/health', methods=['GET'])
def health_check():
    logger.info("API health check successful")
    return jsonify({"status": "API is healthy"}), 200 