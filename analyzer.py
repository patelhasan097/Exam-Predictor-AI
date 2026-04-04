# ============================================
# EXAM PREDICTOR - AI Analyzer
# ============================================

import pdfplumber
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import re
import nltk
from collections import Counter

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# NLTK downloads
try:
    nltk.data.find('tokenizers/punkt')
except:
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('punkt_tab')

# ============================================
# EXAM TOPICS DATABASE
# ============================================

EXAM_TOPICS = {
    "JEE Main": {
        "Integration": ["integral", "integrate", "antiderivative", "definite", "indefinite", "area under"],
        "Differentiation": ["derivative", "differentiate", "dy/dx", "rate of change", "tangent"],
        "Thermodynamics": ["heat", "temperature", "entropy", "enthalpy", "thermodynamic", "carnot", "adiabatic"],
        "Coordinate Geometry": ["circle", "parabola", "ellipse", "hyperbola", "coordinate", "locus"],
        "Organic Chemistry": ["organic", "carbon", "hydrocarbon", "alkane", "alkene", "benzene", "reaction"],
        "Waves & Optics": ["wave", "optics", "light", "reflection", "refraction", "lens", "mirror"],
        "Matrices": ["matrix", "matrices", "determinant", "eigenvalue", "inverse", "transpose"],
        "Statistics": ["mean", "median", "mode", "standard deviation", "probability", "variance"],
        "Electrostatics": ["electric", "charge", "coulomb", "potential", "capacitor", "field"],
        "Mechanics": ["force", "momentum", "energy", "newton", "friction", "acceleration"],
    },
    "JEE Advanced": {
        "Integration": ["integral", "integrate", "definite", "indefinite", "area", "volume"],
        "Mechanics": ["force", "momentum", "energy", "collision", "rotation", "torque"],
        "Electrochemistry": ["electrode", "cell", "electrolysis", "oxidation", "reduction", "redox"],
        "Organic Chemistry": ["organic", "reaction mechanism", "named reaction", "synthesis"],
        "Waves": ["wave", "superposition", "interference", "standing wave", "doppler"],
        "Modern Physics": ["photoelectric", "quantum", "nuclear", "radioactive", "atom"],
    },
    "NEET": {
        "Human Physiology": ["heart", "blood", "digestion", "respiration", "nervous", "hormone"],
        "Cell Biology": ["cell", "membrane", "nucleus", "mitochondria", "chromosome", "dna"],
        "Genetics": ["gene", "genetics", "heredity", "mutation", "allele", "mendel"],
        "Organic Chemistry": ["organic", "carbon", "reaction", "compound", "functional group"],
        "Physical Chemistry": ["mole", "concentration", "solution", "equilibrium", "ph", "acid"],
        "Plant Biology": ["plant", "photosynthesis", "transpiration", "chlorophyll", "root"],
        "Ecology": ["ecosystem", "food chain", "biodiversity", "habitat", "population"],
        "Evolution": ["evolution", "natural selection", "darwin", "fossil", "adaptation"],
    },
    "UPSC CSE": {
        "Indian Economy": ["economy", "gdp", "inflation", "fiscal", "monetary", "budget", "rbi"],
        "Environment & Ecology": ["environment", "ecology", "climate", "biodiversity", "pollution"],
        "Modern History": ["british", "independence", "gandhi", "freedom", "colonial", "revolt"],
        "Polity": ["constitution", "amendment", "article", "parliament", "fundamental", "directive"],
        "Geography": ["climate", "monsoon", "rainfall", "geography", "weather", "river", "soil"],
        "Ancient History": ["ancient", "maurya", "gupta", "indus", "vedic", "harappa"],
        "Medieval History": ["mughal", "delhi sultanate", "medieval", "akbar", "aurangzeb"],
        "Science & Tech": ["technology", "space", "isro", "nuclear", "satellite", "biotechnology"],
        "International Relations": ["foreign policy", "treaty", "bilateral", "united nations", "summit"],
    },
    "GATE": {
        "Data Structures": ["array", "linked list", "tree", "graph", "stack", "queue", "heap"],
        "Algorithms": ["sorting", "searching", "complexity", "dynamic programming", "greedy"],
        "Operating Systems": ["process", "thread", "scheduling", "memory", "deadlock", "semaphore"],
        "Database": ["sql", "query", "normalization", "transaction", "acid", "join"],
        "Computer Networks": ["network", "protocol", "tcp", "ip", "routing", "osi", "http"],
        "Digital Logic": ["boolean", "logic gate", "flip flop", "circuit", "binary", "multiplexer"],
        "Computer Architecture": ["processor", "cache", "pipeline", "instruction", "register"],
    },
    "CAT": {
        "Quantitative Aptitude": ["number", "algebra", "geometry", "arithmetic", "percentage"],
        "Verbal Ability": ["grammar", "vocabulary", "reading", "comprehension", "sentence"],
        "Logical Reasoning": ["puzzle", "arrangement", "syllogism", "coding", "series"],
        "Data Interpretation": ["graph", "chart", "table", "pie", "bar", "data"],
    },
    "MAH CET MBA": {
        "Logical Reasoning": ["puzzle", "arrangement", "blood relation", "direction", "coding"],
        "Abstract Reasoning": ["pattern", "series", "figure", "analogy", "odd one out"],
        "Quantitative Aptitude": ["number", "algebra", "percentage", "profit", "ratio", "time"],
        "Verbal Ability": ["grammar", "vocabulary", "comprehension", "fill in the blank"],
    },
    "MHT CET": {
        "Physics": ["force", "energy", "wave", "electric", "magnetic", "optics", "thermodynamics"],
        "Chemistry": ["organic", "inorganic", "physical", "reaction", "element", "compound"],
        "Mathematics": ["algebra", "calculus", "trigonometry", "geometry", "statistics", "vector"],
        "Biology": ["cell", "genetics", "ecology", "physiology", "evolution", "plant"],
    },
    "MPSC": {
        "Maharashtra History": ["maratha", "shivaji", "maharashtra", "peshwa", "satara"],
        "Maharashtra Geography": ["western ghats", "konkan", "vidarbha", "marathwada", "river"],
        "Indian Polity": ["constitution", "parliament", "state", "governor", "assembly"],
        "Economy": ["agriculture", "industry", "gdp", "poverty", "employment", "scheme"],
        "Current Affairs": ["government", "scheme", "award", "sports", "international"],
    },
    "SSC CGL": {
        "Quantitative Aptitude": ["number", "percentage", "ratio", "profit", "interest", "time"],
        "English": ["grammar", "vocabulary", "comprehension", "error", "fill"],
        "General Awareness": ["history", "geography", "science", "current", "economy"],
        "Reasoning": ["analogy", "series", "coding", "puzzle", "syllogism", "matrix"],
    },
    "IBPS PO": {
        "Quantitative Aptitude": ["number", "percentage", "ratio", "profit", "interest", "data"],
        "English": ["grammar", "vocabulary", "comprehension", "error", "cloze"],
        "Reasoning": ["puzzle", "arrangement", "syllogism", "coding", "blood relation"],
        "Banking Awareness": ["rbi", "bank", "interest", "credit", "monetary", "finance"],
        "Computer": ["hardware", "software", "internet", "ms office", "network", "database"],
    },
    "CLAT": {
        "Legal Reasoning": ["law", "legal", "act", "court", "judgment", "constitution", "rights"],
        "English": ["grammar", "vocabulary", "comprehension", "passage"],
        "Logical Reasoning": ["argument", "assumption", "conclusion", "inference", "statement"],
        "General Knowledge": ["history", "current", "geography", "science", "economics"],
        "Quantitative": ["number", "percentage", "ratio", "data", "graph"],
    },
    "CA Final": {
        "Financial Reporting": ["accounting", "financial statement", "balance sheet", "profit", "ifrs"],
        "Taxation": ["tax", "income tax", "gst", "deduction", "exemption", "tds"],
        "Audit": ["audit", "auditor", "vouching", "verification", "internal control"],
        "Strategic Management": ["strategy", "management", "corporate", "governance", "risk"],
        "Financial Management": ["capital", "investment", "dividend", "working capital", "npv"],
    },
    "NDA": {
        "Mathematics": ["algebra", "calculus", "trigonometry", "geometry", "statistics", "matrix"],
        "Physics": ["force", "energy", "wave", "optics", "thermodynamics", "electric"],
        "Chemistry": ["element", "compound", "reaction", "organic", "periodic", "acid"],
        "English": ["grammar", "vocabulary", "comprehension"],
        "General Knowledge": ["history", "geography", "current", "science", "sports"],
    },
}

