# ============================================
# EXAM PREDICTOR - Flask Backend (v2.0)
# Render Deployment Ready
# ============================================

import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request,
    jsonify, session, send_file, abort
)
from werkzeug.utils import secure_filename

from analyzer import (
    process_papers,
    get_demo_data,
    EXAM_TOPICS,
    generate_timetable,
    track_syllabus_coverage,
    cleanup_files,
    analyze_difficulty,
    identify_question_patterns
)

# ============================================
# LOGGING SETUP
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# FLASK APP SETUP
# ============================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    'SECRET_KEY',
    'exampredictor-secret-key-2024'
)

# ============================================
# CONFIGURATION
# ============================================

class Config:
    UPLOAD_FOLDER = 'data/raw_papers'
    PROCESSED_FOLDER = 'data/processed'
    EXPORT_FOLDER = 'data/exports'

    # File settings
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    MAX_FILE_SIZE = 10 * 1024 * 1024
    MAX_FILES_PER_REQUEST = 10
    ALLOWED_EXTENSIONS = {'pdf'}

    # Rate limiting
    RATE_LIMIT_REQUESTS = 20
    RATE_LIMIT_WINDOW = 3600


app.config.from_object(Config)
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

# ============================================
# IN-MEMORY RATE LIMITER
# ============================================

request_tracker = {}


def is_rate_limited(ip):
    now = datetime.now()
    window_start = now - timedelta(
        seconds=Config.RATE_LIMIT_WINDOW
    )

    if ip in request_tracker:
        request_tracker[ip] = [
            t for t in request_tracker[ip]
            if t > window_start
        ]
    else:
        request_tracker[ip] = []

    if len(request_tracker[ip]) >= Config.RATE_LIMIT_REQUESTS:
        return True

    request_tracker[ip].append(now)
    return False


def rate_limit(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.environ.get(
            'HTTP_X_FORWARDED_FOR',
            request.remote_addr
        )
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()

        if is_rate_limited(ip):
            logger.warning(
                f"Rate limit exceeded for IP: {ip}"
            )
            return jsonify({
                'success': False,
                'error': 'Bahut zyada requests. '
                         'Thodi der baad try karo.',
                'retry_after': Config.RATE_LIMIT_WINDOW
            }), 429
        return f(*args, **kwargs)
    return decorated

# ============================================
# DATABASE - SIMPLE JSON BASED
# (SQLite removed - Render free mein
#  persistent storage nahi hoti)
# ============================================

def save_analysis_log(session_id, exam, mode,
                      predictions_count):
    """Simple log - no database needed"""
    logger.info(
        f"Analysis: session={session_id}, "
        f"exam={exam}, mode={mode}, "
        f"topics={predictions_count}"
    )

# ============================================
# FILE VALIDATION
# ============================================

def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower()
        in Config.ALLOWED_EXTENSIONS
    )


def validate_pdf_file(file):
    if not allowed_file(file.filename):
        return False, "Sirf PDF files allowed hain"

    try:
        header = file.read(5)
        file.seek(0)

        if not header.startswith(b'%PDF-'):
            return False, (
                f"{file.filename} valid PDF nahi hai"
            )
    except Exception:
        file.seek(0)

    return True, "Valid"


def validate_exam(exam):
    allowed_exams = list(EXAM_TOPICS.keys())
    if exam not in allowed_exams:
        return False, f"Invalid exam selected"
    return True, "Valid"

# ============================================
# SESSION MANAGEMENT
# ============================================

def get_or_create_session():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        session['created_at'] = datetime.now().isoformat()
        session['analyses_count'] = 0
    return session['session_id']

# ============================================
# ROUTES - MAIN
# ============================================

@app.route('/')
def home():
    session_id = get_or_create_session()
    exams = list(EXAM_TOPICS.keys())
    logger.info(f"Home visited - Session: {session_id}")
    return render_template(
        'index.html',
        exams=exams,
        exam_stats=[]
    )


