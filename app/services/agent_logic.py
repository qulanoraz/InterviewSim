# AI agent logic (question generation, answer evaluation) will be here 

import openai
from flask import current_app
from app.utils.logger import get_logger
import os

logger = get_logger(__name__)

# Store the client instance to avoid reinitialization on every call within the same app context
_llm_client = None

def get_llm_client():
    global _llm_client
    if _llm_client is not None:
        logger.debug("Returning existing LLM client instance.")
        return _llm_client

    logger.info("Initializing LLM client...")
    try:
        api_key = current_app.config.get('DEEPSEEK_API_KEY') # Assuming this is now the OpenRouter Key
        if not api_key:
            logger.error("DEEPSEEK_API_KEY (for OpenRouter) not found in config.")
            return None

        # Configuration for OpenRouter
        base_url = "https://openrouter.ai/api/v1"
        
        _llm_client = openai.OpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        logger.info(f"LLM client initialized for OpenRouter with key ending in '...{api_key[-4:] if api_key else 'NONE'}'.")
        return _llm_client
    except Exception as e:
        logger.error(f"Error initializing LLM client: {e}")
        _llm_client = None # Ensure client is reset on error
        return None

def _get_openrouter_headers():
    """Helper to get headers required by OpenRouter."""
    app_site_url = current_app.config.get('APP_SITE_URL', 'http://localhost:5000')
    app_name = current_app.config.get('APP_NAME', 'JobSimAI')
    return {
        "HTTP-Referer": app_site_url,
        "X-Title": app_name,
    }

