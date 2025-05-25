import os
from io import BytesIO
import PyPDF2
from docx import Document
from app.utils.logger import get_logger

# Potentially for LLM-based skill extraction later
# from flask import current_app
# from .agent_logic import get_llm_client 

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.txt'}

def get_file_extension(filename: str) -> str | None:
    """Extracts the file extension from a filename."""
    if '.' in filename:
        return os.path.splitext(filename)[1].lower()
    logger.warning(f"Filename '{filename}' has no extension.")
    return None

def extract_text_from_pdf(file_stream: BytesIO) -> str:
    """Extracts text from a PDF file stream."""
    text = ""
    try:
        reader = PyPDF2.PdfReader(file_stream)
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            page_text = page.extract_text()
            if page_text:
                text += page_text
        logger.info(f"Successfully extracted text from PDF (length: {len(text)}).")
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise 
    return text

def extract_text_from_docx(file_stream: BytesIO) -> str:
    """Extracts text from a DOCX file stream."""
    text = ""
    try:
        doc = Document(file_stream)
        for para in doc.paragraphs:
            text += para.text + "\n"
        logger.info(f"Successfully extracted text from DOCX (length: {len(text)}).")
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {e}")
        raise
    return text

def extract_text_from_txt(file_stream: BytesIO) -> str:
    """Extracts text from a TXT file stream."""
    try:
        decoded_text = file_stream.read().decode('utf-8')
        logger.info(f"Successfully extracted text from TXT (length: {len(decoded_text)}).")
        return decoded_text
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decoding error extracting text from TXT: {e}. Attempting with 'latin-1'.")
        try:
            # Reset stream position and try with a different encoding
            file_stream.seek(0)
            decoded_text = file_stream.read().decode('latin-1')
            logger.info(f"Successfully extracted text from TXT with 'latin-1' (length: {len(decoded_text)}).")
            return decoded_text
        except Exception as e_alt:
            logger.error(f"Error extracting text from TXT with 'latin-1' as fallback: {e_alt}")
            raise e_alt # Re-raise the exception from the fallback attempt
    except Exception as e:
        logger.error(f"Error extracting text from TXT: {e}")
        raise

def extract_text_from_cv(file_name: str, file_stream: BytesIO) -> str | None:
    """Extracts text from an uploaded CV file based on its extension."""
    extension = get_file_extension(file_name)

    if not extension or extension not in SUPPORTED_EXTENSIONS:
        logger.error(f"Unsupported file type: '{extension}' for file '{file_name}'. Supported types are {SUPPORTED_EXTENSIONS}")
        return None

    try:
        logger.info(f"Attempting to extract text from '{file_name}' (type: {extension}).")
        if extension == '.pdf':
            return extract_text_from_pdf(file_stream)
        elif extension == '.docx':
            return extract_text_from_docx(file_stream)
        elif extension == '.txt':
            return extract_text_from_txt(file_stream)
    except Exception as e:
        logger.error(f"Failed to extract text from CV '{file_name}': {e}")
        # Specific extractors already log and re-raise, this is a final catch.
        return None
    
    return None # Should logically not be reached if extension is supported and no error occurs

# --- Placeholder for LLM-based skill and experience extraction ---
def extract_skills_and_experience(cv_text: str) -> dict:
    logger.info(f"Extracting skills and experience from CV text (length: {len(cv_text)} chars)...")
    
    # Need to import get_llm_client from agent_logic or make it commonly accessible
    # For now, let's assume it might be refactored or called carefully
    # This creates a potential circular dependency if not handled well.
    # A better approach might be to pass the LLM client instance to this function.
    try:
        from .agent_logic import get_llm_client # Delayed import to avoid circularity at module load time
        client = get_llm_client()
    except ImportError:
        logger.error("Could not import get_llm_client from agent_logic for CV parsing.")
        client = None # Ensure client is defined

    if not client:
        logger.error("LLM client not available for CV parsing.")
        return {"skills": [], "experience_summary": "Error: LLM client unavailable."}

    # Limit text length to manage token usage and cost for LLM call
    # Max length for prompt context should be chosen based on model limits and typical CV size
    max_cv_text_length = 8000 # Example: approx 2000 tokens, adjust as needed
    truncated_cv_text = cv_text[:max_cv_text_length]
    if len(cv_text) > max_cv_text_length:
        logger.warning(f"CV text was truncated from {len(cv_text)} to {max_cv_text_length} characters for LLM processing.")

    try:
        prompt = (
            f"Analyze the following resume text and extract the key skills and a brief summary of relevant professional experience (max 3-4 sentences).\n"
            f"Focus on tangible skills, technologies, and responsibilities. Avoid generic phrases if possible.\n"
            f"Return the skills as a JSON list of strings. These should be specific skills, e.g., [\"Python\", \"Flask API Development\", \"Project Management\", \"Agile Methodologies\", \"React.js\", \"AWS S3\"].\n"
            f"Return the experience summary as a single string.\n"
            f"Output ONLY a valid JSON object with two keys: 'skills' (a list of strings) and 'experience_summary' (a string).\n"
            f"Example JSON Output: {{ \"skills\": [\"Python\", \"Flask\", \"React\", \"PostgreSQL\", \"Docker\"], \"experience_summary\": \"Developed and maintained web applications using Python and Flask, with a focus on RESTful API design. Collaborated in Agile teams to deliver software projects.\" }}\n\n"
            f"Resume Text:\n{truncated_cv_text}"
        )

        # Determine which LLM model to use (OpenRouter or direct Deepseek)
        # This should ideally be consistent with agent_logic's LLM choice
        # For now, hardcoding the OpenRouter model as it was the last active one in agent_logic
        # This section might need refactoring if LLM client provider changes frequently
        llm_model_name = "deepseek/deepseek-chat-v3-0324:free" # Defaulting to OpenRouter model
        # Potentially check current_app.config if we add a general LLM_MODEL_NAME config

        logger.info(f"Sending CV text to LLM ({llm_model_name}) for skill/experience extraction.")

        response = client.chat.completions.create(
            model=llm_model_name, 
            messages=[
                {"role": "system", "content": "You are an expert HR analyst specializing in accurately parsing resumes into structured JSON data. Only return the JSON object."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" },
            temperature=0.2 # Lower temperature for more deterministic extraction
        )
        
        extracted_data_str = response.choices[0].message.content
        logger.info(f"Received structured data from LLM for CV: {extracted_data_str}")
        
        import json
        try:
            extracted_data = json.loads(extracted_data_str)
        except json.JSONDecodeError as json_e:
            logger.error(f"JSON decoding failed for LLM response: {json_e}. Raw response: {extracted_data_str}")
            return {"skills": [], "experience_summary": "Error: AI returned invalid JSON format."}

        # Basic validation of the structure
        if not isinstance(extracted_data, dict) or \
           not isinstance(extracted_data.get('skills'), list) or \
           not all(isinstance(skill, str) for skill in extracted_data.get('skills', [])) or \
           not isinstance(extracted_data.get('experience_summary'), str):
            logger.error(f"LLM returned malformed or incomplete JSON structure for CV skills/experience. Data: {extracted_data}")
            return {"skills": [], "experience_summary": "Error: Malformed or incomplete data from AI."}
            
        return extracted_data
    except Exception as e:
        logger.error(f"Error during LLM-based CV data extraction: {e}")
        # Check for specific API errors if possible (e.g., auth, rate limits from the exception type)
        # For example, if using openai library directly: if isinstance(e, openai.APIError):
        # logger.error(f"OpenAI API Error: {e.status_code} - {e.message}")
        return {"skills": [], "experience_summary": f"Error during AI processing of CV."} 