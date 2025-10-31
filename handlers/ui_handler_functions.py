import sys
import os
# import psutil  # Commented out - only used for debugging utilities we don't need
import time
import logging

# Add path to Multi_Agent_Email_tool for email fetching functions
# Go up from handlers/ to Prompt_Playground/, then up to All_Coding_Projects/, then into Multi_Agent_Email_tool/
project_root = os.path.dirname(os.path.dirname(__file__))  # Get Prompt_Playground directory
email_tool_path = os.path.join(os.path.dirname(project_root), 'Multi_Agent_Email_tool')
sys.path.insert(0, email_tool_path)

from persistent_data.ui_session_data_mgmt import *
from typing import Optional, Tuple, List
from server_data.ui_server_side_data import *

# Commented out - PDF processing not needed for prompt playground
# from pdf_processor_service.pdf_processor import *

# Import email fetching functions from Multi_Agent_Email_tool
# TODO [Future Enhancement]: Extract shared Gmail functions into a separate gmail-utils library
#       This would allow both Prompt_Playground and Multi_Agent_Email_tool to use the same
#       authentication, message fetching, and parsing code. Ideal structure:
#       - gmail-utils library (pip installable)
#       - Separate credentials management per project
#       - Shared core functions: authenticate_user(), get_message_metadata(), get_message_body()
# TODO [Update]: Change import from V0.4.py to email_objects.py once that module is finalized
try:
    # Read and extract only the function definitions from V0.4.py
    # Skip module-level code that causes errors
    v0_4_path = os.path.join(email_tool_path, "V0.4.py")
    with open(v0_4_path, 'r') as f:
        lines = f.readlines()

    # Find line 79 where authenticate_user starts (first function we need)
    # Skip everything before that to avoid module-level instantiation errors
    start_line = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('def authenticate_user'):
            start_line = i
            break

    # Execute only from line 79 onwards
    v0_4_source = ''.join(lines[start_line:])

    # Need to add necessary imports back
    v0_4_imports = """
import os.path
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
"""

    v0_4_namespace = {}
    exec(v0_4_imports + v0_4_source, v0_4_namespace)

    # Extract the functions we need
    gmail_authenticate = v0_4_namespace.get('authenticate_user')
    fetch_messages = v0_4_namespace.get('fetch_messages')
    get_message_metadata = v0_4_namespace.get('get_message_metadata')
    get_message_body = v0_4_namespace.get('get_message_body')
    generate_gmail_search_query = v0_4_namespace.get('generate_gmail_search_query')

    # Verify we got all the functions
    if not all([gmail_authenticate, fetch_messages, get_message_metadata, get_message_body, generate_gmail_search_query]):
        raise ImportError("Failed to extract required functions from V0.4.py")

    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    GMAIL_AVAILABLE = True
    print("Gmail functions loaded successfully")
except Exception as e:
    print(f"Warning: Could not import Gmail functions: {e}")
    GMAIL_AVAILABLE = False

import langchain

from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder

from langchain.memory import ConversationBufferMemory

from langchain.globals import set_debug



#################################
# For OpenAI, use the following:
#################################
# from langchain_openai import ChatOpenAI

#################################
# For Gemini, use the following:
#################################
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnableWithMessageHistory
from langchain.schema import HumanMessage, AIMessage

# import pdfplumber  # Commented out - PDF processing not needed
import logging

# Set up logging configuration - uncomment when needed
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('debug.log', mode='w'),
#         logging.StreamHandler()  # This will print to console
#     ]
# )
# # Loggers for specific components - uncomment when needed
# # Specifically restrict pdfminer logging to WARNING level
# # it shpuld be used sparingly, as it is a resource HOG
# logging.getLogger('pdfminer').setLevel(logging.WARNING)
# logging.getLogger('langchain').setLevel(logging.WARNING)  # Suppress most LangChain logs
# logging.getLogger('urllib3').setLevel(logging.WARNING)   # Suppress HTTP request logs
# logging.getLogger('google').setLevel(logging.WARNING)    # If using Google/Gemini

# # Create our conversation-specific debug logger
# conversation_logger = logging.getLogger(__name__)
# conversation_logger.setLevel(logging.DEBUG)


