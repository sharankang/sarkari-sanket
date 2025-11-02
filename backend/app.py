from flask import Flask, request, jsonify
from flask_cors import CORS
from agent import get_bill_text_from_web, generate_detailed_summary, get_social_media_sentiment, compare_bills, find_matching_schemes
import PyPDF2
from io import BytesIO
import firebase_admin
from firebase_admin import credentials, auth, firestore
import os

try:
    key_path = "backend/firebase-key.json"
    if not os.path.exists(key_path):
        key_path = "firebase-key.json"
        if not os.path.exists(key_path):
            raise FileNotFoundError("firebase-key.json not found in 'backend/' or root.")
            
    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase connected successfully.")
except FileNotFoundError:
    print("CRITICAL WARNING: 'firebase-key.json' not found. Authentication features will fail.")
    db = None
except Exception as e:
    print(f"Firebase initialization error: {e}")
    db = None

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://127.0.0.1:5500",  # local frontend
            "http://localhost:3000",
            # "https://sharankang.github.io" # live frontend
        ]
    }
})

# Helper Function to Verify Token
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
        print(f"Error verifying token: {e}")
        return None

#Authentication Route
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
                'profile': {} # Empty profile
            })
        return jsonify({'uid': user.uid, 'email': user.email}), 201
    except auth.EmailAlreadyExistsError:
        return jsonify({'error': 'An account with this email already exists.'}), 400
    except Exception as e:
        return jsonify({'error': f'An error occurred: {e}'}), 500

#Bill Analysis Route
@app.route('/api/analyze', methods=['POST'])
def analyze_bill():
    try:
        user = get_user_from_token(request)
        file = request.files.get('bill_file')
        bill_name = request.form.get('bill_name')
        language = request.form.get('language', 'English')
        bill_text, source_url, bill_name_for_analysis = "", "", bill_name

        if file and file.filename != '':
            print("AGENT: Processing uploaded PDF file.")
            try:
                pdf_reader = PyPDF2.PdfReader(BytesIO(file.read()))
                for page in pdf_reader.pages:
                    bill_text += page.extract_text() or ""
            except Exception as e:
                print(f"Error reading PDF: {e}")
                return jsonify({'error': 'Could not read text from the uploaded PDF.'}), 500
            source_url = f"Uploaded File: {file.filename}"
            if not bill_name_for_analysis:
                bill_name_for_analysis = file.filename.replace('.pdf', '').replace('_', ' ')
        
        elif bill_name:
            print("AGENT: Processing by bill name, calling web scraper.")
            web_data = get_bill_text_from_web(bill_name)
            if web_data.get('error'):
                return jsonify({'error': web_data['error'], 'source_url': web_data.get('url')}), 500
            bill_text, source_url = web_data.get('text'), web_data.get('url')
        
        else:
            return jsonify({'error': 'Please enter a bill name or upload a PDF file.'}), 400

        if not bill_text:
            return jsonify({'error': 'Could not extract readable text from the provided source.'}), 500

        summary = generate_detailed_summary(bill_text, bill_name_for_analysis, language)
        sentiment = get_social_media_sentiment(bill_name_for_analysis)
        
        if user and db:
            try:
                user_id = user['uid']
                history_ref = db.collection('users').document(user_id).collection('history').document()
                sentiment_to_save = sentiment.get('note') or sentiment.get('error') if sentiment.get('note') or sentiment.get('error') else sentiment
                history_ref.set({
                    'billName': bill_name_for_analysis, 'summary': summary,
                    'sentiment': sentiment_to_save, 'source': source_url,
                    'date': firestore.SERVER_TIMESTAMP
                })
                print(f"Saved history for user {user_id}")
            except Exception as e:
                print(f"Error saving history: {e}")

        return jsonify({'summary': summary, 'sentiment': sentiment, 'source_url': source_url})
    except Exception as e:
        print(f"A critical error occurred in /api/analyze: {e}")
        return jsonify({'error': 'A critical internal error occurred.'}), 500