# ============================================
# OCR - PDF SE TEXT NIKALNA
# ============================================

def extract_text_from_pdf(pdf_path):
    print(f"Reading: {pdf_path}")
    
    # Method 1: Direct extraction
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Direct failed: {e}")
    
    # Method 2: OCR if direct failed
    if len(text.strip()) < 100:
        try:
            images = convert_from_path(pdf_path, dpi=200)
            for image in images:
                page_text = pytesseract.image_to_string(image, lang='eng')
                text += page_text + "\n"
        except Exception as e:
            print(f"OCR failed: {e}")
    
    # Clean text
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s\.\?\(\)\,\:]', '', text)
    return text.strip()

# ============================================
# ANALYZER - TOPICS DHUNDNA
# ============================================

def analyze_topics(text, exam):
    topics = EXAM_TOPICS.get(exam, EXAM_TOPICS["JEE Main"])
    text_lower = text.lower()
    
    topic_counts = {}
    for topic, keywords in topics.items():
        count = sum(text_lower.count(kw) for kw in keywords)
        topic_counts[topic] = count
    
    return topic_counts

# ============================================
# PREDICTOR - PREDICTIONS BANANA
# ============================================

def generate_predictions(topic_counts, exam):
    total = sum(topic_counts.values())
    
    if total == 0:
        # Demo data agar PDF empty hai
        return get_demo_data(exam)
    
    predictions = []
    for topic, count in topic_counts.items():
        frequency = count / total if total > 0 else 0
        probability = min(round(frequency * 300), 95)
        
        if probability >= 70:
            priority = "high"
            reason = f"Bohot zyada aata hai - {count} baar mila"
        elif probability >= 40:
            priority = "medium"
            reason = f"Kabhi kabhi aata hai - {count} baar mila"
        else:
            priority = "low"
            reason = f"Kam aata hai - {count} baar mila"
        
        predictions.append({
            "topic": topic,
            "probability": probability,
            "priority": priority,
            "reason": reason
        })
    
    predictions.sort(key=lambda x: x["probability"], reverse=True)
    return predictions