# # Create a separate handler for LangChain-specific logging
# langchain_logger = logging.getLogger('langchain')
# langchain_handler = logging.FileHandler('langchain_debug.log')
# langchain_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
# langchain_logger.addHandler(langchain_handler)

# Configure LangChain debug logging
set_debug(False)  


def truncate_str(s: str, length: int = 100) -> str:
    """Truncate a string to length chars and add ellipsis if truncated."""
    return s[:length] + '...' if len(s) > length else s

import textwrap


class PDFExtractionError(Exception):
    """Custom exception for PDF extraction errors.""" 
    pass # These can actually be blank classes. We will pass a custom message through them if/when they are raised.

class FileWriteError(Exception):
    """Custom exception for file writing errors."""
    pass

class FileReadError(Exception):
    """Custom exception for file reading errors."""
    pass


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# This is some weird python majic that allows this file (which is in a subdirectory) to
#  access a function in the main project directory


############################
# Set up all the Langchain components for 
#       - system message
#       - additional prompt instructions used with an insurance policy upload
#       - additional prompt contents - the text of an insurance policy
#       - prompt structure
#       - model parameters
#       - conversation memory
#       - the Conversation Chain



# Start by defining the system messaage:

##########################################################
# New system prompt allowing any and all insurance types
##########################################################

system_message = """You are a helpful AI assistant. Please respond to the user's questions accurately and concisely. If the user asks about job job listings in the this email, please search for jobs that involve AI Product Management or AI Product Strategy at any level. For each tht that you find that meet that description, please check to see if they are remote, hybrid or local or on-site only, and report that job to the user, letting them know whether it is remote, hybrid or local onsite. If it is hybrid, local, or onsite or in any other way will require the user to be in the office regularly, let them know the location of the position. If you are unsure about any feture of this job, please indicate that you are unsure and let the user now that they should check the specifics of that job themselves. Answer any questions that the user might ask about any of the positions, such as the employer, a brief summary of the job responsibilities and qualifications for the position. Always be truthful and accurate."""

#If the user asks a question about finding an isurance professional or agent, please reply with this exact text: THIS IS JUST A PLACEHOLDER UNTIL THE CORRECT INFORMATION IS SUPPLIED BY ANDY, SCOTT, AND AL. Removed, DR, 3/20.2025 per Andy's request.


#########################
# original system prompt
#########################
# system_message = """Acting as an expert in U.S. personal insurance, please answer questions from the user in a helpful and supportive way about Life Insurance, Disability Insurance, Long Term Care Insurance, Auto Insurance, Umbrella Insurance, Pet Insurance, and Homeowners Insurance (including Condo insurance and Renters insurance), or about their previous questions in the current conversation. If the user asks a question about a different type of insurance, reply that you are not trained to discuss those types of insurance but would be happy to talk to them about Life Insurance, Disability Insurance, Long Term Care Insurance, Auto Insurance, Umbrella Insurance, Pet Insurance, and Homeowner's, Condo, and Renter's Insurance. If the user asks a question about a particular insurance policy, but no policy has been provided, politely invite them to select a policy from the radio buttons on the left of the screen, or upload a policy to the Insutrance Portal. If the user asks a question outside the realm of personal insurance in the United States (unless it is a question about this conversation) politely answer that you would love to help them, but are only trained to discuss issues and questions regarding personal insurance in the U.S. Users may be quite new to the domain of insurance so it is very important that you are welcoming and helpful, and that answers are complete and correct. Please err on the side of completeness rather than on the side of brevity, and always be truthful and accurate. And this is very important: please let the user know that they should always contact an insurance professional before making any important decisions."""

saved_policy_instructions = """Please use the following policy document as the primary source of information for answering the user's next query.  If you cannot find that information in the policy, please clearly state that. If you can answer the question using your general knowledge about insurance, please clearly state that as well. Always prioritize the specific policy details over general knowledge."""

policy_instructions = ""
policy_extracted_content = ""

# Set up the memory
memory = ConversationBufferMemory(return_messages=True) #ConversationBuffer
'''ConversationBufferMemory is a Langchain class that automajically stores the conversation history as a buffer. It labels which strings belong to "HumanMessage" (user) input and which belong to "AIMessage" (bot) output. return_messages=True configures the memory to return the history as a list of messages, which is compatible with chat models.'''




# Set up the language model

