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
    AGENT STEP 1: Finds and scrapes the text of a bill.
    (This is your working resilient version - UNCHANGED)
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
                    print(f"AGENT: SUCCESS! Found and read readable text from {source_url}")
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
    AGENT STEP 2: Sends text to Gemini for a detailed summary.
    (This is your working version - UNCHANGED)
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
    (This is your working version - UNCHANGED)
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

def compare_bills(bill_name: str, older_year: str, language: str) -> str:
    """
    AGENT STEP 4: Compares the bill with an older version.
    (This is your teammate's function - UNCHANGED)
    """
    print(f"AGENT: Comparing '{bill_name}' with version from {older_year}...")

    if not GEMINI_API_KEY:
        return "Error: Gemini API key is not configured."

    #Fetch new bill
    new_bill_data = get_bill_text_from_web(bill_name)
    if new_bill_data.get("error"):
        return f"Could not fetch new bill: {new_bill_data['error']}"

    #Fetch old bill
    old_bill_query = f"{' '.join(bill_name.split()[:-1])} {older_year}"
    print(f"AGENT: Searching for older version with query: '{old_bill_query}'")
    old_bill_data = get_bill_text_from_web(old_bill_query)
    if old_bill_data.get("error"):
        return f"Could not fetch older bill version ({older_year}): {old_bill_data['error']}"

    new_text = new_bill_data.get("text", "")
    old_text = old_bill_data.get("text", "")

    if not new_text or not old_text:
        return "Error: Could not extract text from one or both versions."

    #Summarize differences with Gemini
    model = genai.GenerativeModel("gemini-2.5-flash")

    language_instruction = (
        "Write the comparison in simple Hinglish for common citizens."
        if language == "Hinglish"
        else "Write the comparison in clear English for common citizens."
    )

    prompt = f"""
    You are an expert law analyst. Compare the following two versions of the same bill:

    NEW VERSION TEXT: "{new_text[:3000]}"
    OLD VERSION ({older_year}) TEXT: "{old_text[:3000]}"

    Task: Identify the main differences between these two texts. Focus on:
    - New clauses or sections that have been added.
    - Important clauses or rules that have been removed.
    - Any changes in scope, penalties, or powers.

    Structure your output with the following markdown headings:
    ### Key Additions
    - ...

    ### Key Removals
    - ...

    ### Major Changes
    - ...

    {language_instruction}
    """

    try:
        response = model.generate_content(prompt)
        print("AGENT: Comparison generated successfully.")
        return response.text
    except Exception as e:
        print(f"AGENT ERROR (Comparison): {e}")
        return f"Error occurred while comparing bills: {e}"


def find_matching_schemes(profile: dict) -> dict:
    """
    AGENT STEP 5: Takes a user profile, finds scheme *names*,
    and then finds the *direct link* for each name.
    """
    print(f"AGENT: Finding schemes for profile: {profile}")
    if not all([GOOGLE_API_KEY, SEARCH_ENGINE_ID, GEMINI_API_KEY]):
        return {'error': "API keys are not configured."}

    #Create the initial search query
    query_parts = ["government schemes"]
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
        query_parts.append("for married couples")
    elif profile.get('marital_status') == 'widowed':
        query_parts.append("for widows")
        
    if profile.get('parental_status') == 'orphan':
        query_parts.append("for orphans")
    elif profile.get('parental_status') == 'one_alive':
        query_parts.append("for single parent child")

    query = " ".join(query_parts)
    print(f"AGENT: Generated Search Query: {query}")

    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY, static_discovery=False)
        
        search_query = f"{query} -filetype:pdf (site:gov.in OR site:nic.in OR site:myScheme.gov.in)"
        print(f"AGENT: Executing search: {search_query}")
        
        res = service.cse().list(q=search_query, cx=SEARCH_ENGINE_ID, num=5).execute()
        
        if 'items' not in res or not res['items']:
            return {'error': "Sorry, no relevant scheme websites were found for your profile."}
        
        google_results = []
        for item in res['items']:
            google_results.append({
                "title": item.get('title'),
                "link": item.get('link'),
                "snippet": item.get('snippet')
            })
        
        #Gemini to match schemes from results
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        You are an AI assistant. Here is a user's profile and a list of Google search results.
        Your task is to analyze the Google results and find schemes that *actually match* the user's profile.

        USER PROFILE:
        {profile}

        GOOGLE RESULTS:
        {json.dumps(google_results, indent=2)}

        Task: Find up to 3 relevant schemes from the Google results that are the best match for the user's profile.
        For each scheme, provide:
        1. "scheme_name": The official scheme name (use the 'title' from the search result).
        2. "summary": A 1-2 sentence summary of what it does (use the 'snippet' from the search result, rephrased if needed).
        3. "eligibility": A 1-sentence summary of eligibility (based on the 'snippet').
        4. "link": The 'link' from the *exact same* search result.

        Rules:
        - You MUST use the `link` from the search result you are referencing.
        - Do not invent schemes. Only use information from the provided Google results.
        - If a search result is irrelevant (e.t., a news article, a generic portal homepage), ignore it.
        - If none of the search results are relevant, return an empty list [].

        Return your answer as a JSON list. For example:
        [
          {{
            "scheme_name": "Kalpana Chawla Chhatravriti Yojana, Himachal Pradesh",
            "summary": "This scheme provides scholarships to meritorious girl students of Himachal Pradesh.",
            "eligibility": "For meritorious girl students of Himachal Pradesh.",
            "link": "https://hpepass.cgg.gov.in/NewHomePage.do?actionParameter=schemes"
          }}
        ]
        """
        response = model.generate_content(prompt)
        print("AGENT: Gemini has processed the Google results.")
        
        json_response_text = response.text.strip().lstrip("```json").rstrip("```")
        
        try:
            schemes_list = json.loads(json_response_text)
        except json.JSONDecodeError:
            print(f"AGENT ERROR: Gemini did not return valid JSON. Response: {json_response_text}")
            return {'error': "The AI assistant returned an invalid format."}

        if not schemes_list:
            return {"schemes": "[]", "sources": [res['items'][0]['link']]} # Return empty list if no matches

        print(f"AGENT: Found {len(schemes_list)} matching schemes.")

        #Return the final, augmented JSON
        final_json_string = json.dumps(schemes_list, indent=2)
        return {"schemes": final_json_string, "sources": [r['link'] for r in google_results]}

    except Exception as e:
        print(f"--- DETAILED AGENT ERROR (find_schemes) ---\n{e}\n--------------------------")
        return {'error': f"A critical error occurred while finding schemes: {e}"}