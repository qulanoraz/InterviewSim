# AI agent logic (question generation, answer evaluation) will be here 

import openai
from flask import current_app
from app.utils.logger import get_logger
import os
import re

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

    # Prepare context for logging (truncate long strings)
    log_cv_skills = str(conversation_state.get('cv_skills', []))[:100]
    cv_experience_summary_for_log = conversation_state.get('cv_experience_summary') # Get the value, might be None
    log_cv_experience_summary = (cv_experience_summary_for_log or '')[:50]         # Use 'or' to default to empty string if None/empty
    log_previous_qs_count = len(conversation_state.get('previous_questions', []))
    log_previous_scores = conversation_state.get('previous_scores', [])
    log_current_difficulty = conversation_state.get('current_difficulty', 'normal')
    logger.info(f"Current Conversation State for question gen: Skills: {log_cv_skills}, Exp summary: '{log_cv_experience_summary}', Prev Qs: {log_previous_qs_count}, Scores: {log_previous_scores}, Difficulty: {log_current_difficulty}")

    client = get_llm_client()
    if not client:
        logger.error("LLM client not available for question generation.")
        return None

    prompt_parts = ["You are an expert interviewer."]
    system_message = "You are an expert interviewer. Provide only the question text, in English, no preamble. Be concise."

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
        
        # Check for common refusal phrases in question generation
        refusal_phrases_question = [
            "i cannot", "i'm unable to", "i am unable to", "i'm sorry, but i cannot", 
            "as an ai assistant, i cannot", "policy violation", "controversial", 
            "inappropriate", "i am not programmed to", "i'm not supposed to",
            "generate a question on that topic"
        ]
        if any(phrase in question.lower() for phrase in refusal_phrases_question):
            logger.warning(f"LLM refusal detected during question generation: {question}")
            # Potentially return a specific fallback question or None to indicate failure
            # For now, returning None will trigger the 500 error in routes.py, which is acceptable for a refusal to generate.
            return None 

        phrases_to_remove = ["Here is a question:", "Question:", "Here\'s a question:", "Okay, here is your question:", "Okay, here\'s a question:"]
        for phrase in phrases_to_remove:
            if question.lower().startswith(phrase.lower()):
                question = question[len(phrase):].strip()
        
        # More robust cleaning: strip leading/trailing quotes and asterisks
        question = question.strip('\"*') 

        # Remove leading numbering (e.g., "1. ", "a) ")
        # This regex matches patterns like "1. ", "1) ", "a. ", "A. ", "a) ", "A) " or markdown list markers "* ", "- " or "+ "
        # It also handles optional leading whitespace before the number/letter.
        question = re.sub(r"^\s*[\d\w][\.\)]\s+", "", question).strip()
        # Additional check for markdown style list like "- Question text" or "* Question text"
        if question.startswith("- ") or question.startswith("* ") or question.startswith("+ "):
            question = question[2:].strip()

        if not question.endswith('?') and question: # Ensure it's a question and not empty
            question += '?'
        elif not question: # Handle empty question string from LLM
            logger.warning("LLM generated an empty question string. Returning a fallback question.")
            question = "Can you tell me about a challenging project you worked on?"
        
        logger.info(f"Generated question: {question}")
        return question
    except openai.APIError as e:
        logger.error(f"OpenAI APIError generating interview question: {e.status_code=}, {e.response=}, {e.body=}, {e.request=}")
        return None # Fallback to None, API route will handle 500 error
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
        
        # Check for common refusal phrases
        refusal_phrases = [
            "i cannot", "i'm unable to", "i am unable to", "i'm sorry, but i cannot", 
            "as an ai assistant, i cannot", "policy violation", "controversial", 
            "inappropriate", "i am not programmed to", "i'm not supposed to"
        ]
        # Check in lowercase to be case-insensitive
        if any(phrase in evaluation_str.lower() for phrase in refusal_phrases):
            # Try to extract a more specific refusal message if possible, otherwise use a generic one
            # This is a simple heuristic; more sophisticated extraction might be needed if LLM varies a lot
            first_sentence_of_refusal = evaluation_str.split('.')[0]
            user_friendly_refusal = f"Evaluation failed: {first_sentence_of_refusal}." \
                if len(first_sentence_of_refusal) < 150 else "Evaluation failed: The AI declined to process this request due to content policies."

            logger.warning(f"LLM refusal detected in evaluation: {evaluation_str}")
            return {"score": 0, "feedback": user_friendly_refusal, "refusal": True, "raw_llm_response": evaluation_str}

        # Attempt to extract the JSON part, discarding any preceding text
        cleaned_evaluation_str = evaluation_str.strip()
        
        json_block_start_indices = [
            cleaned_evaluation_str.find("```json"),
            cleaned_evaluation_str.find("```"),
            cleaned_evaluation_str.find("{") 
        ]
        
        actual_start_index = -1
        for index in json_block_start_indices:
            if index != -1:
                actual_start_index = index
                break
        
        if actual_start_index != -1:
            cleaned_evaluation_str = cleaned_evaluation_str[actual_start_index:]
            logger.info(f"Extracted potential JSON block: {cleaned_evaluation_str[:200]}...") # Log first 200 chars
        else:
            logger.warning(f"Could not find a clear JSON block start in LLM response: {evaluation_str}")
            # Fallback to old behavior if no clear start is found, though it might still fail
            pass # cleaned_evaluation_str remains the initially stripped full string

        # Strip markdown code fences if present (applied to the extracted block)
        if cleaned_evaluation_str.startswith("```json"):
            cleaned_evaluation_str = cleaned_evaluation_str[len("```json"):].strip()
        if cleaned_evaluation_str.startswith("```"):
            cleaned_evaluation_str = cleaned_evaluation_str[len("```"):].strip()
        if cleaned_evaluation_str.endswith("```"):
            cleaned_evaluation_str = cleaned_evaluation_str[:-len("```")].strip()

        # Ensure the string is a valid JSON object (starts with { and ends with })
        # Applied after potential Markdown stripping and extraction
        if cleaned_evaluation_str.startswith("\"") and \
           not cleaned_evaluation_str.startswith("{") and \
           not cleaned_evaluation_str.endswith("}"):
            logger.info("Attempting to wrap incomplete JSON (starts with quote) with curly braces.")
            cleaned_evaluation_str = f"{{{cleaned_evaluation_str}}}"
        elif not cleaned_evaluation_str.startswith("{") and cleaned_evaluation_str.strip(): # If not empty and no opening brace
             logger.warning(f"Evaluation string does not start with '{{'. Original: {evaluation_str}, Cleaned Attempt: {cleaned_evaluation_str}")
             # Consider if prepending '{' is safe or if it indicates a deeper issue
        elif not cleaned_evaluation_str.endswith("}") and cleaned_evaluation_str.strip(): # If not empty and no closing brace
             logger.warning(f"Evaluation string does not end with '}}'. Original: {evaluation_str}, Cleaned Attempt: {cleaned_evaluation_str}")
             # Consider if appending '}' is safe

        import json
        try:
            evaluation = json.loads(cleaned_evaluation_str)
            if not isinstance(evaluation.get('score'), (int, float)) or \
               not isinstance(evaluation.get('feedback'), str):
                logger.error(f"LLM returned malformed JSON for evaluation. Data: {evaluation}. Original: {evaluation_str}")
                # Return the raw string if it's not structured as expected, so it can be seen by user if necessary
                return {"score": 1.0, "feedback": f"Error: Malformed evaluation data from AI. Response: {cleaned_evaluation_str[:200]}", "refusal": False, "raw_llm_response": evaluation_str}
            
            score = float(evaluation.get('score', 1.0))
            evaluation['score'] = max(1.0, min(5.0, score)) 
            evaluation['refusal'] = False # Explicitly set refusal to false for successful parses
            evaluation['raw_llm_response'] = evaluation_str # Include for debugging

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
            logger.error(f"JSON decoding failed for LLM evaluation response: {json_e}. Raw response: {evaluation_str} (Cleaned: {cleaned_evaluation_str})")
            # Return the raw string if it's not structured as expected
            return {"score": 1.0, "feedback": f"Error: AI returned non-JSON format for evaluation. Response: {cleaned_evaluation_str[:200]}", "refusal": True, "raw_llm_response": evaluation_str} # Treat decode error as a type of refusal/failure
        except Exception as e_inner:
            logger.error(f"Inner error processing evaluation response: {e_inner}. Raw: {evaluation_str} (Cleaned: {cleaned_evaluation_str})")
            return {"score": 1.0, "feedback": f"Error processing evaluation data. Response: {cleaned_evaluation_str[:200]}", "refusal": True, "raw_llm_response": evaluation_str} # Treat other errors as refusal too

    except openai.APIError as e:
        logger.error(f"OpenAI APIError evaluating answer: {e.status_code=}, {e.response=}, {e.body=}, {e.request=}")
        return {"score": 0, "feedback": f"Evaluation failed due to API error: {e.status_code}", "refusal": True, "raw_llm_response": str(e.body) if e.body else "API Error"}
    except Exception as e:
        logger.error(f"Error evaluating answer: {e}")
        return {"score": 0, "feedback": "Evaluation failed due to an unexpected error.", "refusal": True, "raw_llm_response": str(e)}

# Example Usage (for testing purposes):
# if __name__ == '__main__':
#     pass 