#################################
# For OpenAI, use the following:
#################################
# model = ChatOpenAI(
#     model="gpt-4o",     # Specify the preferred model
#     temperature=0.7,    # control the amount of randomness in replies
#     streaming=True      # Enable Streaming
# )

#################################
# For Gemini, use the following:
#################################
# TODO [Enhancement]: Make model configurable via UI or config file
#       Options to consider:
#       - UI dropdown to select model (gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite)
#       - YAML config file with model selection
#       - Environment variable override
#       Once optimal model is determined, pin to specific version (e.g., gemini-2.5-pro-001)
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.7,
    convert_messages_to_prompt=False, # We are managing the convo history ourselves
    streaming=True
)

#################################
# For OpenAI, use the following:
#################################
# Create the prompt template
# prompt = ChatPromptTemplate.from_messages([ # Langchain will automatically fill in the history and input
#                                             # placeholders with the current conversation history and user
#                                             # query, creating a complete prompt for the language model.
#     SystemMessagePromptTemplate.from_template(system_message), # used for strings
#     SystemMessagePromptTemplate.from_template("{policy_instructions}"),# used for strings
#     SystemMessagePromptTemplate.from_template("{policy_content}"), # used for strings
#     MessagesPlaceholder(variable_name="history"), # used for LISTS of strings
#     HumanMessagePromptTemplate.from_template("{input}")# used for strings
# ])

#################################
# For Gemini, use the following:
#################################
# Create the prompt template
# But we need to modify how we structure the prompt and chain to keep system/policy content separate
prompt = ChatPromptTemplate.from_messages([
    # First message combines system content and instructions
    ("human", "System Instructions:\n{system_template}\n\nPolicy Instructions:\n{policy_instructions}\n\nPolicy Content:\n{policy_content}"),
    # Then include conversation history
    MessagesPlaceholder(variable_name="history"),
    # Finally, the current user query
    ("human", "{input}")
])



# Create the runnable chain (using the "pipe" operator as we would in Unix shells)
# This setup does a few important things:
# It creates a chain that formats our prompt and sends it to the model.
# It wraps this chain with conversation history management.
# It ensures that each time we use this chain, it will automatically:
    # Retrieve the conversation history
    # Add the new input to the history
    # Format the prompt with the full history
    # Send it to the model
    # Save the response back to the history
# This approach simplifies the management of conversation history and makes it easier to maintain context across multiple interactions in a chat session.

# Create the runnable chain
# Modified chain to separate system prompt, policy instructions & content
def create_chain():
    """Create a new chain with current global settings."""
    return (
        {
            "system_template": lambda x: system_message,  # Constant system message
            "policy_instructions": lambda x: x["policy_instructions"],
            "policy_content": lambda x: x["policy_content"],
            "input": lambda x: x["input"],
            "history": lambda x: format_history_for_gemini(memory.load_memory_variables({})["history"])
        }
        | prompt
        | model
    )

# Initial chain creation
chain = create_chain()


####################################
# Focus Handler
####################################

