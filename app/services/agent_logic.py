# AI agent logic (question generation, answer evaluation) will be here 

import openai
from flask import current_app
from app.utils.logger import get_logger

logger = get_logger(__name__)

def get_llm_client():
    # DEEPSEEK_API_KEY is used for the OpenRouter key when configured for OpenRouter
    api_key = current_app.config.get('DEEPSEEK_API_KEY') 
    
    if api_key and api_key.strip():
        key_to_log = api_key.strip()
        logger.debug(f"DEBUG: Using OpenRouter API Key (DEEPSEEK_API_KEY): 'sk-...{key_to_log[-4:]}' (last 4 chars)")
        logger.debug(f"DEBUG: Length of key: {len(key_to_log)}")
        if len(key_to_log) < 10:
             logger.debug(f"DEBUG: WARNING - API Key seems very short.")
    else:
        logger.debug("DEBUG: OpenRouter API Key (DEEPSEEK_API_KEY) is missing, empty, or whitespace before client init.")

    if not api_key or not api_key.strip():
        logger.error("OpenRouter API key (configured as DEEPSEEK_API_KEY) not found, is empty, or whitespace.")
        return None
    
    # Initialize client for OpenRouter
    return openai.OpenAI(
        api_key=api_key.strip(),
        base_url="https://openrouter.ai/api/v1"
    )

def _get_optional_openrouter_headers():
    return {
        "HTTP-Referer": current_app.config.get('APP_SITE_URL', 'http://localhost:5000'),
        "X-Title": current_app.config.get('APP_NAME', 'JobSim AI')
    }

def generate_interview_question(role: str) -> str | None:
    client = get_llm_client()
    if not client:
        return None

    optional_headers = _get_optional_openrouter_headers()

    try:
        logger.info(f"Generating interview question for role: {role} via OpenRouter")
        prompt = (
            f"Generate one behavioral or technical interview question suitable for a "
            f"'{role}' position. The question should be insightful and allow the candidate "
            f"to demonstrate their skills and experience. Do not ask for lists (e.g. \"list three things\"). "
            f"Phrase it as a direct question a human interviewer would ask."
        )
        
        response = client.chat.completions.create(
            model="deepseek/deepseek-chat-v3-0324:free", # OpenRouter model name
            messages=[
                {"role": "system", "content": "You are an expert interviewer generating concise, high-quality interview questions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.7,
            extra_headers=optional_headers 
        )
        question = response.choices[0].message.content.strip()
        logger.info(f"Generated question (OpenRouter/Deepseek): {question}")
        return question
    except Exception as e:
        logger.error(f"Error generating interview question (OpenRouter/Deepseek): {e}")
        return None

def evaluate_answer(question: str, transcript: str) -> dict | None:
    client = get_llm_client()
    if not client:
        return None

    optional_headers = _get_optional_openrouter_headers()

    try:
        logger.info(f"Evaluating answer for question: '{question}' via OpenRouter")
        prompt = (
            f"The user was asked the following interview question: \"{question}\".\n"
            f"The user provided this answer: \"{transcript}\".\n\n"
            f"Please evaluate the answer. Provide a numeric score from 1.0 to 10.0 (e.g., 7.5) "
            f"representing the quality of the answer, and provide concise, constructive feedback "
            f"(2-3 sentences). The feedback should highlight strengths and suggest areas for improvement. "
            f"Focus on clarity, relevance to the question, and completeness. "
            f"Return ONLY a JSON object with two keys: 'score' (float) and 'feedback' (string). "
            f"Example: {{ \"score\": 8.0, \"feedback\": \"Great example of problem-solving. Consider quantifying the impact next time.\" }}"
        )

        response = client.chat.completions.create(
            model="deepseek/deepseek-chat-v3-0324:free", # OpenRouter model name
            messages=[
                {"role": "system", "content": "You are an expert interview coach providing answer evaluations. You must return only a valid JSON object as specified."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" },
            max_tokens=200,
            temperature=0.5,
            extra_headers=optional_headers
        )
        
        evaluation_str = response.choices[0].message.content
        logger.info(f"Received evaluation (OpenRouter/Deepseek): {evaluation_str}")
        
        import json
        evaluation_data = json.loads(evaluation_str)
        
        if not isinstance(evaluation_data.get('score'), (int, float)) or \
           not isinstance(evaluation_data.get('feedback'), str):
            logger.error("LLM (OpenRouter/Deepseek) returned malformed JSON for evaluation.")
            return {"score": 0.0, "feedback": "Error processing evaluation from AI. Please try again."}
            
        return evaluation_data
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding error for evaluation (OpenRouter/Deepseek): {e}. LLM output: {evaluation_str}")
        return {"score": 0.0, "feedback": "AI evaluation was not in the expected format. Please try again."}
    except Exception as e:
        logger.error(f"Error evaluating answer (OpenRouter/Deepseek): {e}")
        return None

# Example Usage (for testing purposes):
# if __name__ == '__main__':
#     pass 