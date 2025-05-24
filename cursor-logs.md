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