def handle_focus(session_state: SessionData, 
                 user_id: str, # would be passed to Chatbot from server
                 session_id: str, # would be passed to Chatbot from server
                 server_users: ServerUserDataCollection) -> None: # would be passed to Chatbot from server
    """
    Handle Focus.
        session_state: is used to manage the data that the chatbot needs to "remember" for the entire session across going in and out of focus.
        The last three function arguments represent data that would be available though the server

    This function processes the focus event for the chatbot. 
    --> WE ARE ASSUMING THAT WHEN FOCUS LANDS ON THE CHATBOT, IT IS AT THE VERY LEAST PASSED THE 
    --> USER ID OF THE CURRENT USER. 
    When focus is switched to the chatbot:
        If the session is not yet initialized, (i.e., no session state object exists for this user_id), this handler creates one.
        This will create a new SessionData object with:
        - The initialization flag set to False
        - The user_id set to ""
        - The number of policies uploaded by this user set to 0
        - The collection of policy objects for this user set to None
        - The currently selected policy set to None
    --> The intialization flag is then set to True
    --> and the actual user_id is filled in

    --> The rest of the handler is executed everytime it is called, whether or nor the initialization has been run.
    --> Using the user_id, the retrieval or at last the copying of the stored data from the server is emulated. This action includes copying and storing:
        - The number of policies uploaded by the user (which may have changed since the last time the chatbot was in focus
            
        - And for each policy uploaded:
            - file_id: str  # Unique identifier for the policy file
            - path:   str # URL or file path
            - policy_type: str  # Type of policy (e.g., "auto", "home")
            - print_name: str  # Display name for the policy
            - carrier: str  # Insurance carrier name
            - format: str  # File format (e.g., "pdf", "docx")
            - additional_metadata: Optional[Dict] = None  # Optional dictionary for extra information 
            - the currently chosen policy is kept at its current value ("which may be none") as the UI is not yet rendered.
    --> Now that the session_state is up to date, the UI can be rendered.
    --> Note that the conversation history will be kept by Langchain as it is a compoenent of the prompt template, and the UI render will need to get that data from Langchain
    
    Args:
        session_state: SessionData. # The current session state, or "None"
        The user ID

    Returns:
        None

    Raises:
    TBD
"""
    session_state.user_id = user_id
    session_state.session_id = session_id
    # the following is only executed the fist time the Chatbot receives focus or when the session is restarted by the tester
    if session_state.get_is_initialized() == False:
        session_state.selected_policy = "None"
        session_state.selected_policy_index = None # ints can be initialized to None
        session_state.is_initialized = True
        
    ###############################################################################################
    # --> IN THE ACTUAL SYSTEM, THE DATA ON THE SERVER WOULD BE ACCESSIBLE VIA API OR OTHER METHOD 
    # --> AND WOULD NOT BE PASSED AS A PARAMETER TO THIS FUNCTION                                  
    ##############################################################################################
 

    # The following would be executed EVERY TIME the chatbot receives focus, including the first, as this data may have changed. E.g., the user may have deleted and/or uploaded some policies since the chatbot last had focus. 
    
    transfer_server_data_for_current_user(session_state, server_users) 




def transfer_server_data_for_current_user(session_state: SessionData, server_users: ServerUserDataCollection) -> None:

    # First get the userID for this session's user
    user_id = session_state.user_id

    # Use user_id as a key to find data for that specific user
    try:
        server_user_data = server_users[user_id]
    except KeyError:
        print(f"User with id {user_id} not found")
    
    session_state.first_name = server_user_data.first_name
    session_state.last_name = server_user_data.last_name

    # Next get the info about that user's uploaded insurance policies
    session_state.policy_list = get_policy_file_info(session_state, user_id, server_user_data)

    



def get_policy_file_info(session_state: SessionData, 
                         user_id: str, 
                         server_user: ServerUserData) -> None:
    
     # the set of uploaded policies may have changed since the last focus even, so reinitialize
    policy_count = 0    # the set of uploaded policies may have changed since the last focus event
    session_state.policy_list=[] # initialize as empty list
    
    for policy in server_user.policies:  # Number of policies uploaded can be 0 
        sesh_policy = Policy() # create a fresh Policy instance
        sesh_policy.file_id = policy.file_id # Unique identifier for the policy file
        sesh_policy.path = policy.path # URL or file path
        sesh_policy.policy_type = policy.policy_type # Type of policy (e.g., "auto", "home")
        sesh_policy.print_name = policy.print_name # Display name for the policy
        sesh_policy.carrier = policy.carrier # Insurance carrier name
        sesh_policy.format = policy.format # File format (e.g., "pdf", "docx", "md")
        sesh_policy.is_extracted = policy.is_extracted
        sesh_policy.extracted_file_path = policy.extracted_file_path
        sesh_policy.additional_metadata = policy.addl_metadata # Optional dictionary for extra information which can either be a dict or None
        
        session_state.policy_list.append(sesh_policy)
        policy_count += 1

    session_state.number_policies = policy_count
    if (policy_count > 0):
        session_state.current_policy = "None" # for users with at least 1 policy uploaded, the "None" button is the default policy selector button
    return(session_state.policy_list)


