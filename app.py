# ============================================
# EXAM PREDICTOR - Flask Backend
# ============================================

from flask import Flask, render_template, request, jsonify
import os
import json
from analyzer import process_papers, get_demo_data, EXAM_TOPICS

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'data/raw_papers'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

ALLOWED_EXAMS = list(EXAM_TOPICS.keys())

# ============================================
# ROUTES
# ============================================

@app.route('/')
def home():
    exams = ALLOWED_EXAMS
    return render_template('index.html', exams=exams)


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        exam = request.form.get('exam', 'JEE Main')
        mode = request.form.get('mode', 'demo')

        # Demo mode
        if mode == 'demo':
            predictions = get_demo_data(exam)
            return jsonify({
                'success': True,
                'predictions': predictions,
                'exam': exam,
                'mode': 'demo',
                'total_topics': len(predictions)
            })

        # PDF mode
        files = request.files.getlist('pdfs')

        if not files or files[0].filename == '':
            predictions = get_demo_data(exam)
            return jsonify({
                'success': True,
                'predictions': predictions,
                'exam': exam,
                'mode': 'demo',
                'total_topics': len(predictions)
            })

        # Save uploaded files
        saved_paths = []
        for file in files:
            if file and file.filename.endswith('.pdf'):
                filepath = os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    file.filename
                )
                file.save(filepath)
                saved_paths.append(filepath)

        if not saved_paths:
            return jsonify({
                'success': False,
                'error': 'Koi valid PDF nahi mila'
            })

        # Process
        predictions = process_papers(saved_paths, exam)

        return jsonify({
            'success': True,
            'predictions': predictions,
            'exam': exam,
            'mode': 'pdf',
            'files_processed': len(saved_paths),
            'total_topics': len(predictions)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/exams')
def get_exams():
    return jsonify({'exams': ALLOWED_EXAMS})


# ============================================
# RUN
# ============================================

if __name__ == '__main__':
    os.makedirs('data/raw_papers', exist_ok=True)
    os.makedirs('data/processed', exist_ok=True)
    print("=" * 50)
    print("  ExamPredictor AI - Starting...")
    print("  Open: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)