import streamlit as st
from pypdf import PdfReader
from openai import OpenAI
import os
from streamlit.errors import StreamlitSecretNotFoundError
import json 
from datetime import datetime, timedelta

st.title("Syllabus Parser")
st.info("Turns your syllabus into full study plan + calendar automatically")

# Upload file
def upload_file():
    uploaded_file = st.file_uploader("Only accept PDF & DOCX Syllabus.")
    return uploaded_file

uploaded_file = upload_file()

if uploaded_file: # checks whether a file was uploaded
    st.text(uploaded_file.name)
else:
    st.text("Please upload your syllabus")

def generate_ai_today_text(syllabus_text):
    prompt = f"""
You are an academic syllabus parser.

Read the syllabus text below and extract all important academic deadlines and events that should be added to a student's personal calendar.

Look for:
- assignments
- quizzes
- exams
- projects
- presentations
- labs
- readings only if they have a due date
- important class deadlines
- final exams or major assessments

Return only valid JSON.
Do not return explanations, markdown, headings, or extra text.

Return a JSON array.
Each item in the array must follow this format:
{{
  "title": "string",
  "type": "assignment | quiz | exam | project | presentation | lab | reading | deadline",
  "date": "YYYY-MM-DD or null",
  "time": "HH:MM or null",
  "description": "short helpful detail or null"
}}

Rules:
- Only include items that have a clear due date or scheduled date.
- Do not guess missing dates or times.
- If the date is missing, do not include the item.
- If the time is missing, use null.
- Keep titles short and student-friendly.
- Sort items by date from earliest to latest.
- If no valid calendar items are found, return [].

Syllabus text:
{syllabus_text}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )
    return response.output_text

def generate_prep_events(title, due_date, task_type):
    prep_events = [] # Create an empty list where I will store all the prep events
    
    # Step 1: decide prep steps 
    if task_type == "assignment":
        steps = [("Research", 7), ("Outline", 5), ("Draft", 3), ("Final Edit", 1)]
    elif task_type == "exam":
        steps = [("Study Session 1", 6), ("Study Session 2", 3), ("Review", 1)]
    elif task_type == "quiz":
        steps = [("Review Notes", 3), ("Practice Questions", 1)]
    elif task_type == "project":
        steps = [("Plan Project", 10), ("Work Session 1", 7), ("Work Session 2", 4), ("Final Touches", 1)]
    else:
        steps = []

    # convert string - date 
    due_date_obj = datetime.strptime(due_date, "%Y-%m-%d")
    
    # loop through steps 
    for step_name, days_before in steps:
        prep_date = due_date_obj - timedelta(days=days_before)

        event = {
            "title": f"{step_name} {title}",
            "date": prep_date.strftime("%Y-%m-%d")
        }

        prep_events.append(event)

    return prep_events
   
analyze_button = st.button("Analyze Syllabus")

if analyze_button:  # Run this code when the user clicks the Analyze button
    if uploaded_file:  # Check if the user actually uploaded a file
        st.text("Analyzing syllabus...")  # Show a message so the user knows work is happening

        syllabus_text = ""  # Start with empty text; we will add each page's text into this
         
        if uploaded_file.name.endswith(".pdf"):
            pdf_reader = PdfReader(uploaded_file) 
            for page in pdf_reader.pages:  # Go through the PDF one page at a time
                page_text = page.extract_text()  # Try to get the text from the current page
                if page_text:  # Only use the page if some text was found
                    syllabus_text += page_text + "\n"  # Keep adding page text into the full syllabus text
        
        elif uploaded_file.name.endswith(".docx"):
            from docx import Document
            doc = Document(uploaded_file)
            for para in doc.paragraphs:
                syllabus_text += para.text + "\n"

        if syllabus_text.strip():  # Check if the final text is not empty
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                try:
                    api_key = st.secrets.get("OPENAI_API_KEY")
                except StreamlitSecretNotFoundError:
                    api_key = None
                
            if api_key:
                client = OpenAI(api_key=api_key)

                ai_response = generate_ai_today_text(syllabus_text)
                calendar_items = json.loads(ai_response)
                # New logic comes here 
                prep_events_lists = []
                for task in calendar_items:
                    title = task["title"]
                    due_date = task["date"]
                    task_type = task["type"]

                    if not due_date:
                        continue

                    prep_events = generate_prep_events(title, due_date, task_type)
                    prep_events_lists.extend(prep_events) # combined them into one list
                # add preview here 
                st.subheader("Deadlines Found")

                for item in calendar_items:
                    title = item["title"]
                    date = item["date"]

                    if not date:
                        continue

                    formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%b %d, %Y")

                    st.write(f"**{title}** - {formatted_date}")

                st.subheader("Your Study Plan")

                for prep_event in prep_events_lists:
                    title = prep_event["title"]
                    date = prep_event["date"]

                    if not date:
                        continue

                    formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%b %d, %Y")

                    st.write(f"**{title}** - {formatted_date}")
                    
                calendar_text = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Syllabus Parser//EN\n"
                for item in calendar_items:
                    title = item["title"]
                    date = item["date"]
                    if not date:
                        continue
                    time = item["time"]
                    description = item["description"]

                    event_text = f"""BEGIN:VEVENT
SUMMARY:{title}
DTSTART;VALUE=DATE:{date.replace("-", "")}
DESCRIPTION:{description if description else ""}
END:VEVENT
"""
                    calendar_text += event_text

                for prep_event in prep_events_lists:
                    title = prep_event["title"] 
                    date = prep_event["date"]
                    event_text = f"""BEGIN:VEVENT
SUMMARY:{title}
DTSTART;VALUE=DATE:{date.replace("-", "")}
END:VEVENT
"""
                    calendar_text += event_text
                
                calendar_text += "END:VCALENDAR\n"
                st.success("Calendar created successfully. Download it below.")
                st.download_button(
                    "Download Calendar",
                    data=calendar_text,
                    file_name="syllabus_calendar.ics",
                    key="download_calendar_button",
                )
                st.info("Tip: Review your calendar before using — AI may miss or misinterpret some details.")

            else:
                st.warning("OpenAI API key not found. Please set OPENAI_API_KEY.")
        else:
            st.warning("Could not extract text from this PDF.")
    else:
        st.warning("Please upload a syllabus first")