def generate_interview_question(role: str, conversation_state: dict) -> str | None:
    logger.info(f"Generating interview question. Role: {role}.")
    if conversation_state is None: conversation_state = {}

    log_cv_skills = conversation_state.get('cv_skills', [])
    log_cv_experience_summary = conversation_state.get('cv_experience_summary', '')[:50]
    log_previous_qs_count = len(conversation_state.get('previous_questions', []))
    log_previous_scores = conversation_state.get('previous_scores', [])
    log_current_difficulty = conversation_state.get('current_difficulty', 'normal')
    logger.info(f"Current Conversation State for question gen: Skills: {log_cv_skills}, Exp summary: '{log_cv_experience_summary}', Prev Qs: {log_previous_qs_count}, Scores: {log_previous_scores}, Difficulty: {log_current_difficulty}")

    client = get_llm_client()
    if not client:
        logger.error("LLM client not available for question generation.")
        return None

    prompt_parts = ["You are an expert interviewer."]
    system_message = "You are an expert interviewer. Provide only the question text, no preamble. Be concise."

    cv_skills = conversation_state.get('cv_skills', [])
    cv_experience = conversation_state.get('cv_experience_summary', '')
    previous_questions = conversation_state.get('previous_questions', [])
    previous_answers = conversation_state.get('previous_answers', [])
    previous_scores = conversation_state.get('previous_scores', [])
    
    current_difficulty = conversation_state.get('current_difficulty_next', conversation_state.get('current_difficulty', 'normal'))
    conversation_state['current_difficulty'] = current_difficulty 
    if 'current_difficulty_next' in conversation_state:
        del conversation_state['current_difficulty_next']

    if previous_questions:
        last_q = previous_questions[-1]
        last_a = previous_answers[-1] if previous_answers and len(previous_answers) == len(previous_questions) else "N/A"
        last_score = previous_scores[-1] if previous_scores and len(previous_scores) == len(previous_answers) else None
        
        prompt_parts.append(f"The candidate is applying for the role of '{role}'.")
        prompt_parts.append(f"The previous question was: \"{last_q}\".")
        if last_a != "N/A":
            prompt_parts.append(f"The candidate's answer was (raw transcript): \"{last_a[:300]}...\".")
        if last_score is not None:
            prompt_parts.append(f"The candidate's score for the last answer was {last_score} out of 5.")

        if current_difficulty == 'easy':
            prompt_parts.append("The candidate seemed to struggle previously. Ask a slightly simpler follow-up, a related conceptual question on the same topic, or an easier behavioral question.")
        elif current_difficulty == 'hard':
            prompt_parts.append("The candidate did well previously. Ask a more challenging follow-up, delve deeper into a technical aspect, or present a more complex scenario.")
        else: 
            prompt_parts.append("Generate a relevant follow-up question. It can be to clarify, expand, or explore a related concept.")
        
        if cv_skills:
            skills_preview = (", ".join(cv_skills[:3])) + ('...' if len(cv_skills) > 3 else '')
            prompt_parts.append(f"If relevant, consider their CV which mentions skills like: {skills_preview}.")

    elif cv_skills:
        skills_str = (", ".join(cv_skills[:7])) + ('...' if len(cv_skills) > 7 else '')
        prompt_parts.append(f"The candidate is applying for the role of '{role}'. Their CV mentions skills such as: {skills_str}.")
        if cv_experience:
            prompt_parts.append(f"Their experience summary includes: \"{cv_experience[:300]}...\".")
        
        question_type_prompt = "Ask a behavioral question related to one of these skills or typical experiences for this role."
        technical_keywords = ['engineer', 'developer', 'software', 'technical', 'data', 'cloud', 'security']
        if any(keyword in role.lower() for keyword in technical_keywords) or len(cv_skills) > 5:
             if len(previous_questions) % 2 != 0: 
                question_type_prompt = "Ask a technical or scenario-based question that probes one of their key skills relevant to the role."
        prompt_parts.append(question_type_prompt)

        if current_difficulty == 'easy':
             prompt_parts.append("The question should be fairly straightforward and fundamental.")
        elif current_difficulty == 'hard':
             prompt_parts.append("The question can be more complex, nuanced, or require multi-step thinking.")

    else: 
        prompt_parts.append(f"The candidate is applying for the role of '{role}'.")
        prompt_parts.append("Generate a good, general opening interview question. It could be behavioral or a common role-related question.")
        if current_difficulty == 'easy':
             prompt_parts.append("The question should be fairly straightforward.")

    prompt_parts.append("The question should be a single, direct question, without any of your own conversational preamble.")
    final_prompt = "\\n".join(prompt_parts)
    logger.debug(f"Question generation prompt: {final_prompt}")

    llm_model_for_question = "deepseek/deepseek-chat-v3-0324:free"
    logger.info(f"Using model for question generation: {llm_model_for_question} with difficulty: {current_difficulty}")

    try:
        response = client.chat.completions.create(
            model=llm_model_for_question, 
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": final_prompt}
            ],
            temperature=0.75, 
            max_tokens=180,
            extra_headers=_get_openrouter_headers()
        )
        question = response.choices[0].message.content.strip()
        phrases_to_remove = ["Here is a question:", "Question:", "Here's a question:", "Okay, here is your question:", "Okay, here's a question:"]
        for phrase in phrases_to_remove:
            if question.lower().startswith(phrase.lower()):
                question = question[len(phrase):].strip()
        if not question.endswith('?') and question: # Ensure it's a question and not empty
            question += '?'
        elif not question: # Handle empty question string from LLM
            logger.warning("LLM generated an empty question string. Returning a fallback question.")
            question = "Can you tell me about a challenging project you worked on?"
        
        logger.info(f"Generated question: {question}")
        return question
    except Exception as e:
        logger.error(f"Error generating interview question: {e}")
        return None # Fallback to None, API route will handle 500 error