@app.route('/analyze', methods=['POST'])
@rate_limit
def analyze():
    session_id = get_or_create_session()
    saved_paths = []

    try:
        exam = request.form.get('exam', 'JEE Main').strip()
        mode = request.form.get('mode', 'demo').strip()

        is_valid, msg = validate_exam(exam)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': msg
            }), 400

        logger.info(
            f"Analysis - Session: {session_id}, "
            f"Exam: {exam}, Mode: {mode}"
        )

        # ----------------------------------------
        # DEMO MODE
        # ----------------------------------------
        if mode == 'demo':
            predictions = get_demo_data(exam)
            difficulty = {
                'easy': 35, 'medium': 40, 'hard': 25
            }
            patterns = {
                'MCQ': 60, 'Numerical': 25,
                'Proof': 8, 'Conceptual': 7
            }

            save_analysis_log(
                session_id, exam, 'demo',
                len(predictions)
            )

            session['analyses_count'] = \
                session.get('analyses_count', 0) + 1

            return jsonify({
                'success': True,
                'analysis_id': str(uuid.uuid4()),
                'predictions': predictions,
                'exam': exam,
                'mode': 'demo',
                'total_topics': len(predictions),
                'difficulty_analysis': difficulty,
                'question_patterns': patterns,
                'high_count': len([
                    p for p in predictions
                    if p['priority'] == 'high'
                ]),
                'medium_count': len([
                    p for p in predictions
                    if p['priority'] == 'medium'
                ]),
                'low_count': len([
                    p for p in predictions
                    if p['priority'] == 'low'
                ]),
                'message': 'Demo analysis complete!'
            })

        # ----------------------------------------
        # PDF MODE
        # ----------------------------------------
        files = request.files.getlist('pdfs')

        if not files or files[0].filename == '':
            predictions = get_demo_data(exam)
            return jsonify({
                'success': True,
                'predictions': predictions,
                'exam': exam,
                'mode': 'demo_fallback',
                'total_topics': len(predictions),
                'difficulty_analysis': {
                    'easy': 35,
                    'medium': 40,
                    'hard': 25
                },
                'question_patterns': {
                    'MCQ': 60, 'Numerical': 25,
                    'Proof': 8, 'Conceptual': 7
                },
                'high_count': len([
                    p for p in predictions
                    if p['priority'] == 'high'
                ]),
                'medium_count': len([
                    p for p in predictions
                    if p['priority'] == 'medium'
                ]),
                'low_count': len([
                    p for p in predictions
                    if p['priority'] == 'low'
                ]),
                'message': 'Koi file nahi mili - Demo data'
            })

        if len(files) > Config.MAX_FILES_PER_REQUEST:
            return jsonify({
                'success': False,
                'error': f'Maximum '
                         f'{Config.MAX_FILES_PER_REQUEST} '
                         f'files allowed hain'
            }), 400

        validation_errors = []

        for file in files:
            if not file or file.filename == '':
                continue

            is_valid, error_msg = validate_pdf_file(file)
            if not is_valid:
                validation_errors.append(
                    f"{file.filename}: {error_msg}"
                )
                continue

            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)

            if file_size > Config.MAX_FILE_SIZE:
                size_mb = Config.MAX_FILE_SIZE / 1024 / 1024
                validation_errors.append(
                    f"{file.filename}: "
                    f"{size_mb}MB se bada hai"
                )
                continue

            safe_name = secure_filename(file.filename)
            if not safe_name:
                safe_name = f"upload_{uuid.uuid4().hex}.pdf"

            unique_name = f"{uuid.uuid4().hex}_{safe_name}"
            filepath = os.path.join(
                app.config['UPLOAD_FOLDER'],
                unique_name
            )

            try:
                file.save(filepath)
                saved_paths.append(filepath)
                logger.info(f"File saved: {filepath}")
            except Exception as e:
                logger.error(f"File save error: {e}")
                validation_errors.append(
                    f"{file.filename}: Save nahi hua"
                )

        if not saved_paths:
            error_detail = (
                '\n'.join(validation_errors)
                if validation_errors
                else 'Koi valid PDF nahi mili'
            )
            return jsonify({
                'success': False,
                'error': error_detail
            }), 400

        result = process_papers(saved_paths, exam)
        predictions = result.get('predictions', [])
        difficulty = result.get('difficulty_analysis', {})
        patterns = result.get('question_patterns', {})

        timetable = generate_timetable(
            predictions=predictions,
            days_left=30,
            daily_hours=6
        )

        coverage = track_syllabus_coverage(
            predictions, exam
        )

        save_analysis_log(
            session_id, exam, 'pdf',
            len(predictions)
        )

        session['analyses_count'] = \
            session.get('analyses_count', 0) + 1

        return jsonify({
            'success': True,
            'analysis_id': str(uuid.uuid4()),
            'predictions': predictions,
            'exam': exam,
            'mode': result.get('mode', 'pdf'),
            'files_processed': result.get(
                'successful_files', 0
            ),
            'files_failed': result.get(
                'failed_files', 0
            ),
            'total_topics': len(predictions),
            'difficulty_analysis': difficulty,
            'question_patterns': patterns,
            'timetable': timetable,
            'syllabus_coverage': coverage,
            'high_count': len([
                p for p in predictions
                if p['priority'] == 'high'
            ]),
            'medium_count': len([
                p for p in predictions
                if p['priority'] == 'medium'
            ]),
            'low_count': len([
                p for p in predictions
                if p['priority'] == 'low'
            ]),
            'validation_warnings': (
                validation_errors
                if validation_errors else []
            )
        })

    except Exception as e:
        logger.error(f"Analyze error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Analysis mein problem aayi. '
                     'Dobara try karo.'
        }), 500

    finally:
        if saved_paths:
            cleanup_files(saved_paths)

