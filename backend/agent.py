import requests
import google.generativeai as genai
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from textblob import TextBlob
import PyPDF2
from io import BytesIO
import praw
import re


try:
    from config import (
        GOOGLE_API_KEY, SEARCH_ENGINE_ID, GEMINI_API_KEY,
        REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
    )
except ImportError:
    GOOGLE_API_KEY, SEARCH_ENGINE_ID, GEMINI_API_KEY = None, None, None
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT = None, None, None


if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def get_bill_text_from_web(bill_name: str):
    """
    This function is unchanged from your working version.
    """
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
                scraped_text += page.extract_text() or ""
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
    This function is also unchanged from your working version.
    """
    print(f"AGENT: Sending text to Gemini for summarization in {language}...")
    if not GEMINI_API_KEY:
        return "Error: Gemini API key is not configured."
    
    if language == 'Hinglish':
        language_instruction = "create a clear, detailed summary in simple Hinglish for the common citizen."
        heading1 = "### Yeh Kis Par Laagu Hota Hai?"
        heading2 = "### Yeh Bill Kya Hai?"
    else:
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
    """
    AGENT STEP 3: This is the UPGRADED function that uses the Reddit API.
    """
    print(f"AGENT: Searching Reddit for '{bill_name}'...")
    if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT]):
        return {'error': "Reddit API keys are not fully configured."}

    try:
        year_match = re.search(r'\b(19\d{2}|20[0-1]\d)\b', bill_name)
        if year_match:
            return {'note': "Sentiment analysis is not available for bills before 2020."}
    except Exception:
        pass 

    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )
        
        subreddit = reddit.subreddit("india+unitedstatesofindia+indiaspeaks")
        submissions = subreddit.search(bill_name, sort='relevance', time_filter='year', limit=25)
        
        comments_and_titles = []
        for post in submissions:
            comments_and_titles.append(post.title)
            post.comments.replace_more(limit=0)
            for comment in post.comments.list()[:5]:
                comments_and_titles.append(comment.body)

        if not comments_and_titles:
            return {'note': "No relevant posts found on Reddit for this bill."}

        positive, negative, neutral = 0, 0, 0
        for text in comments_and_titles:
            analysis = TextBlob(text)
            if analysis.sentiment.polarity > 0.1:
                positive += 1
            elif analysis.sentiment.polarity < -0.1:
                negative += 1
            else:
                neutral += 1
        
        total = len(comments_and_titles)
        return {
            'positive': round((positive / total) * 100),
            'negative': round((negative / total) * 100),
            'neutral': round((neutral / total) * 100)
        }
    except Exception as e:
        print(f"AGENT ERROR (Reddit API): {e}")
        return {'error': f"Could not fetch data from Reddit. Please check your API keys."}
