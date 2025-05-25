# Cursor Logs for JobSim AI Backend

## Initial Plan Phase
- Defined project structure and core components.
- Outlined steps for creating Flask backend, services, and API endpoint.

## Execution Phase - Project Setup
- Creating initial directory structure.
- Creating requirements.txt.
- Creating .env template.
- Implemented `config.py` for application configuration and environment variable management.
- Implemented basic `app/utils/logger.py`.
- Implemented Application Factory in `app/__init__.py`.
- Implemented `app/services/deepgram_service.py` for audio transcription.
- Implemented `app/services/agent_logic.py` for LLM-based question generation and answer evaluation.
- Implemented API routes in `app/api/routes.py` including the `/interview` endpoint and a health check.
- Implemented `run.py` as the application entry point.

## Task: Switch LLM to OpenRouter (using Deepseek via OpenRouter)
- Modified `app/services/agent_logic.py` to use OpenRouter API:
    - Changed base URL to `https://openrouter.ai/api/v1`.
    - Updated model name to OpenRouter specific identifier (e.g., `deepseek/deepseek-chat`).
    - The existing `DEEPSEEK_API_KEY` from `.env` will be used as the OpenRouter API key.

## Task: Troubleshoot OpenRouter 401 Error ("No auth credentials found")
- Modified `app/services/agent_logic.py` to explicitly set `Authorization: Bearer <key>` header and add `HTTP-Referer` & `X-Title` in `default_headers` for the OpenAI client when targeting OpenRouter.
- Updated `config.py` to load `APP_SITE_URL` and `APP_NAME` from environment variables for these headers.

## Task: Further Troubleshoot OpenRouter 401 Error
- Modified `get_llm_client` in `app/services/agent_logic.py` to pass `api_key=None` to `OpenAI()` constructor, relying solely on `default_headers` for authorization. Also stripped whitespace from API key used in header and enhanced initial API key check.

## Task: Align OpenRouter Auth with Standard OpenAI Library Usage
- Reverted `get_llm_client` in `app/services/agent_logic.py` to pass the OpenRouter API key directly to the `api_key` parameter of the `OpenAI()` constructor. Removed explicit `Authorization` from `default_headers`.
- Updated the model name to `deepseek/deepseek-chat-v3-0324:free` based on OpenRouter documentation screenshot.

## Task: Add Debugging for Persistent OpenRouter 401 Error
- Added print statements in `get_llm_client` in `app/services/agent_logic.py` to display the last 4 characters of the loaded API key and check for empty/short keys to verify correct loading from `.env`.

## Task: Align OpenRouter API Calls with Documentation Example
- Modified `app/services/agent_logic.py` based on OpenRouter's `openai-python` example:
    - `OpenAI` client initialized with only `api_key` and `base_url`.
    - Optional headers (`HTTP-Referer`, `X-Title`) moved from `default_headers` during client init to `extra_headers` parameter in `client.chat.completions.create()` calls.

## Task: Fix ImportError for logger and standardize logging
- Modified `app/services/deepgram_service.py`, `app/services/agent_logic.py`, and `app/api/routes.py` to correctly import `get_logger` from `app.utils.logger` and use `logger.info()`, `logger.error()`, and `logger.debug()` instead of `print()` statements or incorrect logger function calls.

## Task: Hyper-Explicit Authorization for OpenRouter & Final Debugging Steps
- In `app/services/agent_logic.py`:
    - `get_llm_client()` now initializes `OpenAI` with `api_key=None`.
    - New `_get_request_headers()` helper created to build all headers, including explicit `Authorization: Bearer <key>`.
    - `generate_interview_question()` and `evaluate_answer()` now use `_get_request_headers()` and pass them to `extra_headers` in `client.chat.completions.create()`.