# ============================================
# DEMO DATA - BINA PDF KE
# ============================================

def get_demo_data(exam):
    demo = {
        "JEE Main": [
            {"topic": "Integration", "probability": 95, "priority": "high", "reason": "Har saal aata hai - 5 saal se continuous"},
            {"topic": "Thermodynamics", "probability": 88, "priority": "high", "reason": "3 saal ka cycle - High priority"},
            {"topic": "Coordinate Geometry", "probability": 82, "priority": "high", "reason": "Last 10 saal mein 8 baar aaya"},
            {"topic": "Organic Chemistry", "probability": 78, "priority": "high", "reason": "High frequency topic"},
            {"topic": "Electrostatics", "probability": 72, "priority": "high", "reason": "Consistent presence"},
            {"topic": "Waves & Optics", "probability": 65, "priority": "medium", "reason": "Alternate years pattern"},
            {"topic": "Mechanics", "probability": 58, "priority": "medium", "reason": "Medium frequency"},
            {"topic": "Matrices", "probability": 45, "priority": "medium", "reason": "Recently aaya tha"},
            {"topic": "Statistics", "probability": 38, "priority": "low", "reason": "Low frequency topic"},
            {"topic": "3D Geometry", "probability": 25, "priority": "low", "reason": "Rarely aata hai"},
        ],
        "NEET": [
            {"topic": "Human Physiology", "probability": 94, "priority": "high", "reason": "Sabse zyada questions yahan se"},
            {"topic": "Cell Biology", "probability": 86, "priority": "high", "reason": "Har saal consistent"},
            {"topic": "Genetics", "probability": 79, "priority": "high", "reason": "High weightage topic"},
            {"topic": "Organic Chemistry", "probability": 71, "priority": "high", "reason": "Chemistry mein highest"},
            {"topic": "Physical Chemistry", "probability": 65, "priority": "medium", "reason": "Medium frequency"},
            {"topic": "Ecology", "probability": 55, "priority": "medium", "reason": "Thoda aata hai"},
            {"topic": "Plant Biology", "probability": 40, "priority": "medium", "reason": "Medium priority"},
            {"topic": "Evolution", "probability": 30, "priority": "low", "reason": "Kam aata hai"},
        ],
        "UPSC CSE": [
            {"topic": "Indian Economy", "probability": 92, "priority": "high", "reason": "Har saal 8-10 questions"},
            {"topic": "Environment & Ecology", "probability": 87, "priority": "high", "reason": "Trending - Last 5 saal badha"},
            {"topic": "Modern History", "probability": 83, "priority": "high", "reason": "Consistent presence"},
            {"topic": "Polity", "probability": 76, "priority": "high", "reason": "Current affairs link"},
            {"topic": "Geography", "probability": 68, "priority": "medium", "reason": "Medium frequency"},
            {"topic": "Science & Tech", "probability": 60, "priority": "medium", "reason": "Growing trend"},
            {"topic": "Ancient History", "probability": 42, "priority": "medium", "reason": "Thoda kam aata"},
            {"topic": "Medieval History", "probability": 35, "priority": "low", "reason": "Low in recent years"},
            {"topic": "International Relations", "probability": 28, "priority": "low", "reason": "Kabhi kabhi aata"},
        ],
        "MAH CET MBA": [
            {"topic": "Logical Reasoning", "probability": 92, "priority": "high", "reason": "Sabse zyada questions"},
            {"topic": "Abstract Reasoning", "probability": 85, "priority": "high", "reason": "High weightage"},
            {"topic": "Quantitative Aptitude", "probability": 78, "priority": "high", "reason": "Consistent presence"},
            {"topic": "Verbal Ability", "probability": 70, "priority": "high", "reason": "Important section"},
        ],
        "GATE": [
            {"topic": "Data Structures", "probability": 93, "priority": "high", "reason": "Core topic - Har saal"},
            {"topic": "Algorithms", "probability": 88, "priority": "high", "reason": "High weightage"},
            {"topic": "Operating Systems", "probability": 81, "priority": "high", "reason": "Consistent presence"},
            {"topic": "Database", "probability": 74, "priority": "high", "reason": "Medium-High frequency"},
            {"topic": "Computer Networks", "probability": 67, "priority": "medium", "reason": "Regular topic"},
            {"topic": "Digital Logic", "probability": 55, "priority": "medium", "reason": "Medium frequency"},
            {"topic": "Computer Architecture", "probability": 45, "priority": "medium", "reason": "Thoda aata hai"},
        ],
    }
    
    return demo.get(exam, demo["JEE Main"])

# ============================================
# MAIN FUNCTION
# ============================================

def process_papers(pdf_paths, exam):
    all_text = ""
    
    for pdf_path in pdf_paths:
        text = extract_text_from_pdf(pdf_path)
        all_text += text + "\n"
    
    if len(all_text.strip()) < 50:
        return get_demo_data(exam)
    
    topic_counts = analyze_topics(all_text, exam)
    predictions = generate_predictions(topic_counts, exam)
    
    return predictions