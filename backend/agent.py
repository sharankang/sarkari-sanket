import requests
import google.generativeai as genai
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from textblob import TextBlob
import PyPDF2
from io import BytesIO

try:
    from config import GOOGLE_API_KEY, SEARCH_ENGINE_ID, GEMINI_API_KEY
except ImportError:
    GOOGLE_API_KEY, SEARCH_ENGINE_ID, GEMINI_API_KEY = None, None, None

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_bill_text_from_web(bill_name: str):
    print(f"AGENT: Searching for '{bill_name}'...")
    if not GOOGLE_API_KEY or not SEARCH_ENGINE_ID:
        return {'error': "Google API keys are not configured."}
    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY, static_discovery=False)
        query = bill_name
        res = service.cse().list(q=query, cx=SEARCH_ENGINE_ID, num=5).execute()
        if 'items' not in res or not res['items']:
            return {'error': "Sorry, no search results were found."}
        trusted_source_url = None
        trusted_domains = ['prsindia.org', 'gov.in', 'nic.in', 'sansad.in', 'legislative.gov.in', 'pib.gov.in', 'indiacode.nic.in']
        for item in res['items']:
            source_url = item['link']
            if any(domain in source_url for domain in trusted_domains):
                trusted_source_url = source_url
                print(f"AGENT: Found trusted source: {trusted_source_url}")
                break
        if not trusted_source_url:
            trusted_source_url = res['items'][0]['link']
            print(f"AGENT: No trusted source found. Trying first result: {trusted_source_url}")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(trusted_source_url, headers=headers, timeout=15)
        response.raise_for_status()
        scraped_text = ""
        if trusted_source_url.lower().endswith('.pdf'):
            pdf_file = BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                scraped_text += page.extract_text()
        else:
            soup = BeautifulSoup(response.content, 'html.parser')
            paragraphs = soup.find_all('p')
            if paragraphs:
                scraped_text = ' '.join(p.get_text() for p in paragraphs)
        if not scraped_text:
            return {'error': "Could not extract readable text from the source.", 'url': trusted_source_url}
        return {'text': scraped_text[:4000], 'url': trusted_source_url, 'error': None}
    except Exception as e:
        print(f"--- DETAILED AGENT ERROR ---\n{e}\n--------------------------")
        return {'error': f"A technical error occurred while fetching data: {e}"}

def generate_detailed_summary(bill_text: str, bill_name: str, language: str) -> str:
    """
    AGENT STEP 2: Sends text to Gemini with a language-specific prompt.
    """
    print(f"AGENT: Sending text to Gemini for summarization in {language}...")
    if not GEMINI_API_KEY:
        return "Error: Gemini API key is not configured."
    
    # --- DYNAMIC PROMPT LOGIC ---
    if language == 'Hinglish':
        language_instruction = "create a clear, detailed summary in simple Hinglish for the common citizen."
        heading1 = "### Yeh Kis Par Laagu Hota Hai?"
        heading2 = "### Yeh Bill Kya Hai?"
    else: # Default to English
        language_instruction = "create a clear, detailed summary in simple, easy-to-understand English for the common citizen."
        heading1 = "### Who Does It Apply To?"
        heading2 = "### What Is This Bill?"

    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = f"""
    You are an expert policy analyst named 'Sarkari Sanket'. Your task is to analyze the provided text of a government bill and {language_instruction}

    The bill name is: "{bill_name}"
    The bill text is: "{bill_text}"

    Your summary MUST be structured into exactly two sections with the following markdown headings:

    {heading1}
    (In this section, clearly explain the people, groups, or industries affected by this bill. Be specific.)

    {heading2}
    (In this section, explain the main purpose, key features, and the most important changes this bill introduces. Use simple language.)

    Generate the response now.
    """
    try:
        response = model.generate_content(prompt)
        print("AGENT: Successfully received summary from Gemini.")
        return response.text
    except Exception as e:
        print(f"AGENT ERROR (Gemini API): {e}")
        return f"Sorry, an error occurred while generating the summary: {e}"

def get_social_media_sentiment(bill_name: str) -> dict:
    mock_tweets = ["This is great!", "I love this bill.", "This is terrible.", "Worst decision ever.", "I'm not sure."]
    positive, negative, neutral = 0, 0, 0
    for tweet in mock_tweets:
        polarity = TextBlob(tweet).sentiment.polarity
        if polarity > 0.1: positive += 1
        elif polarity < -0.1: negative += 1
        else: neutral += 1
    total = len(mock_tweets)
    return {'positive': round((positive/total)*100), 'negative': round((negative/total)*100), 'neutral': round((neutral/total)*100)}
