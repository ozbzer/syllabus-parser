import streamlit as st
from pypdf import PdfReader
from openai import OpenAI
import os
from streamlit.errors import StreamlitSecretNotFoundError
import json 

st.title("Syllabus Parser")

# Upload file
def upload_file():
    uploaded_file = st.file_uploader("Only accept PDF Syllabus.")
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

analyze_button = st.button("Analyze Syllabus")

if analyze_button:  # Run this code when the user clicks the Analyze button
    if uploaded_file:  # Check if the user actually uploaded a file
        st.text("Analyzing syllabus...")  # Show a message so the user knows work is happening

        pdf_reader = PdfReader(uploaded_file)  # Open the uploaded PDF so Python can read its pages
        syllabus_text = ""  # Start with empty text; we will add each page's text into this

        for page in pdf_reader.pages:  # Go through the PDF one page at a time
            page_text = page.extract_text()  # Try to get the text from the current page
            if page_text:  # Only use the page if some text was found
                syllabus_text += page_text + "\n"  # Keep adding page text into the full syllabus text

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

                calendar_text += "END:VCALENDAR\n"
                st.success("Calendar created successfully. Download it below.")
                st.download_button(
                    "Download Calendar",
                    data=calendar_text,
                    file_name="syllabus_calendar.ics",
                    key="download_calendar_button",
                )

            else:
                st.warning("OpenAI API key not found. Please set OPENAI_API_KEY.")
        else:
            st.warning("Could not extract text from this PDF.")
    else:
        st.warning("Please upload a syllabus first")
