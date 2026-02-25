from flask import Flask, request, jsonify
from flask_cors import CORS
from agent import (
    get_bill_text_from_web, 
    generate_detailed_summary, 
    get_social_media_sentiment, 
    compare_bills, 
    find_matching_schemes,
    ask_sarkari_mitra,
    calculate_impact_scores,
    get_bill_news
)
import PyPDF2
from io import BytesIO
import firebase_admin
from firebase_admin import credentials, auth, firestore
import os
import traceback


try:
    key_path = "backend/firebase-key.json"
    if not os.path.exists(key_path):
        key_path = "firebase-key.json"
    
    if os.path.exists(key_path):
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("AGENT: Firebase connected successfully.")
    else:
        print("AGENT CRITICAL WARNING: 'firebase-key.json' not found. DB features will fail.")
        db = None
except Exception as e:
    print(f"AGENT ERROR: Firebase initialization error: {e}")
    db = None

app = Flask(__name__)


CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://sharankang.github.io",
            "http://127.0.0.1:5500",
            "http://127.0.0.1:5501",
            "http://localhost:3000"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Helper function to verify token
def get_user_from_token(request):
    id_token = request.headers.get('Authorization')
    if not id_token:
        return None
    if id_token.startswith('Bearer '):
        id_token = id_token.split('Bearer ')[1]
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        print(f"AGENT: Error verifying token: {e}")
        return None



@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400
    try:
        user = auth.create_user(email=email, password=password)
        if db:
            user_ref = db.collection('users').document(user.uid)
            user_ref.set({
                'email': user.email,
                'created_at': firestore.SERVER_TIMESTAMP,
                'profile': {} 
            })
        return jsonify({'uid': user.uid, 'email': user.email}), 201
    except auth.EmailAlreadyExistsError:
        return jsonify({'error': 'An account with this email already exists.'}), 400
    except Exception as e:
        return jsonify({'error': f'An error occurred: {e}'}), 500



@app.route('/api/analyze', methods=['POST'])
def analyze_bill():
    try:
        user = get_user_from_token(request)
        file = request.files.get('bill_file')
        bill_name = request.form.get('bill_name')
        language = request.form.get('language', 'English')
        bill_text, source_url, bill_name_for_analysis = "", "", bill_name

        # Text extraction
        if file and file.filename != '':
            try:
                pdf_reader = PyPDF2.PdfReader(BytesIO(file.read()))
                for page in pdf_reader.pages:
                    bill_text += page.extract_text() or ""
                source_url = f"Uploaded File: {file.filename}"
                if not bill_name_for_analysis:
                    bill_name_for_analysis = file.filename.replace('.pdf', '').replace('_', ' ')
            except Exception as e:
                return jsonify({'error': 'Could not read uploaded PDF.'}), 500
        
        elif bill_name:
            web_data = get_bill_text_from_web(bill_name)
            if web_data.get('error'):
                return jsonify({'error': web_data['error'], 'source_url': web_data.get('url')}), 400
            bill_text, source_url = web_data.get('text'), web_data.get('url')
        
        else:
            return jsonify({'error': 'Provide a bill name or PDF file.'}), 400

        if not bill_text:
            return jsonify({'error': 'Could not extract text.'}), 500

        #Sequential analysis processing
        summary = generate_detailed_summary(bill_text, bill_name_for_analysis, language)
        sentiment = get_social_media_sentiment(bill_name_for_analysis)
        impact_scores = calculate_impact_scores(bill_text)
        news = get_bill_news(bill_name_for_analysis)
        
        #History management
        if user and db:
            try:
                history_ref = db.collection('users').document(user['uid']).collection('history').document()
                sentiment_data = sentiment.get('note') or sentiment.get('error') or sentiment
                history_ref.set({
                    'billName': bill_name_for_analysis, 
                    'summary': summary,
                    'sentiment': sentiment_data, 
                    'source': source_url,
                    'date': firestore.SERVER_TIMESTAMP
                })
            except Exception as e:
                print(f"AGENT: History Save Error: {e}")

        #Final response construction
        return jsonify({
            'summary': summary, 
            'sentiment': sentiment, 
            'source_url': source_url,
            'impact_scores': impact_scores,
            'news': news,
            'bill_text': bill_text[:8000]
        })
    except Exception as e:
        print("AGENT CRITICAL ERROR in /api/analyze:")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat_with_mitra():
    data = request.get_json()
    bill_text = data.get('bill_text')
    query = data.get('query')
    language = data.get('language', 'English')
    
    if not bill_text or not query:
        return jsonify({'error': 'Missing context/query'}), 400
        
    answer = ask_sarkari_mitra(bill_text, query, language)
    return jsonify({'answer': answer})

@app.route('/api/compare', methods=['POST'])
def compare_bill_versions():
    data = request.get_json()
    bill_name = data.get('bill_name')
    older_year = data.get('older_year')
    language = data.get('language', 'English')

    if not bill_name or not older_year:
        return jsonify({'error': 'Required: bill_name, older_year'}), 400
    try:
        result = compare_bills(bill_name, older_year, language)
        return jsonify({'comparison': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/get-profile', methods=['GET'])
def get_profile():
    user = get_user_from_token(request)
    if not user or not db: return jsonify({'error': 'Not authorized'}), 401
    try:
        doc = db.collection('users').document(user['uid']).get()
        return jsonify(doc.to_dict().get('profile', {})) if doc.exists else jsonify({}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-profile', methods=['POST'])
def update_profile():
    user = get_user_from_token(request)
    if not user or not db: return jsonify({'error': 'Not authorized'}), 401
    profile_data = request.get_json()
    try:
        db.collection('users').document(user['uid']).set({'profile': profile_data}, merge=True)
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/find-schemes', methods=['GET'])
def find_schemes():
    user = get_user_from_token(request)
    if not user or not db: return jsonify({'error': 'Not authorized'}), 401
    try:
        doc = db.collection('users').document(user['uid']).get()
        if not doc.exists or not doc.to_dict().get('profile'):
            return jsonify({'error': 'Profile not found'}), 400
        
        schemes = find_matching_schemes(doc.to_dict().get('profile'))
        return jsonify(schemes), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-history', methods=['GET'])
def get_history():
    user = get_user_from_token(request)
    if not user or not db: return jsonify({'error': 'Not authorized'}), 401
    try:
        docs = db.collection('users').document(user['uid']).collection('history').order_by('date', direction=firestore.Query.DESCENDING).limit(5).stream()
        history = []
        for doc in docs:
            d = doc.to_dict()
            if d.get('date'): d['date'] = d['date'].strftime('%Y-%m-%d %H:%M:%S')
            d['id'] = doc.id
            history.append(d)
        return jsonify(history), 200
    except Exception as e:
        return jsonify({'error': 'History fetch failed.'}), 500

@app.route('/')
def home():
    return "Sarkari Sanket Backend Online."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)