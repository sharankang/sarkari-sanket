from flask import Flask, request, jsonify
from flask_cors import CORS
from agent import get_bill_text_from_web, generate_detailed_summary, get_social_media_sentiment

app = Flask(__name__)
# CORS(app, resources={r"/api/*": {"origins": ["http://127.0.0.1:5500", "http://localhost:3000", "http://127.0.0.1:8000", "https://sharankang.github.io"]}})

CORS(app)

@app.route('/')
def home():
    return "Backend server for Sarkari Sanket is running!"

@app.route('/api/analyze', methods=['POST'])
def analyze_bill():
    data = request.get_json()
    bill_name = data.get('bill_name')
    language = data.get('language', 'English') 
    
    if not bill_name:
        return jsonify({'error': 'bill_name is a required field'}), 400
    try:
        web_data = get_bill_text_from_web(bill_name)
        
        if web_data.get('error'):
            return jsonify({'error': web_data['error'], 'source_url': web_data.get('url')}), 500

        bill_text = web_data.get('text')
        source_url = web_data.get('url')

        #Pass language to the agent
        summary = generate_detailed_summary(bill_text, bill_name, language)
        sentiment = get_social_media_sentiment(bill_name)
        
        return jsonify({
            'summary': summary,
            'sentiment': sentiment,
            'source_url': source_url
        })
    except Exception as e:
        print(f"A critical error occurred in app.py: {e}")
        return jsonify({'error': 'A critical internal error occurred.'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
