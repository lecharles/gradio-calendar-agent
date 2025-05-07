import requests
from pypdf import PdfReader
from openai import OpenAI
from pydantic import BaseModel

# Download PDF from a link
def download_pdf(url, filename="temp.pdf"):
    response = requests.get(url)
    with open(filename, "wb") as f:
        f.write(response.content)
    return filename

# Extract text from PDF
def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# Define your structured data model
class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]

# Main function to extract structured data from a PDF link
def extract_event_from_pdf(pdf_url):
    pdf_path = download_pdf(pdf_url)
    pdf_text = extract_text_from_pdf(pdf_path)
    client = OpenAI()
    response = client.responses.parse(
        model="gpt-4o-2024-08-06",
        input=[
            {"role": "system", "content": "Extract the event information."},
            {"role": "user", "content": pdf_text},
        ],
        text_format=CalendarEvent,
    )
    return response.output_parsed

# Example usage:
if __name__ == "__main__":
    pdf_url = "https://arxiv.org/pdf/2210.09545v1"  # Provided PDF link
    event = extract_event_from_pdf(pdf_url)
    print(event)