####################################
# Query Handler
####################################
def handle_query(user_input: str, session_state: SessionData, user_id: str) -> None:

    policy_instructions = ""
    policy_content = ""

    # First check if there are any policies uploaded or selected
    if(policy_is_selected(session_state)):
        index = session_state.selected_policy_index
        policy = session_state.policy_list[index] 

        if (not (policy.is_extracted)):
            process_pdf_file(policy, session_state)
            
        policy_content = read_from_extracted_file(policy.extracted_file_path) 
        policy_instructions = saved_policy_instructions
    
    history = memory.load_memory_variables({})["history"]

    buffer_chunks = []  # Use list instead of string concatenation, IMPORTANT! Strings cause very long lag
    full_response_chunks = []  # Use list instead of string concatenation, IMPORTANT! Strings cause very long lag

    try:
        # Streaming chunks of the response
        for chunk in chain.stream({
            "input": user_input,
            "policy_instructions": policy_instructions,
            "policy_content": policy_content,
            "history": memory.load_memory_variables({})["history"]
        }):

            
            # This line is used to extract the content of the chunk, which could either be directly an attribute of chunk itself (chunk.content), or it could be nested within another attribute (chunk.message.content). The goal is to safely access these fields without throwing an error if they don't exist.
            content = getattr(chunk, 'content', None) or getattr(chunk.message, 'content', None)
            
            if content:
                buffer_chunks.append(content)
                full_response_chunks.append(content)

                # Send buffer in chunks of 50 characters
                buffer = ''.join(buffer_chunks)
                while len(buffer) >= 50:
                    send_chunk = buffer[:50]
                    buffer = buffer[50:]
                    buffer_chunks = [buffer]  # Reset buffer_chunks with remaining content
                    send_chunk = send_chunk.replace('\n', '\\n')
                    yield send_chunk

        # Handle any remaining buffer content
        if buffer_chunks:
            final_buffer = ''.join(buffer_chunks).replace('\n', '\\n')
            yield final_buffer

        # Join full response chunks only once at the end
        full_response = ''.join(full_response_chunks)

        if not full_response:
            full_response = "I apologize, but I encountered an error processing your request. Please try again."

        memory.save_context({"input": user_input}, {"output": full_response})

        
    except Exception as e:
        conversation_logger.error(f"Error in chat stream: {str(e)}", exc_info=True)
        yield "I apologize, but I encountered an error. Please try again."

    yield "DONE"

def policy_is_selected(session_state: SessionData) -> bool:
    return (session_state.number_policies is not None and 
            session_state.number_policies > 0 and 
            session_state.selected_policy_index is not None and 
            session_state.selected_policy != "None")
        

def format_history_for_gemini(history):
    """Format conversation history while maintaining message objects"""
    seen_messages = set()  # Track unique messages
    formatted_messages = []
    
    for i, msg in enumerate(history):
        content = str(msg.content)
        # Only add message if we haven't seen it before
        if content not in seen_messages:
            formatted_messages.append(msg)  # Keep the original message object
            seen_messages.add(content)

    return formatted_messages  # Return list of message objects, not strings

    
def process_pdf_file(policy: Policy, session_state: SessionData):
    '''Create a text file from the pdf file by: 
            1) Converting the .pdf to a text string
            2) Save the text in a file with the same name but with a .txt extension
            3) Store the path to the converted file in the session_state
            4) Set is_extracted to True in the session_state

    '''
    txt_file_path = create_txt_file_path(policy.path)
    file_contents = extract_text_from_pdf(policy.path, txt_file_path) # in subdir pdf_processor
    #txt_file_path = write_text_to_txt_file (file_contents, policy)
    policy.extracted_file_path = txt_file_path
    policy.is_extracted = True

def extract_text_from_pdf(policy, txt_file_path):
    # Initialize the service
    pdf_service = PDFProcessingService(base_temp_dir="processing_tmp")

    # Check dependencies first
    if not pdf_service.check_dependencies():
        print("Missing dependencies. Please install required packages.")
        exit(1)

    # Process a document
    result = pdf_service.process_document(
        pdf_path=policy,
        output_file=txt_file_path,
        languages=["eng"]
    )

    # Check result and use the extracted text
    if result["success"]:
        print(f"Document processed successfully as {result['document_type']}")
        print(f"Text available at: {result['text_file_path']}")
        
    else:
        print(f"Processing failed: {result['error']}")

    # Optional: Clean up temporary files when done
    if "job_id" in result:
        pdf_service.cleanup_job(result["job_id"])