## Task: Final Attempt at OpenRouter Auth - Revert to Standard Client Init & Full Key Logging
- In `app/services/agent_logic.py`:
    - `get_llm_client()` reverted to pass the `api_key` directly to the `OpenAI()` constructor, aligning with OpenRouter's primary Python example.
    - `_get_request_headers()` renamed to `_get_optional_headers()` and now only returns non-authorization headers (`HTTP-Referer`, `X-Title`).
    - For critical debugging, `get_llm_client()` now temporarily logs the *entire* loaded API key to verify its exact value against the user-provided key.

## Task: Confirm External Auth Issue & Secure Code
- User confirmed `curl` command with the same API key also results in a 401 "No auth credentials found" from OpenRouter.
- This indicates the issue is external to the Python application (likely API key validity, permissions, or OpenRouter account status).
- The debug line in `app/services/agent_logic.py` that logged the full API key has been reverted to log only the last 4 characters for security.

## Task: Switch from OpenRouter to Direct Deepseek API
- User decided to use a direct API key from Deepseek.
- In `app/services/agent_logic.py`:
    - `get_llm_client()` updated to use Deepseek's direct API base URL (`https://api.deepseek.com/v1`).
    - The client continues to use `DEEPSEEK_API_KEY` (now for the direct key).
    - OpenRouter-specific `extra_headers` (and the helper function for them) were removed from `client.chat.completions.create()` calls.
    - Model name set to generic `deepseek-chat` (user may need to adjust based on specific direct Deepseek model names).
    - Log messages updated to reflect direct Deepseek API usage.

## Task: Address stale API key issue
- Instructed user to stop and restart the Flask application to ensure the updated `.env` file (with the new direct Deepseek API key) is loaded. The application was still using the old cached API key.

## Task: Resolve Direct Deepseek API Usage - Payment Required
- After restarting the server with the correct direct Deepseek API key, the authentication issue (401) was resolved.
- A new error `402 Payment Required` with message `'Insufficient Balance'` is now occurring.
- This indicates the API key is valid, but the associated Deepseek account lacks funds/credits for the requested model/service.
- Advised user to check their Deepseek account balance, add funds if necessary, and verify model pricing/availability.

## Task: Revert to OpenRouter API Configuration
- User decided to switch back to using their OpenRouter API key.
- `app/services/agent_logic.py` reverted to OpenRouter configuration:
    - `get_llm_client()` reconfigured for OpenRouter's base URL and API key handling.
    - OpenRouter-specific optional headers (`HTTP-Referer`, `X-Title`) re-added via `extra_headers`.
    - Model name set to OpenRouter's `deepseek/deepseek-chat-v3-0324:free`.
    - Log messages updated to reflect OpenRouter usage.
- Reminded user to update `.env` with their OpenRouter key for `DEEPSEEK_API_KEY` and restart the Flask application.

## Task: Enhance Agent Logic (CV Parsing, Follow-ups, Adaptive Difficulty) - Phase 1 & 2
- Added `pypdf2` and `python-docx` to `requirements.txt`.
- Created `app/services/cv_parser_service.py` with text extraction for PDF, DOCX, TXT.
- Integrated logger into `cv_parser_service.py`.
- Implemented LLM-based skill/experience extraction in `cv_parser_service.extract_skills_and_experience`.
- Modified `app/api/routes.py` (`/interview` endpoint) to:
    - Handle `multipart/form-data` for CV uploads (alongside existing JSON handling).
    - Call `cv_parser_service` to process uploaded CVs.
    - Introduce a basic in-memory `cv_data_store` for temporary conversation state (skills, summary, history - HACK for single user).
    - Adjusted logic to pass CV data context (conceptually) to agent logic functions (actual parameter passing is next).