# ============================================
# ROUTES - TIMETABLE
# ============================================

@app.route('/timetable', methods=['POST'])
@rate_limit
def get_timetable():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON data chahiye'
            }), 400

        exam = data.get('exam', 'JEE Main')
        days_left = int(data.get('days_left', 30))
        daily_hours = float(data.get('daily_hours', 6))

        is_valid, msg = validate_exam(exam)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': msg
            }), 400

        if not (1 <= days_left <= 365):
            return jsonify({
                'success': False,
                'error': 'Days 1 se 365 ke beech hone chahiye'
            }), 400

        if not (1 <= daily_hours <= 18):
            return jsonify({
                'success': False,
                'error': 'Hours 1 se 18 ke beech hone chahiye'
            }), 400

        predictions = get_demo_data(exam)
        timetable = generate_timetable(
            predictions=predictions,
            days_left=days_left,
            daily_hours=daily_hours
        )

        return jsonify({
            'success': True,
            'timetable': timetable,
            'exam': exam
        })

    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid numbers'
        }), 400
    except Exception as e:
        logger.error(f"Timetable error: {e}")
        return jsonify({
            'success': False,
            'error': 'Timetable generate nahi hua'
        }), 500

# ============================================
# ROUTES - COMPARE
# ============================================

@app.route('/compare', methods=['POST'])
@rate_limit
def compare_exams():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON data chahiye'
            }), 400

        exam1 = data.get('exam1', '')
        exam2 = data.get('exam2', '')

        for exam in [exam1, exam2]:
            is_valid, msg = validate_exam(exam)
            if not is_valid:
                return jsonify({
                    'success': False,
                    'error': f'{exam}: {msg}'
                }), 400

        if exam1 == exam2:
            return jsonify({
                'success': False,
                'error': 'Alag alag exams chuno'
            }), 400

        topics1 = set(EXAM_TOPICS.get(exam1, {}).keys())
        topics2 = set(EXAM_TOPICS.get(exam2, {}).keys())

        common = topics1 & topics2
        only_exam1 = topics1 - topics2
        only_exam2 = topics2 - topics1

        total_unique = len(topics1 | topics2)
        overlap_pct = (
            round(len(common) / total_unique * 100)
            if total_unique > 0 else 0
        )

        if overlap_pct >= 50:
            recommendation = (
                f"Bahut overlap hai! {exam1} aur {exam2} "
                f"ek saath prepare kar sakte ho. "
                f"{len(common)} common topics hain!"
            )
        elif overlap_pct >= 25:
            recommendation = (
                f"Decent overlap hai. "
                f"{len(common)} topics common hain."
            )
        else:
            recommendation = (
                f"Kam overlap hai. "
                f"Alag strategy chahiye dono ke liye."
            )

        return jsonify({
            'success': True,
            'exam1': exam1,
            'exam2': exam2,
            'common_topics': sorted(list(common)),
            'only_in_exam1': sorted(list(only_exam1)),
            'only_in_exam2': sorted(list(only_exam2)),
            'overlap_percentage': overlap_pct,
            'total_unique_topics': total_unique,
            'recommendation': recommendation
        })

    except Exception as e:
        logger.error(f"Compare error: {e}")
        return jsonify({
            'success': False,
            'error': 'Comparison nahi ho saka'
        }), 500

