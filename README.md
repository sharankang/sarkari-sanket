
## Sarkari Sanket is an AI-powered platform designed to simplify Indian government bills and schemes for the common citizen, offering simplified summaries, sentiment analysis, and personalized scheme recommendations.

### Features

1. Bill Simplification & Summary

- Upload any government bill (PDF) or enter its name.
- The AI agent scrapes the bill text and generates a simplified, easy-to-understand summary.
- Multi-language Support: Get summaries in English or Hinglish (Hindi + English).

2. Public Sentiment Analysis
   
- Analyzes public opinion on a bill by scanning social media (Reddit).
- Provides a sentiment score (Positive, Negative, Neutral) to show how people are reacting to the policy.

3. Find My Schemes (AI Agent)

- Users can create a personalized profile (Age, State, Income, Occupation, etc.).
- An intelligent agent searches government databases to find relevant welfare schemes tailored specifically to the user.
- Provides direct, verified links to official government portals.

4. Bill Comparison

- Compare two versions of a bill (e.g., a new 2023 bill vs. an old 1988 act) to see exactly what has changed.

### Tech Stack

- Frontend: HTML5, Tailwind CSS, JavaScript (Vanilla)
- Backend: Python, Flask
- AI & ML: - Google Gemini API (for summarization and reasoning)
- TextBlob (for sentiment analysis)
- Database & Auth: Firebase Firestore & Authentication
- APIs: - Google Custom Search API (for scraping bill text and schemes)
- PRAW (Reddit API for sentiment data)

