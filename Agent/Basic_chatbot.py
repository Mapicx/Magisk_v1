import os
os.environ['TRANSFORMERS_VERBOSITY'] = 'critical'

from langchain_core.messages import HumanMessage
from graph.graph_setup import setup_graph
from tools.pdf_tools import edit_resume_pdf_tool
from utils.logging_utils import log_llm_operation

# Initialize the chatbot with tools
tools = [edit_resume_pdf_tool]
chatbot = setup_graph(tools)

# Log chatbot initialization
log_llm_operation("CHATBOT_INITIALIZED", {"tools_available": [tool.name for tool in tools]})

# Only run the interactive loop if this file is executed directly
if __name__ == "__main__":
    thread_id = "cli_session"
    config = {"configurable": {"thread_id": thread_id}}

    print("AI: Hello! I'm your resume assistant. 👋")
    print("AI: To get started, please paste your resume. (Type 'exit' to quit)")

    # Get the resume
    resume = ""
    while True:
        user_msg = input("Your Resume: ")
        if user_msg.strip():
            resume = user_msg
            break
        print("AI: Please paste your resume to continue.")

    print("AI: Great! Now, please paste the job description.")

    # Get the job description
    job_description = ""
    while True:
        user_msg = input("Job Description: ")
        if user_msg.strip():
            job_description = user_msg
            break
        print("AI: Please paste the job description to continue.")

    print("AI: Perfect! I have your resume and the job description. How can I help you optimize it?")

    # Start the chat loop
    while True:
        user_msg = input("You: ")
        if user_msg.strip().lower() in ["exit", "quit", "bye"]:
            print("AI: Goodbye! 👋")
            break

        # Log user input
        log_llm_operation("USER_INPUT", {"message": user_msg})

        # Invoke with all state items
        inputs = {
            "messages": [HumanMessage(content=user_msg)],
            "resume": resume,
            "job_description": job_description,
            "resume_file_path": "Not available in CLI mode",
            "resume_file_name": "CLI_input.txt"
        }
        
        try:
            result = chatbot.invoke(inputs, config=config) # type: ignore
            # Get the last AI message
            for msg in reversed(result["messages"]):
                if hasattr(msg, 'content') and msg.content:
                    print("AI:", msg.content)
                    break
        except Exception as e:
            error_msg = f"Error during chatbot invocation: {str(e)}"
            log_llm_operation("CHATBOT_ERROR", {"error": error_msg}, success=False)
            print("AI: Sorry, I encountered an error. Please try again.")