# ============================================
# ROUTES - FEEDBACK
# ============================================

@app.route('/feedback', methods=['POST'])
@rate_limit
def submit_feedback():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON data chahiye'
            }), 400

        rating = data.get('rating')
        comment = data.get('comment', '').strip()

        if rating is not None:
            rating = int(rating)
            if not (1 <= rating <= 5):
                return jsonify({
                    'success': False,
                    'error': 'Rating 1 se 5 ke beech'
                }), 400

        if len(comment) > 500:
            comment = comment[:500]

        logger.info(
            f"Feedback received: rating={rating}, "
            f"comment={comment[:50]}"
        )

        return jsonify({
            'success': True,
            'message': 'Feedback ke liye shukriya!'
        })

    except Exception as e:
        logger.error(f"Feedback error: {e}")
        return jsonify({
            'success': False,
            'error': 'Feedback submit nahi hua'
        }), 500

# ============================================
# ROUTES - CHAT
# ============================================

CHATBOT_KB = {
    "integration": """
📚 Integration Tips:
• Basic formulas yaad karo
• Substitution method sabse common
• Integration by parts: udv = uv - vdu
• Definite integrals - Properties use karo
⏱️ Daily 30 min practice karo
    """,
    "thermodynamics": """
🔥 Thermodynamics:
• First Law: dU = Q - W
• Carnot efficiency = 1 - T2/T1
• PV diagrams zaroor samjho
• Entropy concept clear karo
⚡ High priority topic!
    """,
    "organic chemistry": """
⚗️ Organic Chemistry:
• Named reactions list banao
• Mechanisms samjho - ratta nahi
• IUPAC nomenclature practice karo
• Functional group reactions yaad karo
📝 Flashcards banao
    """,
    "genetics": """
🧬 Genetics:
• Mendel laws - Numericals practice
• Dihybrid cross - Chi square test
• DNA structure aur replication
• Hardy Weinberg equation
💡 Diagrams banao!
    """,
    "human physiology": """
🫀 Human Physiology:
• Heart - Cardiac cycle, ECG
• Nephron - Filtration process
• Nervous system - Action potential
• Hormones - Glands aur target organs
📊 Highest weightage in NEET!
    """,
    "study plan": """
📅 Study Plan:
• High priority: 60% time
• Medium priority: 30% time
• Low priority: 10% time
• Daily revision zaruri
• Weekly mock tests lena
⏰ Consistency beats intensity!
    """,
    "time management": """
⏰ Time Management:
• Pomodoro - 25 min study, 5 min break
• Toughest subject pehle
• Phone door rakhna study mein
• Sleep 7-8 hours - Brain needs rest
💪 Quality over Quantity
    """,
    "motivation": """
💪 Motivation:
• Chhote daily goals set karo
• Progress track karo
• Study group join karo
• Apna 'why' yaad rakho
🎯 Ek din ek step - You can do it!
    """,
    "indian economy": """
💰 Indian Economy:
• Economic Survey padhna must
• RBI policies - Repo, CRR, SLR
• Recent govt schemes yaad karo
• GDP calculation methods
📰 Daily newspaper padhna shuru karo
    """,
    "data structures": """
💻 Data Structures:
• Arrays, Linked Lists basics
• Trees - BST, AVL
• Graph - BFS, DFS
• Hash tables
• Practice coding daily!
🖥️ LeetCode/HackerRank use karo
    """
}