#####################################################################
# Deprecated by PDFProcessingService
#####################################################################
# def extract_text_from_pdf_file(policy: Policy) -> str:
#     try:
#         text_parts = []
#         with pdfplumber.open(policy.path) as pdf:
#             total_pages = len(pdf.pages)
#             for page in pdf.pages:
#                 extracted_text = page.extract_text()
#                 if extracted_text:  # Guard against None or empty strings
#                     text_parts.append(extracted_text)
#         return "\n\n".join(text_parts)
#     except Exception as e:
#         raise PDFExtractionError(f"Failed to extract text from PDF: {str(e)}")



# def extract_text_from_pdf_file(policy) -> str:
#     """
#     Extracts text from a PDF file, handling both text-based and scanned PDFs.
#     First tries to extract text directly, falls back to OCR if needed.
#     """
#     try:
#         # First try direct text extraction with pdfplumber
#         #pagenum = 0;
#         text_parts = []
#         #print(f'Path: {policy.path}')
#         with pdfplumber.open(policy.path) as pdf:
#             for page in pdf.pages:
#                 #pagenum += 1
#                 #print(f'attempting text extract for page {pagenum}')
#                 extracted_text = page.extract_text()
#                 if extracted_text:  # Non-empty text
#                     text_parts.append(extracted_text)
        
#         # If we got meaningful text, return it
#         if text_parts and len("\n\n".join(text_parts).strip()) > 100:
#             print(f"Successfully extracted text directly from {policy.path}")
#             return "\n\n".join(text_parts)
        
#         # Otherwise, fall back to OCR
#         print(f"Falling back to OCR for {policy.path}")
#         import pytesseract
#         from pdf2image import convert_from_path
        
#         images = convert_from_path(policy.path)
#         ocr_text_parts = []
#         for i, image in enumerate(images):
#             print(f"Processing page {i+1} with OCR")
#             text = pytesseract.image_to_string(image)
#             ocr_text_parts.append(text)
        
#         return "\n\n".join(ocr_text_parts)
        
#     except Exception as e:
#         raise PDFExtractionError(f"Failed to extract text from PDF {policy.path}: {str(e)}")




def write_text_to_txt_file (file_contents: str, policy: Policy) -> str:
    txt_file_path = create_txt_file_path(policy.path)
    try:
        with open(txt_file_path, 'w', encoding='utf-8') as file:
            file.write(file_contents)
        return(txt_file_path)
    except Exception as e:
        raise FileWriteError(f"Failed to write text to file: {str(e)}")
    

def create_txt_file_path(pdf_file_path: str) -> str:
     # Split the path into the directory path, filename, and extension
    directory, filename = os.path.split(pdf_file_path)
    name, _ = os.path.splitext(filename)
    # Create the new filename with .txt extension
    new_filename = name + '.txt'
    # Create full path
    # Join the directory path with the new filename
    txt_file_path = os.path.join(directory, new_filename)
    return (txt_file_path)


