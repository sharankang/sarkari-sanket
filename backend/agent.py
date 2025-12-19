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
import json

# Load Configuration
try:
    from config import (
        GOOGLE_API_KEY, SEARCH_ENGINE_ID, GEMINI_API_KEY,
        REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
    )
except ImportError:
    GOOGLE_API_KEY, SEARCH_ENGINE_ID, GEMINI_API_KEY = None, None, None
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT = None, None, None

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def get_bill_text_from_web(bill_name: str):
    """
    AGENT STEP 1: Finds and scrapes the text of a bill using Google Search API.
    """
    print(f"AGENT: Starting resilient search for '{bill_name}'...")
    if not GOOGLE_API_KEY or not SEARCH_ENGINE_ID:
        return {'error': "Google API keys are not configured."}
    
    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY, static_discovery=False)
        query = bill_name
        res = service.cse().list(q=query, cx=SEARCH_ENGINE_ID, num=5).execute()

        if 'items' not in res or not res['items']:
            return {'error': "Sorry, no search results were found for this bill."}
        
        for i, item in enumerate(res['items']):
            source_url = item['link']
            print(f"\nAGENT: Attempt {i+1}: Trying source -> {source_url}")

            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(source_url, headers=headers, timeout=20)
                response.raise_for_status()
                
                scraped_text = ""
                if source_url.lower().endswith('.pdf'):
                    pdf_file = BytesIO(response.content)
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    for page in pdf_reader.pages:
                        scraped_text += page.extract_text() or ""
                else:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    paragraphs = soup.find_all('p')
                    if paragraphs:
                        scraped_text = ' '.join(p.get_text() for p in paragraphs)
                
                if scraped_text and len(scraped_text) > 100:
                    print(f"AGENT: SUCCESS! Found readable text from {source_url}")
                    return {'text': scraped_text, 'url': source_url, 'error': None}
                else:
                    print("AGENT: Source was accessible, but contained no readable text.")

            except Exception as e:
                print(f"AGENT: FAILED to process source. Error: {e}")
        
        return {'error': "Could not find and access a readable source after trying multiple links."}

    except Exception as e:
        print(f"--- DETAILED AGENT ERROR (Google Search API) ---\n{e}\n--------------------------")
        return {'error': f"A critical error occurred with the Google Search API: {e}"}