@app.route('/chat', methods=['POST'])
@rate_limit
def chatbot():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Message chahiye'
            }), 400

        query = data.get('message', '').strip().lower()

        if not query:
            return jsonify({
                'success': False,
                'error': 'Empty message'
            }), 400

        if len(query) > 500:
            query = query[:500]

        best_match = None
        best_score = 0

        for key, response in CHATBOT_KB.items():
            score = 0
            key_words = key.split()
            for word in key_words:
                if word in query:
                    score += 1
            if key in query:
                score += 3

            if score > best_score:
                best_score = score
                best_match = response

        if best_match and best_score > 0:
            return jsonify({
                'success': True,
                'response': best_match.strip(),
                'matched': True
            })
        else:
            return jsonify({
                'success': True,
                'response': (
                    "🤔 Is topic ke baare mein info nahi.\n\n"
                    "Try karo:\n"
                    "• 'integration tips'\n"
                    "• 'study plan'\n"
                    "• 'time management'\n"
                    "• 'motivation'\n"
                    "• Koi topic name"
                ),
                'matched': False
            })

    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        return jsonify({
            'success': False,
            'error': 'Response nahi de saka'
        }), 500

# ============================================
# ROUTES - EXAMS LIST
# ============================================

@app.route('/exams')
def get_exams():
    exams_info = []
    for exam, topics in EXAM_TOPICS.items():
        exams_info.append({
            'name': exam,
            'total_topics': len(topics),
            'topics': list(topics.keys())
        })

    return jsonify({
        'success': True,
        'exams': exams_info,
        'total': len(exams_info)
    })


@app.route('/topics/<exam>')
def get_topics(exam):
    try:
        is_valid, msg = validate_exam(exam)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': msg
            }), 404

        topics = EXAM_TOPICS.get(exam, {})
        topics_list = []

        for topic, keywords in topics.items():
            topics_list.append({
                'topic': topic,
                'keywords_count': len(keywords),
                'sample_keywords': keywords[:3]
            })

        return jsonify({
            'success': True,
            'exam': exam,
            'topics': topics_list,
            'total': len(topics_list)
        })

    except Exception as e:
        logger.error(f"Topics error: {e}")
        return jsonify({
            'success': False,
            'error': 'Topics load nahi hue'
        }), 500

# ============================================
# HEALTH CHECK - Render ke liye
# ============================================

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'app': 'ExamPredictor AI',
        'version': '2.0',
        'timestamp': datetime.now().isoformat()
    }), 200

# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(400)
def bad_request(e):
    return jsonify({
        'success': False,
        'error': 'Bad request'
    }), 400


@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'success': False,
        'error': 'Page nahi mila'
    }), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({
        'success': False,
        'error': 'Method allowed nahi'
    }), 405


@app.errorhandler(413)
def file_too_large(e):
    return jsonify({
        'success': False,
        'error': 'File bahut badi hai. Max 50MB.'
    }), 413


@app.errorhandler(429)
def too_many_requests(e):
    return jsonify({
        'success': False,
        'error': 'Bahut zyada requests.'
    }), 429


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal error: {e}")
    return jsonify({
        'success': False,
        'error': 'Server error. Baad mein try karo.'
    }), 500

# ============================================
# SECURITY HEADERS
# ============================================

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# ============================================
# FOLDERS BANANA
# ============================================

def create_directories():
    folders = [
        'data/raw_papers',
        'data/processed',
        'data/exports',
        'static',
        'templates'
    ]
    for folder in folders:
        os.makedirs(folder, exist_ok=True)

# ============================================
# MAIN - RENDER KE LIYE FIXED
# ============================================

if __name__ == '__main__':
    print("=" * 50)
    print("  ExamPredictor AI v2.0 - Starting...")
    print("=" * 50)

    create_directories()

    # Render ka PORT environment variable use karo
    port = int(os.environ.get('PORT', 5000))

    print(f"  Port: {port}")
    print(f"  Exams: {len(EXAM_TOPICS)}")
    print("=" * 50)

    app.run(
        host='0.0.0.0',    # Render ke liye zaruri
        port=port,          # Render ka PORT use karo
        debug=False         # Production mein False
    )