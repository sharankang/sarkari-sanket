import requests
import google.generativeai as genai
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from textblob import TextBlob
import PyPDF2
from io import BytesIO
import praw
import re
from datetime import datetime

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
    print(f"AGENT: Starting resilient search for '{bill_name}'...")
    if not GOOGLE_API_KEY or not SEARCH_ENGINE_ID:
        return {'error': "Google API keys are not configured."}
    
    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY, static_discovery=False)
        query = bill_name
        res = service.cse().list(q=query, cx=SEARCH_ENGINE_ID, num=5).execute()

        if 'items' not in res or not res['items']:
            return {'error': "Sorry, no search results were found for this bill."}
        
        trusted_domains = ['prsindia.org', 'gov.in', 'nic.in', 'sansad.in', 'legislative.gov.in', 'pib.gov.in', 'indiacode.nic.in']
        
        for i, item in enumerate(res['items']):
            source_url = item['link']
            print(f"\nAGENT: Attempt {i+1}: Trying source -> {source_url}")

            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(source_url, headers=headers, timeout=20)
                response.raise_for_status()
                
                scraped_text = ""
                if source_url.lower().endswith('.pdf'):
                    print("AGENT: PDF detected. Attempting to read with PyPDF2.")
                    pdf_file = BytesIO(response.content)
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    for page in pdf_reader.pages:
                        scraped_text += page.extract_text() or ""
                else:
                    print("AGENT: HTML detected. Attempting to read with BeautifulSoup.")
                    soup = BeautifulSoup(response.content, 'html.parser')
                    paragraphs = soup.find_all('p')
                    if paragraphs:
                        scraped_text = ' '.join(p.get_text() for p in paragraphs)
                
                if scraped_text and len(scraped_text) > 100:
                    print(f"AGENT: SUCCESS! Found and read readable text from {source_url}")
                    return {'text': scraped_text[:4000], 'url': source_url, 'error': None}
                else:
                    print("AGENT: Source was accessible, but contained no readable text.")

            except requests.exceptions.RequestException as e:
                print(f"AGENT: FAILED to connect to the source. Error: {e}")
            except Exception as e:
                print(f"AGENT: FAILED to parse the source. Error: {e}")
        
        return {'error': "Could not find and access a readable source after trying multiple links."}

    except Exception as e:
        print(f"--- DETAILED AGENT ERROR (Google Search API) ---\n{e}\n--------------------------")
        return {'error': f"A critical error occurred with the Google Search API: {e}"}


def generate_detailed_summary(bill_text: str, bill_name: str, language: str) -> str:
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
    print(f"AGENT: Starting sentiment analysis for '{bill_name}'...")
    if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT]):
        return {'error': "Reddit API keys are not fully configured."}

    time_period = 'year' # Default to 'year' for recent bills
    try:
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', bill_name)
        if year_match:
            bill_year = int(year_match.group(0))
            current_year = datetime.now().year
            
            if bill_year < 2020:
                print(f"AGENT: Bill year ({bill_year}) is before 2020. Skipping sentiment analysis.")
                return {'note': "Sentiment analysis is not available for bills before 2020."}
            
            if bill_year < current_year:
                time_period = 'all'
                print(f"AGENT: Bill from a past year ({bill_year}). Setting time filter to 'all'.")

    except Exception:
        pass 

    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )
        
        print(f"AGENT: Searching Reddit with time_filter='{time_period}'...")
        subreddit = reddit.subreddit("india+unitedstatesofindia+indiaspeaks")
        submissions = subreddit.search(bill_name, sort='relevance', time_filter=time_period, limit=25)
        
        comments_and_titles = []
        for post in submissions:
            comments_and_titles.append(post.title)
            post.comments.replace_more(limit=0)
            for comment in post.comments.list()[:5]:
                comments_and_titles.append(comment.body)

        if not comments_and_titles:
            print("AGENT: No relevant Reddit posts found.")
            return {'note': "No relevant posts found on Reddit for this bill."}
        
        print(f"AGENT: Found {len(comments_and_titles)} posts and comments to analyze.")
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
        result = {
            'positive': round((positive / total) * 100),
            'negative': round((negative / total) * 100),
            'neutral': round((neutral / total) * 100)
        }
        print(f"AGENT: Sentiment analysis complete. Result: {result}")
        return result

    except Exception as e:
        print(f"AGENT ERROR (Reddit API): {e}")
        return {'error': f"Could not fetch data from Reddit. Please check your API keys."}

