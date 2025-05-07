import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from openai import OpenAI
from pydantic import BaseModel
from agents import Agent, function_tool, Runner
import json
import re

# Tool: Fetch PDF links from a URL
def fetch_pdf_links_fn(url: str) -> list[str]:
    print(f"[TOOL] fetch_pdf_links_fn called with url={url}")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    pdf_links = []

    # Helper: Convert arXiv abstract/abs link to PDF link
    def arxiv_abs_to_pdf(abs_url: str) -> str:
        # Handles both /abs/ and /pdf/ links
        match = re.search(r"arxiv.org/(abs|pdf)/([\w.\-]+)", abs_url)
        if match:
            paper_id = match.group(2)
            return f"https://arxiv.org/pdf/{paper_id}.pdf"
        return None

    # If arXiv page, extract all abstract links and convert to PDF links
    if "arxiv.org" in url:
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Absolute or relative abs links
            if "/abs/" in href:
                from urllib.parse import urljoin
                abs_url = urljoin(url, href)
                pdf_url = arxiv_abs_to_pdf(abs_url)
                if pdf_url:
                    pdf_links.append(pdf_url)
            # Direct PDF links (rare in listings)
            elif href.lower().endswith('.pdf'):
                if href.startswith('http'):
                    pdf_links.append(href)
                else:
                    from urllib.parse import urljoin
                    pdf_links.append(urljoin(url, href))
        # Remove duplicates
        pdf_links = list(dict.fromkeys(pdf_links))
        return pdf_links

    # Default: non-arXiv logic
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.lower().endswith('.pdf'):
            if href.startswith('http'):
                pdf_links.append(href)
            else:
                # Handle relative links
                from urllib.parse import urljoin
                pdf_links.append(urljoin(url, href))
    return pdf_links

# Tool: Download and extract text from a PDF
def extract_pdf_text_fn(pdf_url: str) -> str:
    print(f"[TOOL] extract_pdf_text_fn called with pdf_url={pdf_url}")
    response = requests.get(pdf_url)
    with open('temp.pdf', 'wb') as f:
        f.write(response.content)
    reader = PdfReader('temp.pdf')
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    # Remove surrogate code points
    text = ''.join(ch for ch in text if not (0xD800 <= ord(ch) <= 0xDFFF))
    # Sanitize text to valid UTF-8
    text = text.encode("utf-8", errors="replace").decode("utf-8")
    return text

# Pydantic model for paper info
class PaperInfo(BaseModel):
    title: str
    summary: str
    year: str
    month: str  # New field for month of publication
    authors: list[str]
    technique_type: str  # 'Prompt Engineering Technique', 'Language Model Technique', or 'Other'
    technique_description: str

# Tool: Analyze paper for prompt engineering relevance and extract info
def analyze_paper_fn(text: str) -> dict:
    print(f"[TOOL] analyze_paper_fn called (text length={len(text)})")
    client = OpenAI()
    system_prompt = (
        "You are an expert in prompt engineering and language model research. "
        "Given the following paper text, extract the following fields as JSON: "
        "{title, summary, year, month, authors, technique_type, technique_description}. "
        "- 'year' should be the year of publication. "
        "- 'month' should be the month of publication if available, otherwise an empty string. "
        "- 'authors' should be a list of author names. "
        "- 'technique_type' should be one of: 'Prompt Engineering Technique', 'Language Model Technique', or 'Other'. "
        "- If the paper describes a technique, set 'technique_type' accordingly and provide a brief 'technique_description'. "
        "- If not, set 'technique_type' to 'Other' and 'technique_description' to an empty string. "
        "If the paper is not about prompt engineering or language model techniques, return null. "
        "Output as JSON: {title, summary, year, month, authors, technique_type, technique_description} or null."
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text[:12000]},  # Truncate to fit token limit
        ],
        temperature=0,
        max_tokens=512
    )
    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return None

# Register tools
fetch_pdf_links = function_tool(fetch_pdf_links_fn)
extract_pdf_text = function_tool(extract_pdf_text_fn)
analyze_paper = function_tool(analyze_paper_fn)

# Agent definition
agent = Agent(
    name="Prompt Engineering Paper Finder",
    instructions="Given a URL with a list of PDFs, find the top 10 prompt engineering papers and output their title, summary, and year as JSON.",
    tools=[fetch_pdf_links, extract_pdf_text, analyze_paper]
)

def save_results_to_markdown_fn(papers: list, filename: str = "papers_output.md") -> str:
    print(f"[TOOL] save_results_to_markdown_fn called with {len(papers)} papers, filename={filename}")
    md_lines = ["# Top Papers\n"]
    for idx, paper in enumerate(papers, 1):
        if not paper:
            continue
        md_lines.append(f"## {idx}. {paper.get('title', 'Untitled')}")
        md_lines.append(f"- **Authors:** {', '.join(paper.get('authors', []))}")
        md_lines.append(f"- **Year:** {paper.get('year', '')}")
        md_lines.append(f"- **Month:** {paper.get('month', '')}")
        md_lines.append(f"- **Technique Type:** {paper.get('technique_type', '')}")
        md_lines.append(f"- **Technique Description:** {paper.get('technique_description', '')}")
        md_lines.append(f"- **Summary:** {paper.get('summary', '')}\n")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    return f"Results saved to {filename}"

save_results_to_markdown = function_tool(save_results_to_markdown_fn)

def orchestrate(url: str):
    pdf_links = fetch_pdf_links_fn(url)
    results = []
    for pdf_url in pdf_links:
        print(f"Processing: {pdf_url}")
        text = extract_pdf_text_fn(pdf_url)
        info = analyze_paper_fn(text)
        if info:
            results.append(info)
        if len(results) >= 10:
            break
    # Save results to markdown
    save_results_to_markdown_fn(results)
    return results

if __name__ == "__main__":
    url = input("Enter the URL containing a list of PDFs: ").strip()
    papers = orchestrate(url)
    print(json.dumps(papers, indent=2)) 