def evaluate_answer(question: str, transcript: str, conversation_state: dict) -> dict | None:
    logger.info(f"Evaluating answer. Question: '{question}'. Transcript (start): '{transcript[:100]}...'")
    if conversation_state is None: conversation_state = {}
    
    question_difficulty = conversation_state.get('current_difficulty', 'normal') 
    logger.info(f"Evaluating based on question_difficulty: {question_difficulty}")

    client = get_llm_client()
    if not client:
        logger.error("LLM client not available for answer evaluation.")
        return None
    
    prompt_parts = [
        f"You are an expert interview evaluator. The candidate was asked the following question for a '{conversation_state.get("role", "generic")}' role: '{question}'",
        f"The candidate's answer (raw transcript) was: '{transcript}'.",
        "Evaluate the answer based on clarity, relevance, accuracy, and depth of understanding.",
        "Provide a numeric score from 1 (poor) to 5 (excellent). The score should be a single number (e.g., 3 or 3.5).",
        "Provide brief, constructive feedback (1-3 sentences)."
    ]

    if question_difficulty == 'easy':
        prompt_parts.append("This question was intended to be relatively straightforward. Evaluate if the core concept was addressed adequately, even if simply.")
    elif question_difficulty == 'hard':
        prompt_parts.append("This was intended as a more challenging question. Assess the depth, sophistication, and handling of complexity in the answer.")

    prompt_parts.append("Return ONLY a valid JSON object with two keys: 'score' (a float or int, e.g., 3 or 3.5) and 'feedback' (a string).")
    prompt_parts.append("Example JSON: { \"score\": 4.0, \"feedback\": \"The answer was clear and relevant, demonstrating good understanding. Could provide more specific examples next time.\" }")
    
    final_prompt = "\\n".join(prompt_parts)
    logger.debug(f"Evaluation prompt: {final_prompt}")

    llm_model_for_evaluation = "deepseek/deepseek-chat-v3-0324:free"
    logger.info(f"Using model for evaluation: {llm_model_for_evaluation}")

    try:
        response = client.chat.completions.create(
            model=llm_model_for_evaluation, 
            messages=[
                {"role": "system", "content": "You are an expert interview evaluator. Only return the JSON object as specified."},
                {"role": "user", "content": final_prompt}
            ],
            response_format={ "type": "json_object" },
            temperature=0.25, 
            extra_headers=_get_openrouter_headers()
        )
        evaluation_str = response.choices[0].message.content
        logger.info(f"Received evaluation from LLM: {evaluation_str}")
        
        import json
        try:
            evaluation = json.loads(evaluation_str)
            if not isinstance(evaluation.get('score'), (int, float)) or \
               not isinstance(evaluation.get('feedback'), str):
                logger.error(f"LLM returned malformed JSON for evaluation. Data: {evaluation}")
                return {"score": 1.0, "feedback": "Error: Malformed evaluation data from AI."}
            
            score = float(evaluation.get('score', 1.0))
            evaluation['score'] = max(1.0, min(5.0, score)) 
            
            next_difficulty = question_difficulty
            if evaluation['score'] < 2.5 and question_difficulty != 'easy':
                next_difficulty = 'easy'
            elif evaluation['score'] >= 4.0 and question_difficulty != 'hard':
                next_difficulty = 'hard'
            elif evaluation['score'] >= 2.5 and evaluation['score'] < 4.0: 
                next_difficulty = 'normal'
            
            conversation_state['current_difficulty_next'] = next_difficulty
            logger.info(f"Score: {evaluation['score']}. Difficulty for NEXT question set to: {next_difficulty}")

            return evaluation
        except json.JSONDecodeError as json_e:
            logger.error(f"JSON decoding failed for LLM evaluation response: {json_e}. Raw response: {evaluation_str}")
            return {"score": 1.0, "feedback": "Error: AI returned invalid JSON format for evaluation."}
        except Exception as e_inner:
            logger.error(f"Inner error processing evaluation response: {e_inner}. Raw: {evaluation_str}")
            return {"score": 1.0, "feedback": "Error processing evaluation data."}

    except Exception as e:
        logger.error(f"Error evaluating answer: {e}")
        return None

# Example Usage (for testing purposes):
# if __name__ == '__main__':
#     pass 