def read_from_extracted_file(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError("Error: The file was not found.")
    except IOError:
        raise IOError("Error: There was an issue reading the file.")
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {e}")
    

####################################
# Policy Selection Handler
####################################

def handle_policy_selection(session_state: SessionData, user_id: str, selected_policy: str) -> None:
   
    
    if selected_policy == "None":
        session_state.selected_policy = 'None'
        session_state.selected_policy_index = None
    else:
        for index, policy in enumerate(session_state.policy_list):
            if policy.print_name == selected_policy:
                session_state.selected_policy = policy
                session_state.selected_policy_index = index
                break
        else:
            print(f"Warning: Selected policy '{selected_policy}' not found")
    

            





####################################
# Email Fetching Handler
####################################

def handle_fetch_emails(session_state: SessionData, date_str: str):
    """
    Fetch emails from Gmail for the specified date.

    Args:
        session_state: Current session state to store fetched emails
        date_str: Date in YYYY-MM-DD format (e.g., "2025-11-30")

    Returns:
        dict with success status and message
    """
    if not GMAIL_AVAILABLE:
        return {"success": False, "error": "Gmail functions not available"}

    try:
        # Authenticate with Gmail
        creds = gmail_authenticate()
        service = build("gmail", "v1", credentials=creds)

        # Generate query for the specified date
        query = generate_gmail_search_query(date_str, date_str)

        # Fetch all messages
        messages = fetch_messages(service, query)

        if not messages:
            return {"success": True, "count": 0, "message": f"No emails found for {date_str}"}

        # Fetch metadata only (lazy load bodies when user views each email)
        email_list = []
        for msg in messages:
            metadata = get_message_metadata(service, msg['id'])
            email_list.append({
                'id': metadata['id'],
                'sender': metadata['sender'],
                'subject': metadata['subject'],
                'date': metadata['date'],
                'internal_date': metadata['internal_date'],  # Include for sorting
                'body': None  # Will be fetched lazily
            })

        # Sort emails by internal_date (newest first)
        email_list.sort(key=lambda x: int(x.get('internal_date', 0)), reverse=True)

        # Store in session state
        session_state.fetched_emails = email_list
        session_state.current_email_index = 0
        session_state.gmail_service = service  # Store service for later body fetching

        # Return ALL email metadata (sorted by date)
        emails_metadata = []
        for email in email_list:
            emails_metadata.append({
                'sender': email['sender'],
                'subject': email['subject'],
                'date': email['date'],
                'internal_date': email['internal_date']
            })

        return {
            "success": True,
            "count": len(email_list),
            "message": f"Fetched {len(email_list)} emails from {date_str}",
            "emails": emails_metadata  # Return all emails at once
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# Old sequential navigation removed - replaced with direct email selection via handle_select_email()
# Users now click any email in the sidebar to select it


def handle_select_email(session_state: SessionData, email_index: int):
    """
    Select an email by index and fetch its body if needed.

    Args:
        session_state: Current session state
        email_index: Index of email in fetched_emails list

    Returns:
        dict with email data including body
    """
    if not hasattr(session_state, 'fetched_emails') or not session_state.fetched_emails:
        return {"success": False, "error": "No emails fetched"}

    if email_index < 0 or email_index >= len(session_state.fetched_emails):
        return {"success": False, "error": "Invalid email index"}

    email = session_state.fetched_emails[email_index]

    # Fetch body if not already loaded
    if email['body'] is None:
        try:
            service = session_state.gmail_service
            email['body'] = get_message_body(service, email['id'])
        except Exception as e:
            email['body'] = f"[Error fetching body: {str(e)}]"

    # Update current index
    session_state.current_email_index = email_index

    return {
        "success": True,
        "email": {
            "sender": email['sender'],
            "subject": email['subject'],
            "date": email['date'],
            "body": email['body']
        }
    }


# Note: Email context is now injected client-side in script.js before sending queries
# See handleQuerySubmit() function which prepends email body, sender, subject, and date


####################################
# Clear Button Click Handler
####################################

def handle_clear_button_click(session_state, user_id):
    '''Clear the conversation by resetting memory, policy data, and chain state.The key to clearing the conversation is to clear the memory. But  we should also clear the policy instructions and the policy content. We recreate the chain itself to insure that all values, including history and input are reset. Finally, session state values are reinitialized by setting the selected policy to the str "None" and the selected policy's index to None.
    '''
    global memory, chain, policy_instructions, policy_extracted_content
    

    
    global memory, chain, policy_instructions, policy_extracted_content
    
    # Log memory state before clearing
    initial_history = memory.load_memory_variables({})["history"]

    
    # Clear the Langchain conversation memory
    memory.clear()

    # Verify memory is cleared
    cleared_history = memory.load_memory_variables({})["history"]

    

    # Clear policy instructions and policy content
    policy_instructions = ""
    policy_extracted_content = ""
  
    # Recreate chain to ensure completely fresh state
    chain = create_chain()

    
    # Reset the selected policy
    session_state.selected_policy = "None"
    session_state.selected_policy_index = None


    
#######################
# Debugging utilities
#######################
# Commented out - these were for Docker debugging and require psutil
# def get_container_resource_usage():
#     try:
#         process = psutil.Process(os.getpid())
#         cpu_percent = process.cpu_percent(interval=0.1)
#         memory_info = process.memory_info()
#         memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
#         return f"CPU Usage: {cpu_percent}%, Memory: {memory_mb:.2f}MB"
#     except Exception as e:
#         return f"Error getting resource usage: {e}"
#
# def print_container_limits():
#     try:
#         with open('/sys/fs/cgroup/memory/memory.limit_in_bytes', 'r') as f:
#             memory_limit = int(f.read().strip()) / (1024 * 1024)  # Convert to MB
#             print(f"Container memory limit: {memory_limit:.2f}MB")
#     except Exception as e:
#         print(f"Could not read container limits: {e}")