#History Route
@app.route('/api/get-history', methods=['GET'])
def get_history():
    user = get_user_from_token(request)
    if not user: return jsonify({'error': 'Not authorized. Please log in.'}), 401
    if not db: return jsonify({'error': 'Database not connected'}), 500
    try:
        user_id = user['uid']
        history_ref = db.collection('users').document(user_id).collection('history').order_by('date', direction=firestore.Query.DESCENDING).limit(5)
        docs = history_ref.stream()
        history_list = []
        for doc in docs:
            data = doc.to_dict()
            if data.get('date'):
                data['date'] = data['date'].strftime('%Y-%m-%d %H:%M:%S')
            data['id'] = doc.id
            history_list.append(data)
        return jsonify(history_list), 200
    except Exception as e:
        print(f"Error fetching history: {e}")
        return jsonify({'error': 'Could not fetch history.'}), 500

#Compare Route
@app.route('/api/compare', methods=['POST'])
def compare_bill_versions():
    data = request.get_json()
    bill_name = data.get('bill_name')
    older_year = data.get('older_year')
    language = data.get('language', 'English')

    if not bill_name or not older_year:
        return jsonify({'error': 'bill_name and older_year are required fields'}), 400
    try:
        comparison_result = compare_bills(bill_name, older_year, language)
        if "Error:" in comparison_result:
            return jsonify({'error': comparison_result}), 500
        return jsonify({'comparison': comparison_result})
    except Exception as e:
        print(f"Error in /api/compare route: {e}")
        return jsonify({'error': 'A critical internal error occurred.'}), 500


@app.route('/api/get-profile', methods=['GET'])
def get_profile():
    user = get_user_from_token(request)
    if not user: return jsonify({'error': 'Not authorized'}), 401
    if not db: return jsonify({'error': 'Database not connected'}), 500

    try:
        user_ref = db.collection('users').document(user['uid'])
        doc = user_ref.get()
        if doc.exists:
            profile_data = doc.to_dict().get('profile', {})
            return jsonify(profile_data), 200
        else:
            return jsonify({}), 200
    except Exception as e:
        return jsonify({'error': f'An error occurred: {e}'}), 500

@app.route('/api/update-profile', methods=['POST'])
def update_profile():
    user = get_user_from_token(request)
    if not user: return jsonify({'error': 'Not authorized'}), 401
    if not db: return jsonify({'error': 'Database not connected'}), 500

    profile_data = request.get_json()
    if not profile_data:
        return jsonify({'error': 'No profile data provided'}), 400

    try:
        user_ref = db.collection('users').document(user['uid'])
        user_ref.set({'profile': profile_data}, merge=True)
        return jsonify({'success': True, 'message': 'Profile updated!'}), 200
    except Exception as e:
        return jsonify({'error': f'An error occurred: {e}'}), 500

@app.route('/api/find-schemes', methods=['GET'])
def find_schemes():
    user = get_user_from_token(request)
    if not user: return jsonify({'error': 'Not authorized'}), 401
    if not db: return jsonify({'error': 'Database not connected'}), 500

    try:
        #Get the user's saved profile
        user_ref = db.collection('users').document(user['uid'])
        doc = user_ref.get()
        if not doc.exists or not doc.to_dict().get('profile'):
            return jsonify({'error': 'Please save your profile first.'}), 400
        
        profile = doc.to_dict().get('profile')
        
        #Call the new agent function
        schemes_result = find_matching_schemes(profile)
        
        if schemes_result.get("error"):
            return jsonify({'error': schemes_result.get("error")}), 500
            
        return jsonify(schemes_result), 200

    except Exception as e:
        print(f"Error in /api/find-schemes: {e}")
        return jsonify({'error': 'A critical internal error occurred.'}), 500


@app.route('/')
def home():
    return "Backend server for Sarkari Sanket is running!"

if __name__ == '__main__':
    app.run(debug=True, port=5000)