def generate_detailed_summary(bill_text: str, bill_name: str, language: str) -> str:
    """
    AGENT STEP 2: Sends text to Gemini for a detailed summary in English or Hinglish.
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

    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"""
    You are an expert policy analyst named 'Sarkari Sanket'. Your task is to analyze the provided text of a government bill and {language_instruction}
    The bill name is: "{bill_name}"
    The bill text is: "{bill_text[:4000]}"
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
    AGENT STEP 3: Gathers and analyzes sentiment from Reddit.
    """
    print(f"AGENT: Starting sentiment analysis for '{bill_name}'...")
    if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT]):
        return {'error': "Reddit API keys are not fully configured."}

    time_period = 'year'
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


def compare_bills(bill_name, older_year, language):
    """AGENT STEP 4: Simplified comparison of two bill versions."""
    new_data = get_bill_text_from_web(bill_name)
    old_data = get_bill_text_from_web(f"{bill_name} {older_year}")
    
    if "error" in new_data or "error" in old_data:
        return "Error: Could not find both versions of the bill for comparison."

    new_text = new_data.get('text', '')
    old_text = old_data.get('text', '')

    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"""
    Compare these bills simply. 
    NEW: {new_text[:2500]}
    OLD: {old_text[:2500]}
    
    CRITICAL: Be extremely brief for a citizen. Max 3 bullets per heading. 
    Each bullet point MUST be under 15 words. Avoid legal jargon.
    ### Key Additions
    ### Key Removals
    ### Major Changes
    Answer in {language}.
    """
    try: return model.generate_content(prompt).text
    except Exception as e: return str(e)

def find_matching_schemes(profile: dict) -> dict:
    """
    AGENT STEP 5: Takes a user profile and finds matching government schemes.
    Enhanced to handle all 9+ profile fields and provide terminal debugging.
    """
    print(f"\nAGENT: --- STARTING SCHEME SEARCH ---")
    print(f"AGENT: Input Profile: {profile}")
    
    if not all([GOOGLE_API_KEY, SEARCH_ENGINE_ID, GEMINI_API_KEY]):
        print("AGENT ERROR: Configuration keys missing in agent.py")
        return {'error': "API keys are not configured."}

    # Create the search query using the full 9-field profile data
    query_parts = ["government schemes India"]
    
    if profile.get('occupation'):
        query_parts.append(f"for {profile['occupation']}")
    
    if profile.get('state'):
        query_parts.append(f"in {profile['state']}")
    
    if profile.get('category') and profile.get('category') not in ['general', '---']:
        query_parts.append(f"for {profile['category']} category")
    
    if profile.get('sex'):
        query_parts.append(f"for {profile['sex']}")
        
    if profile.get('is_only_girl_child') == 'yes':
        query_parts.append("for only girl child")
        
    if profile.get('marital_status') == 'married':
        query_parts.append("for married")
    elif profile.get('marital_status') == 'widowed':
        query_parts.append("for widows")
        
    if profile.get('parental_status') == 'orphan':
        query_parts.append("for orphans")

    # Final query construction
    query = " ".join(query_parts)
    print(f"AGENT: Final Search Query: {query}")

    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY, static_discovery=False)
        
        # Restricting search to official gov domains for better quality
        search_query = f"{query} -filetype:pdf (site:gov.in OR site:nic.in OR site:myScheme.gov.in)"
        print(f"AGENT: Executing Google CSE Search: {search_query}")
        
        res = service.cse().list(q=search_query, cx=SEARCH_ENGINE_ID, num=5).execute()
        
        if 'items' not in res or not res['items']:
            print("AGENT WARNING: Google CSE returned ZERO results.")
            return {'error': "Google search could not find any official government scheme links for this profile."}
        
        print(f"AGENT: Found {len(res['items'])} potential links. Passing to Gemini for matching...")

        google_results = []
        for item in res['items']:
            google_results.append({
                "title": item.get('title'),
                "link": item.get('link'),
                "snippet": item.get('snippet')
            })
        
        # Using the model name you confirmed works
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        prompt = f"""
        You are an AI assistant helping a citizen find government schemes. 
        Analyze these Google search results against the user's profile.

        USER PROFILE:
        {profile}

        GOOGLE SEARCH RESULTS:
        {json.dumps(google_results, indent=2)}

        TASK: 
        Find the top 3 schemes from the search results that are a direct match for this user.
        Return ONLY a JSON list of objects with these keys:
        - "scheme_name": Official name of the scheme.
        - "summary": 1-2 sentence description of benefits.
        - "eligibility": 1-sentence summary of who can apply.
        - "link": The exact URL from the search result.

        RULES:
        1. Use the EXACT links provided in the results.
        2. If a result is just a news article or generic home page, ignore it.
        3. If NO schemes match, return an empty list: [].
        """
        
        response = model.generate_content(prompt)
        print("AGENT: Gemini analysis complete.")
        
        # Clean the response text for JSON parsing
        json_response_text = response.text.strip().lstrip("```json").rstrip("```")
        
        try:
            schemes_list = json.loads(json_response_text)
            print(f"AGENT: Successfully identified {len(schemes_list)} matching schemes.")
            
            # Return the JSON list stringified so script.js double-parsing works
            return {
                "schemes": json.dumps(schemes_list), 
                "sources": [r['link'] for r in google_results]
            }
            
        except json.JSONDecodeError:
            print("AGENT ERROR: Gemini returned invalid JSON format.")
            return {'error': "The AI assistant returned an invalid response format."}

    except Exception as e:
        print(f"AGENT CRITICAL ERROR in find_matching_schemes: {str(e)}")
        return {'error': f"A critical error occurred while searching: {str(e)}"}


def ask_sarkari_mitra(bill_text, query, language):
    """
    AGENT STEP 6: Context-aware AI chatbot assistant (Sarkari Mitra).
    """
    print(f"AGENT: Sarkari Mitra processing query in {language}...")
    if not GEMINI_API_KEY:
        return "Error: Gemini API key is not configured."

    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    You are 'Sarkari Mitra', a helpful policy assistant. 
    Context (Bill Text): {bill_text[:6000]} 
    User Question: {query}
    Provide a helpful, concise answer in {language}. 
    If the question is unrelated to the bill, politely guide them back.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"AGENT ERROR (Sarkari Mitra): {e}")
        return f"Sorry, I encountered an error: {e}"


def calculate_impact_scores(bill_text):
    """
    AGENT STEP 7: DYNAMIC Demographic-specific impact scorer.
    Identifies relevant groups based on bill content and scores them.
    """
    print("AGENT: Dynamically identifying and scoring demographic impact...")
    if not GEMINI_API_KEY:
        return {}

    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    Analyze this bill text: {bill_text[:4000]}
    
    TASK:
    1. Identify the 4 specific demographic groups or citizen categories most affected by this bill (e.g., 'Freelancers', 'Industrial Workers', 'Rural Women', 'Startups', etc.).
    2. For each identified group, provide an 'Impact Score' (1-100).
    3. Provide a 1-sentence reason for that score.

    RULES:
    - Choose categories relevant to the specific bill content.
    - Return ONLY a JSON object with this exact structure:
    {{
        "Group_Name": {{"score": X, "reason": "..."}},
        "Group_Name_2": {{"score": Y, "reason": "..."}}
    }}
    """
    try:
        response = model.generate_content(prompt)
        # Clean JSON from markdown tags
        clean_json = response.text.strip().replace('```json', '').replace('```', '')
        raw_scores = json.loads(clean_json)
        
        return {k: v for k, v in raw_scores.items() if v['score'] > 20}
    except Exception as e:
        print(f"AGENT ERROR (Impact Scorer): {e}")
        return {}

def get_bill_news(bill_name):
    """
    AGENT STEP 8: Real-time news aggregator for the viewed bill.
    """
    print(f"AGENT: Fetching news for {bill_name}...")
    if not GOOGLE_API_KEY or not SEARCH_ENGINE_ID:
        return []

    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        # Query specifically for news/press releases
        res = service.cse().list(q=f"{bill_name} latest news press releases India", cx=SEARCH_ENGINE_ID, num=3).execute()
        news_items = []
        if 'items' in res:
            for item in res['items']:
                news_items.append({
                    'title': item['title'], 
                    'link': item['link'], 
                    'snippet': item['snippet']
                })
        return news_items
    except Exception as e:
        print(f"AGENT ERROR (News Aggregator): {e}")
        return []