## Task: Enhance Agent Logic (CV Parsing, Follow-ups, Adaptive Difficulty) - Phase 3: Agent Logic Implementation
- Updated `app/services/agent_logic.py` (`generate_interview_question` and `evaluate_answer`):
    - Functions now accept and utilize a `conversation_state` dictionary.
    - Refactored `get_llm_client` to initialize client once (for OpenRouter).
    - Model name for LLM calls (question generation, evaluation) explicitly set to OpenRouter's `deepseek/deepseek-chat-v3-0324:free` for consistency.
    - **`generate_interview_question` enhancements:**
        - Uses `current_difficulty_next` from `conversation_state` (set by `evaluate_answer`) to determine `current_difficulty` for the current question.
        - Generates follow-up questions based on last question, answer, and score, adapting prompt based on `current_difficulty`.
        - If no history but CV data exists, attempts to route between behavioral/technical questions (rudimentary routing based on role keywords and skill count) and tailors prompt to `current_difficulty`.
        - Generates general questions if no history/CV, considering `current_difficulty`.
        - Improved prompt engineering and added post-processing for LLM question output (stripping preamble, ensuring question mark, fallback for empty question).
    - **`evaluate_answer` enhancements:**
        - Evaluation prompt now considers the `current_difficulty` at which the question was asked.
        - Score from LLM is parsed as float and clamped to the 1.0-5.0 range.
        - Sets `conversation_state['current_difficulty_next']` based on the latest score to influence the *next* question's difficulty.
- Updated `app/api/routes.py` to correctly pass `conversation_state` to the modified `agent_logic` functions.
- Fixed several linter errors in `app/services/agent_logic.py` related to f-string formatting and syntax.

## Agent Logic Enhancements & Frontend Interaction Debugging (User Query -> Assistant Plan -> User "ACT" -> Assistant Execution)

*   User reports white screen on `localhost:5000`. Identified port conflict (Flask and Vite on 5000) and Vite proxy misconfiguration.
    *   **Action:** Changed Flask in `run.py` to port `5001`.
    *   **Action:** Instructed user to change Vite proxy target in `vite.config.ts` to `http://localhost:5001`.
    *   User confirmed accessing frontend via `localhost:5000` (Vite) and backend via `localhost:5001` (Flask).
*   User reports "Error: Failed to start interview" on frontend when submitting only "Job Role" without CV. Backend logs show 400 error: "Missing 'audio' in request...".
    *   **Diagnosis:** The backend logic incorrectly required audio if a CV wasn't being actively processed in the current request for the first time. It didn't allow starting an interview with only a role to get the first question.
    *   **Action:** Modified audio requirement logic in `app/api/routes.py`.
        *   Audio is now considered optional if:
            1.  A CV file is part of the current request, and it's for the first question (i.e., `conversation_state["previous_questions"]` is empty).
            2.  No CV file is part of the current request, and it's the very first question (i.e., `conversation_state["previous_questions"]` is empty).
        *   Audio is required if `audio_base64` is missing and neither of the above conditions for omitting audio is met (typically for subsequent interview answers).
    *   This allows the frontend to initiate an interview by sending just the `role` (and optionally a CV) without needing to send audio for the first interaction. The backend will then generate and return the first interview question.
*   User initiated interview with "Job Role" only (no CV, no audio). Backend logs showed the audio requirement was correctly bypassed, but a `500 Internal Server Error` occurred.
    *   **Traceback:** `TypeError: 'NoneType' object is not subscriptable` in `app/services/agent_logic.py` at line `log_cv_experience_summary = conversation_state.get('cv_experience_summary', '')[:50]`.
    *   **Diagnosis:** When no CV is provided, `cv_experience_summary` is `None`. The `get(key, default)` method returns `None` if the key exists with a value of `None`, rather than the default. Slicing `None` causes the `TypeError`.
    *   **Action:** Modified the line in `app/services/agent_logic.py` to `cv_experience_summary_for_log = conversation_state.get('cv_experience_summary')` followed by `log_cv_experience_summary = (cv_experience_summary_for_log or '')[:50]`. This ensures an empty string is sliced if the summary is `None` or actually an empty string. 