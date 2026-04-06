# ============================================
# EXAM PREDICTOR - AI Analyzer (v2.0)
# Render Deployment Ready
# ============================================

import os
import re
import platform
import hashlib
import logging
from datetime import datetime
from collections import Counter

import pdfplumber
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import nltk
from nltk.corpus import stopwords

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
# TESSERACT SETUP
# ============================================

def setup_tesseract():
    system = platform.system()
    if system == 'Windows':
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                logger.info(f"Tesseract found: {path}")
                return True
        logger.warning("Tesseract not found - OCR disabled")
        return False
    else:
        # Linux/Mac - Render pe
        pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
        return True

TESSERACT_AVAILABLE = setup_tesseract()

# ============================================
# NLTK SETUP
# ============================================

def setup_nltk():
    packages = ['punkt', 'stopwords', 'punkt_tab']
    for package in packages:
        try:
            if package == 'stopwords':
                nltk.data.find('corpora/stopwords')
            else:
                nltk.data.find(f'tokenizers/{package}')
        except LookupError:
            try:
                nltk.download(package, quiet=True)
                logger.info(f"NLTK {package} downloaded")
            except Exception as e:
                logger.warning(
                    f"NLTK {package} failed: {e}"
                )

setup_nltk()

# ============================================
# STOP WORDS
# ============================================

try:
    STOP_WORDS = set(stopwords.words('english'))
except Exception:
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but',
        'in', 'on', 'at', 'to', 'for', 'of',
        'with', 'by', 'is', 'are', 'was', 'were'
    }

# ============================================
# EXAM TOPICS DATABASE
# ============================================

EXAM_TOPICS = {
    "JEE Main": {
        "Integration": [
            "integral", "integrate", "antiderivative",
            "definite", "indefinite", "area under",
            "integration by parts", "substitution",
            "partial fraction"
        ],
        "Differentiation": [
            "derivative", "differentiate", "dy/dx",
            "rate of change", "tangent", "normal",
            "maxima", "minima", "rolle",
            "mean value theorem", "chain rule"
        ],
        "Thermodynamics": [
            "heat", "temperature", "entropy", "enthalpy",
            "thermodynamic", "carnot", "adiabatic",
            "isothermal", "isobaric", "isochoric",
            "internal energy", "specific heat"
        ],
        "Coordinate Geometry": [
            "circle", "parabola", "ellipse", "hyperbola",
            "coordinate", "locus", "straight line",
            "slope", "chord", "conic section"
        ],
        "Organic Chemistry": [
            "organic", "carbon", "hydrocarbon", "alkane",
            "alkene", "alkyne", "benzene", "reaction",
            "isomer", "functional group", "iupac",
            "polymer", "alcohol", "aldehyde", "ketone"
        ],
        "Waves & Optics": [
            "wave", "optics", "light", "reflection",
            "refraction", "lens", "mirror", "interference",
            "diffraction", "wavelength", "frequency",
            "amplitude", "doppler", "sound"
        ],
        "Matrices": [
            "matrix", "matrices", "determinant",
            "eigenvalue", "inverse", "transpose",
            "adjoint", "rank", "singular", "cofactor"
        ],
        "Statistics & Probability": [
            "mean", "median", "mode", "standard deviation",
            "probability", "variance", "binomial", "bayes",
            "permutation", "combination", "distribution"
        ],
        "Electrostatics": [
            "electric", "charge", "coulomb", "potential",
            "capacitor", "field", "gauss", "dipole",
            "flux", "dielectric", "conductor"
        ],
        "Mechanics": [
            "force", "momentum", "energy", "newton",
            "friction", "acceleration", "velocity",
            "projectile", "circular motion", "gravitation",
            "kepler", "escape velocity", "satellite"
        ],
        "3D Geometry": [
            "three dimension", "3d", "plane",
            "direction cosine", "vector", "cross product",
            "dot product", "angle between"
        ],
        "Limits & Continuity": [
            "limit", "continuity", "discontinuity",
            "left hand limit", "right hand limit",
            "l'hopital"
        ],
        "Complex Numbers": [
            "complex", "imaginary", "real part",
            "argument", "modulus", "conjugate",
            "polar form", "de moivre"
        ],
    },

    "JEE Advanced": {
        "Integration": [
            "integral", "integrate", "definite",
            "indefinite", "area", "volume",
            "reduction formula", "leibniz"
        ],
        "Mechanics": [
            "force", "momentum", "energy", "collision",
            "rotation", "torque", "moment of inertia",
            "angular momentum", "rigid body"
        ],
        "Electrochemistry": [
            "electrode", "cell", "electrolysis",
            "oxidation", "reduction", "redox", "nernst",
            "faraday", "galvanic", "electrode potential"
        ],
        "Organic Chemistry": [
            "organic", "reaction mechanism", "named reaction",
            "synthesis", "rearrangement", "stereochemistry",
            "chirality", "enantiomer", "nucleophilic"
        ],
        "Waves & Sound": [
            "wave", "superposition", "interference",
            "standing wave", "doppler", "resonance",
            "beats", "stationary wave"
        ],
        "Modern Physics": [
            "photoelectric", "quantum", "nuclear",
            "radioactive", "atom", "bohr", "de broglie",
            "uncertainty", "fission", "fusion", "half life"
        ],
        "Thermodynamics": [
            "entropy", "gibbs", "helmholtz",
            "thermodynamic equilibrium", "reversible",
            "irreversible", "heat engine"
        ],
        "Differential Equations": [
            "differential equation", "order", "degree",
            "homogeneous", "linear", "bernoulli"
        ],
    },

    "NEET": {
        "Human Physiology": [
            "heart", "blood", "digestion", "respiration",
            "nervous", "hormone", "kidney", "liver",
            "lung", "neuron", "synapse", "reflex",
            "cardiac output", "breathing", "excretion"
        ],
        "Cell Biology": [
            "cell", "membrane", "nucleus", "mitochondria",
            "chromosome", "dna", "rna", "ribosome",
            "golgi", "endoplasmic reticulum", "lysosome",
            "cell division", "meiosis", "mitosis"
        ],
        "Genetics": [
            "gene", "genetics", "heredity", "mutation",
            "allele", "mendel", "dominant", "recessive",
            "genotype", "phenotype", "linkage",
            "crossing over", "sex determination"
        ],
        "Organic Chemistry": [
            "organic", "carbon", "reaction", "compound",
            "functional group", "biomolecule", "carbohydrate",
            "protein", "lipid", "nucleic acid", "enzyme"
        ],
        "Physical Chemistry": [
            "mole", "concentration", "solution",
            "equilibrium", "ph", "acid", "base", "buffer",
            "titration", "colligative"
        ],
        "Plant Biology": [
            "plant", "photosynthesis", "transpiration",
            "chlorophyll", "root", "xylem", "phloem",
            "stomata", "seed", "flower", "pollination"
        ],
        "Ecology": [
            "ecosystem", "food chain", "biodiversity",
            "habitat", "population", "community",
            "succession", "biome", "nutrient cycle",
            "carbon cycle", "nitrogen cycle"
        ],
        "Evolution": [
            "evolution", "natural selection", "darwin",
            "fossil", "adaptation", "speciation",
            "mutation", "lamarck", "origin of life"
        ],
        "Animal Kingdom": [
            "classification", "phylum", "vertebrate",
            "invertebrate", "mammal", "reptile",
            "amphibian", "coelom", "symmetry"
        ],
        "Biotechnology": [
            "biotechnology", "recombinant dna", "pcr",
            "gel electrophoresis", "restriction enzyme",
            "cloning", "gmo", "transgenic", "bioreactor"
        ],
    },

    "UPSC CSE": {
        "Indian Economy": [
            "economy", "gdp", "inflation", "fiscal",
            "monetary", "budget", "rbi", "tax", "subsidy",
            "poverty", "unemployment", "growth rate",
            "trade deficit", "fdi", "fii"
        ],
        "Environment & Ecology": [
            "environment", "ecology", "climate",
            "biodiversity", "pollution", "carbon",
            "greenhouse", "paris agreement", "cop",
            "wetland", "tiger reserve", "national park",
            "ramsar", "species"
        ],
        "Modern History": [
            "british", "independence", "gandhi", "freedom",
            "colonial", "revolt", "congress", "partition",
            "non cooperation", "civil disobedience",
            "quit india", "swadeshi"
        ],
        "Polity": [
            "constitution", "amendment", "article",
            "parliament", "fundamental", "directive",
            "dpsp", "preamble", "governor", "president",
            "supreme court", "high court",
            "election commission"
        ],
        "Geography": [
            "climate", "monsoon", "rainfall", "geography",
            "weather", "river", "soil", "agriculture",
            "mineral", "mountain", "plateau", "coast",
            "ocean current", "tectonic"
        ],
        "Ancient History": [
            "ancient", "maurya", "gupta", "indus", "vedic",
            "harappa", "ashoka", "chandragupta",
            "buddhism", "jainism", "sangam"
        ],
        "Medieval History": [
            "mughal", "delhi sultanate", "medieval",
            "akbar", "aurangzeb", "vijayanagara",
            "maratha", "bhakti", "sufi"
        ],
        "Science & Tech": [
            "technology", "space", "isro", "nuclear",
            "satellite", "biotechnology",
            "artificial intelligence", "5g", "quantum",
            "mission", "launch", "rocket", "defense"
        ],
        "International Relations": [
            "foreign policy", "treaty", "bilateral",
            "united nations", "summit", "g20", "brics",
            "sco", "asean", "nato", "trade agreement"
        ],
        "Social Issues": [
            "poverty", "education", "health", "gender",
            "caste", "tribal", "minority", "scheme",
            "welfare", "social justice", "reservation"
        ],
    },

    "GATE": {
        "Data Structures": [
            "array", "linked list", "tree", "graph",
            "stack", "queue", "heap", "hash",
            "binary search tree", "avl", "trie"
        ],
        "Algorithms": [
            "sorting", "searching", "complexity",
            "dynamic programming", "greedy",
            "divide and conquer", "backtracking",
            "big o", "time complexity", "np complete"
        ],
        "Operating Systems": [
            "process", "thread", "scheduling", "memory",
            "deadlock", "semaphore", "mutex", "paging",
            "segmentation", "virtual memory", "file system"
        ],
        "Database": [
            "sql", "query", "normalization", "transaction",
            "acid", "join", "index", "er diagram",
            "relational algebra", "functional dependency",
            "bcnf", "concurrency"
        ],
        "Computer Networks": [
            "network", "protocol", "tcp", "ip", "routing",
            "osi", "http", "dns", "dhcp", "subnet",
            "congestion", "sliding window", "mac"
        ],
        "Digital Logic": [
            "boolean", "logic gate", "flip flop", "circuit",
            "binary", "multiplexer", "decoder", "adder",
            "karnaugh", "sequential", "combinational"
        ],
        "Theory of Computation": [
            "automata", "turing machine", "grammar",
            "language", "regular expression",
            "context free", "pushdown", "decidable",
            "halting problem", "pumping lemma"
        ],
        "Compiler Design": [
            "compiler", "lexical", "parsing", "syntax",
            "semantic", "code generation", "optimization",
            "symbol table", "grammar ambiguous", "ll", "lr"
        ],
    },

    "CAT": {
        "Quantitative Aptitude": [
            "number", "algebra", "geometry", "arithmetic",
            "percentage", "profit loss", "time work",
            "speed distance", "ratio proportion",
            "sequence series", "logarithm"
        ],
        "Verbal Ability": [
            "grammar", "vocabulary", "reading",
            "comprehension", "sentence", "parajumbles",
            "fill in the blank", "idiom", "synonym",
            "antonym", "analogy", "critical reasoning"
        ],
        "Logical Reasoning": [
            "puzzle", "arrangement", "syllogism", "coding",
            "series", "blood relation", "direction",
            "clocks", "calendars", "seating arrangement"
        ],
        "Data Interpretation": [
            "graph", "chart", "table", "pie", "bar",
            "data", "line graph", "caselets",
            "venn diagram", "mixed graph"
        ],
    },

    "MAH CET MBA": {
        "Logical Reasoning": [
            "puzzle", "arrangement", "blood relation",
            "direction", "coding", "input output",
            "statement conclusion", "course of action",
            "critical reasoning"
        ],
        "Abstract Reasoning": [
            "pattern", "series", "figure", "analogy",
            "odd one out", "matrix reasoning",
            "mirror image", "paper folding"
        ],
        "Quantitative Aptitude": [
            "number", "algebra", "percentage", "profit",
            "ratio", "time", "speed", "work", "interest",
            "geometry", "mensuration"
        ],
        "Verbal Ability": [
            "grammar", "vocabulary", "comprehension",
            "fill in the blank", "error correction",
            "sentence improvement", "reading passage"
        ],
    },

    "MHT CET": {
        "Physics": [
            "force", "energy", "wave", "electric",
            "magnetic", "optics", "thermodynamics",
            "circular motion", "gravitation", "rotational",
            "semiconductor", "communication"
        ],
        "Chemistry": [
            "organic", "inorganic", "physical", "reaction",
            "element", "compound", "periodic table",
            "chemical bonding", "equilibrium",
            "electrochemistry", "solid state"
        ],
        "Mathematics": [
            "algebra", "calculus", "trigonometry",
            "geometry", "statistics", "vector",
            "integration", "differentiation", "matrix",
            "probability", "linear programming"
        ],
        "Biology": [
            "cell", "genetics", "ecology", "physiology",
            "evolution", "plant", "animal", "reproduction",
            "biotechnology", "human health"
        ],
    },

    "MPSC": {
        "Maharashtra History": [
            "maratha", "shivaji", "maharashtra", "peshwa",
            "satara", "kolhapur", "nagpur", "sambhaji"
        ],
        "Maharashtra Geography": [
            "western ghats", "konkan", "vidarbha",
            "marathwada", "river", "sahyadri", "godavari",
            "krishna", "nashik", "pune", "mumbai"
        ],
        "Indian Polity": [
            "constitution", "parliament", "state",
            "governor", "assembly", "article", "schedule",
            "fundamental right", "directive", "election"
        ],
        "Economy": [
            "agriculture", "industry", "gdp", "poverty",
            "employment", "scheme", "budget", "tax",
            "inflation", "cooperative", "irrigation"
        ],
        "Current Affairs": [
            "government", "scheme", "award", "sports",
            "international", "maharashtra government",
            "yojana", "mission", "development"
        ],
    },

    "SSC CGL": {
        "Quantitative Aptitude": [
            "number", "percentage", "ratio", "profit",
            "interest", "time", "geometry", "trigonometry",
            "algebra", "mensuration", "speed distance"
        ],
        "English": [
            "grammar", "vocabulary", "comprehension",
            "error", "fill", "synonym", "antonym",
            "one word", "idiom", "phrase"
        ],
        "General Awareness": [
            "history", "geography", "science", "current",
            "economy", "polity", "sports", "award",
            "book author", "static gk"
        ],
        "Reasoning": [
            "analogy", "series", "coding", "puzzle",
            "syllogism", "matrix", "direction",
            "blood relation", "ranking", "classification"
        ],
    },

    "IBPS PO": {
        "Quantitative Aptitude": [
            "number", "percentage", "ratio", "profit",
            "interest", "data", "series", "quadratic",
            "approximation", "di", "time work"
        ],
        "English": [
            "grammar", "vocabulary", "comprehension",
            "error", "cloze", "para jumble",
            "fill blanks", "reading passage"
        ],
        "Reasoning": [
            "puzzle", "arrangement", "syllogism", "coding",
            "blood relation", "direction", "inequality",
            "input output", "floor based", "box based"
        ],
        "Banking Awareness": [
            "rbi", "bank", "interest", "credit", "monetary",
            "finance", "repo rate", "crr", "slr", "nbfc",
            "basel", "npa", "financial inclusion", "upi"
        ],
        "Computer": [
            "hardware", "software", "internet", "ms office",
            "network", "database", "keyboard shortcut",
            "memory", "output device", "operating system"
        ],
    },

    "CLAT": {
        "Legal Reasoning": [
            "law", "legal", "act", "court", "judgment",
            "constitution", "rights", "ipc", "crpc",
            "tort", "contract", "evidence",
            "fundamental right"
        ],
        "English": [
            "grammar", "vocabulary", "comprehension",
            "passage", "inference", "author tone"
        ],
        "Logical Reasoning": [
            "argument", "assumption", "conclusion",
            "inference", "statement", "strengthens weakens",
            "critical reasoning", "paragraph inference"
        ],
        "General Knowledge": [
            "history", "current", "geography", "science",
            "economics", "legal current affairs",
            "supreme court judgment", "new act", "amendment"
        ],
        "Quantitative": [
            "number", "percentage", "ratio", "data",
            "graph", "statistics", "table interpretation"
        ],
    },

    "CA Final": {
        "Financial Reporting": [
            "accounting", "financial statement",
            "balance sheet", "profit", "ifrs", "ind as",
            "consolidation", "segment", "lease",
            "revenue recognition", "fair value"
        ],
        "Taxation": [
            "tax", "income tax", "gst", "deduction",
            "exemption", "tds", "assessment", "appeal",
            "penalty", "advance tax", "capital gain"
        ],
        "Audit": [
            "audit", "auditor", "vouching", "verification",
            "internal control", "risk assessment",
            "audit evidence", "audit report", "caro", "sa"
        ],
        "Strategic Management": [
            "strategy", "management", "corporate",
            "governance", "risk", "swot",
            "balanced scorecard", "merger acquisition"
        ],
        "Financial Management": [
            "capital", "investment", "dividend",
            "working capital", "npv", "irr", "wacc",
            "leverage", "portfolio", "derivatives"
        ],
    },

    "NDA": {
        "Mathematics": [
            "algebra", "calculus", "trigonometry",
            "geometry", "statistics", "matrix", "vector",
            "complex number", "probability"
        ],
        "Physics": [
            "force", "energy", "wave", "optics",
            "thermodynamics", "electric", "magnetic",
            "nuclear", "semiconductor", "motion"
        ],
        "Chemistry": [
            "element", "compound", "reaction", "organic",
            "periodic", "acid", "base", "salt",
            "metal", "nonmetal", "bonding"
        ],
        "English": [
            "grammar", "vocabulary", "comprehension",
            "spotting error", "fill blanks"
        ],
        "General Knowledge": [
            "history", "geography", "current", "science",
            "sports", "defence", "indian army", "polity"
        ],
    },
}

# ============================================
# DIFFICULTY MARKERS
# ============================================

DIFFICULTY_MARKERS = {
    'easy': [
        'find', 'calculate', 'state', 'define', 'write',
        'name', 'list', 'identify', 'what is'
    ],
    'medium': [
        'derive', 'prove', 'explain', 'compare', 'analyze',
        'describe', 'discuss', 'distinguish'
    ],
    'hard': [
        'evaluate', 'critically', 'justify', 'complex',
        'hence prove', 'show that', 'deduce', 'establish'
    ]
}

# ============================================
# TEXT EXTRACTION
# ============================================

def extract_text_from_pdf(pdf_path):
    """PDF se text nikalna"""
    logger.info(f"Reading: {pdf_path}")
    text = ""

    # Method 1: Direct extraction
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                except Exception as e:
                    logger.warning(
                        f"Page {page_num + 1} failed: {e}"
                    )
    except Exception as e:
        logger.error(f"Direct extraction failed: {e}")

    # Method 2: OCR if needed
    if len(text.strip()) < 100 and TESSERACT_AVAILABLE:
        logger.info("Trying OCR...")
        try:
            images = convert_from_path(pdf_path, dpi=150)
            for i, image in enumerate(images):
                try:
                    image = image.convert('L')
                    page_text = pytesseract.image_to_string(
                        image, lang='eng',
                        config='--psm 6 --oem 3'
                    )
                    text += page_text + "\n"
                except Exception as e:
                    logger.warning(f"OCR page {i+1}: {e}")
        except Exception as e:
            logger.error(f"OCR failed: {e}")

    text = clean_text(text)
    logger.info(f"Extracted: {len(text)} chars")
    return text


def clean_text(text):
    """Text clean karna"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(
        r'[^\w\s\.\?\(\)\,\:\+\-\=\/\%\&\@\#\!\^\*]',
        ' ', text
    )
    words = text.split()
    words = [w for w in words if len(w) > 1 or w.isdigit()]
    return ' '.join(words).strip()

# ============================================
# TOPIC ANALYZER
# ============================================

def analyze_topics(text, exam):
    """Topics dhundna"""
    topics = EXAM_TOPICS.get(exam, EXAM_TOPICS["JEE Main"])
    text_lower = text.lower()
    topic_counts = {}

    for topic, keywords in topics.items():
        count = 0
        keyword_hits = {}

        for kw in keywords:
            kw_lower = kw.lower()
            exact_count = text_lower.count(kw_lower)
            if exact_count > 0:
                keyword_hits[kw] = exact_count
                word_count = len(kw.split())
                count += exact_count * word_count

        topic_counts[topic] = {
            'total_count': count,
            'keyword_hits': keyword_hits,
            'unique_keywords': len(keyword_hits)
        }

    return topic_counts


def analyze_difficulty(text):
    """Difficulty analyze karna"""
    text_lower = text.lower()
    difficulty_score = {'easy': 0, 'medium': 0, 'hard': 0}

    for level, markers in DIFFICULTY_MARKERS.items():
        for marker in markers:
            difficulty_score[level] += \
                text_lower.count(marker)

    total = sum(difficulty_score.values())
    if total == 0:
        return {'easy': 33, 'medium': 34, 'hard': 33}

    return {
        level: round(count / total * 100)
        for level, count in difficulty_score.items()
    }


def identify_question_patterns(text):
    """Question types identify karna"""
    patterns = {
        'MCQ': r'[a-d]\)\s|\([a-d]\)\s|choose the',
        'Numerical': r'find the value|calculate|determine',
        'Proof': r'prove that|show that|derive',
        'Application': r'a body|a particle|a student',
        'Conceptual': r'explain|define|state|describe'
    }

    question_types = {}
    for qtype, pattern in patterns.items():
        matches = re.findall(pattern, text.lower())
        question_types[qtype] = len(matches)

    return question_types

# ============================================
# PREDICTION GENERATOR
# ============================================

def generate_predictions(topic_counts, exam, trends=None):
    """Smart predictions banana"""
    if not topic_counts:
        return get_demo_data(exam)

    total = sum(
        data['total_count']
        if isinstance(data, dict) else data
        for data in topic_counts.values()
    )

    if total == 0:
        logger.warning("No keywords found - demo data")
        return get_demo_data(exam)

    predictions = []

    for topic, data in topic_counts.items():
        if isinstance(data, dict):
            count = data['total_count']
            unique_kw = data.get('unique_keywords', 0)
            keyword_hits = data.get('keyword_hits', {})
        else:
            count = data
            unique_kw = 0
            keyword_hits = {}

        frequency = count / total if total > 0 else 0
        base_prob = frequency * 250
        uniqueness_bonus = min(unique_kw * 2, 20)
        probability = min(
            round(base_prob + uniqueness_bonus + 5), 95
        )
        probability = max(probability, 5)

        if probability >= 70:
            priority = "high"
            reason = (
                f"Bahut frequently aaya - "
                f"{count} baar, {unique_kw} unique concepts"
            )
        elif probability >= 40:
            priority = "medium"
            reason = (
                f"Medium frequency - "
                f"{count} baar mila"
            )
        else:
            priority = "low"
            reason = f"Kam aata hai - {count} baar mila"

        top_keywords = sorted(
            keyword_hits.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        predictions.append({
            "topic": topic,
            "probability": probability,
            "priority": priority,
            "reason": reason,
            "keyword_count": count,
            "unique_keywords": unique_kw,
            "top_keywords": [kw for kw, _ in top_keywords],
            "trend": "stable"
        })

    predictions.sort(
        key=lambda x: x["probability"],
        reverse=True
    )
    return predictions

# ============================================
# SYLLABUS COVERAGE
# ============================================

OFFICIAL_SYLLABUS = {
    "JEE Main": {
        "Mathematics": [
            "Sets Relations Functions", "Complex Numbers",
            "Matrices", "Determinants", "Permutations",
            "Binomial Theorem", "Sequences Series",
            "Limits Continuity", "Differentiation",
            "Integration", "Coordinate Geometry",
            "3D Geometry", "Vectors", "Statistics"
        ],
        "Physics": [
            "Mechanics", "Thermodynamics", "Waves Optics",
            "Electrostatics", "Current Electricity",
            "Magnetism", "Modern Physics", "Semiconductors"
        ],
        "Chemistry": [
            "Organic Chemistry", "Inorganic Chemistry",
            "Physical Chemistry", "Electrochemistry"
        ]
    }
}


def track_syllabus_coverage(predictions, exam):
    """Syllabus coverage check karna"""
    syllabus = OFFICIAL_SYLLABUS.get(exam, {})
    if not syllabus:
        return {}

    covered_topics = [p['topic'] for p in predictions]
    coverage = {}

    for subject, topics in syllabus.items():
        covered = [
            t for t in topics
            if any(
                t.lower() in ct.lower() or
                ct.lower() in t.lower()
                for ct in covered_topics
            )
        ]
        missing = [t for t in topics if t not in covered]

        coverage[subject] = {
            'total': len(topics),
            'covered': len(covered),
            'percentage': round(
                len(covered) / len(topics) * 100
            ) if topics else 0,
            'missing_topics': missing,
        }

    return coverage

# ============================================
# TIMETABLE GENERATOR
# ============================================

def generate_timetable(predictions, days_left, daily_hours):
    """Personalized timetable banana"""
    if not predictions or days_left <= 0:
        return {}

    total_hours = days_left * daily_hours

    high_topics = [
        p for p in predictions if p['priority'] == 'high'
    ]
    medium_topics = [
        p for p in predictions if p['priority'] == 'medium'
    ]
    low_topics = [
        p for p in predictions if p['priority'] == 'low'
    ]

    high_hours = total_hours * 0.60
    medium_hours = total_hours * 0.30
    low_hours = total_hours * 0.10

    timetable = {
        'summary': {
            'total_days': days_left,
            'daily_hours': daily_hours,
            'total_hours': round(total_hours, 1),
            'high_priority_hours': round(high_hours, 1),
            'medium_priority_hours': round(medium_hours, 1),
            'low_priority_hours': round(low_hours, 1),
        },
        'schedule': []
    }

    for topic_list, hours_pool, priority in [
        (high_topics, high_hours, 'high'),
        (medium_topics, medium_hours, 'medium'),
        (low_topics, low_hours, 'low')
    ]:
        if not topic_list:
            continue

        hours_per_topic = hours_pool / len(topic_list)

        for topic in topic_list:
            sessions = max(1, round(hours_per_topic / 1.5))
            timetable['schedule'].append({
                'topic': topic['topic'],
                'priority': priority,
                'total_hours': round(hours_per_topic, 1),
                'sessions': sessions,
                'hours_per_session': round(
                    hours_per_topic / sessions, 1
                ),
                'probability': topic['probability']
            })

    return timetable

# ============================================
# DEMO DATA
# ============================================

def get_demo_data(exam):
    """Demo data for all exams"""

    demo_data = {
        "JEE Main": [
            {
                "topic": "Integration",
                "probability": 95,
                "priority": "high",
                "reason": "Har saal aata hai - 5 saal se continuous",
                "trend": "stable",
                "top_keywords": ["integral", "definite", "area"]
            },
            {
                "topic": "Thermodynamics",
                "probability": 88,
                "priority": "high",
                "reason": "3 saal ka pattern - High priority",
                "trend": "rising",
                "top_keywords": ["carnot", "entropy", "heat"]
            },
            {
                "topic": "Coordinate Geometry",
                "probability": 82,
                "priority": "high",
                "reason": "Last 10 saal mein 8 baar aaya",
                "trend": "stable",
                "top_keywords": ["parabola", "ellipse", "circle"]
            },
            {
                "topic": "Organic Chemistry",
                "probability": 78,
                "priority": "high",
                "reason": "High frequency topic",
                "trend": "rising",
                "top_keywords": ["reaction", "alkene", "benzene"]
            },
            {
                "topic": "Electrostatics",
                "probability": 72,
                "priority": "high",
                "reason": "Consistent presence",
                "trend": "stable",
                "top_keywords": ["charge", "capacitor", "field"]
            },
            {
                "topic": "Waves & Optics",
                "probability": 65,
                "priority": "medium",
                "reason": "Alternate years pattern",
                "trend": "stable",
                "top_keywords": ["wave", "lens", "refraction"]
            },
            {
                "topic": "Mechanics",
                "probability": 58,
                "priority": "medium",
                "reason": "Medium frequency",
                "trend": "falling",
                "top_keywords": ["force", "momentum", "energy"]
            },
            {
                "topic": "Matrices",
                "probability": 45,
                "priority": "medium",
                "reason": "Recently aaya tha",
                "trend": "stable",
                "top_keywords": ["determinant", "inverse", "transpose"]
            },
            {
                "topic": "Statistics & Probability",
                "probability": 38,
                "priority": "low",
                "reason": "Low frequency topic",
                "trend": "stable",
                "top_keywords": ["mean", "probability", "variance"]
            },
            {
                "topic": "3D Geometry",
                "probability": 25,
                "priority": "low",
                "reason": "Rarely aata hai",
                "trend": "falling",
                "top_keywords": ["plane", "vector", "direction"]
            },
        ],

        "JEE Advanced": [
            {
                "topic": "Integration",
                "probability": 94,
                "priority": "high",
                "reason": "Core topic - Every year",
                "trend": "stable",
                "top_keywords": ["definite", "area", "volume"]
            },
            {
                "topic": "Mechanics",
                "probability": 90,
                "priority": "high",
                "reason": "Highest weightage section",
                "trend": "stable",
                "top_keywords": ["rotation", "torque", "collision"]
            },
            {
                "topic": "Organic Chemistry",
                "probability": 85,
                "priority": "high",
                "reason": "Reaction mechanisms - Always present",
                "trend": "rising",
                "top_keywords": ["mechanism", "named reaction", "synthesis"]
            },
            {
                "topic": "Modern Physics",
                "probability": 78,
                "priority": "high",
                "reason": "Consistent topic",
                "trend": "stable",
                "top_keywords": ["quantum", "nuclear", "photoelectric"]
            },
            {
                "topic": "Electrochemistry",
                "probability": 72,
                "priority": "high",
                "reason": "Rising trend",
                "trend": "rising",
                "top_keywords": ["electrode", "nernst", "faraday"]
            },
            {
                "topic": "Waves & Sound",
                "probability": 65,
                "priority": "medium",
                "reason": "Medium frequency",
                "trend": "stable",
                "top_keywords": ["interference", "superposition", "doppler"]
            },
            {
                "topic": "Thermodynamics",
                "probability": 55,
                "priority": "medium",
                "reason": "Alternate years",
                "trend": "stable",
                "top_keywords": ["entropy", "gibbs", "reversible"]
            },
            {
                "topic": "Differential Equations",
                "probability": 30,
                "priority": "low",
                "reason": "Rarely direct questions",
                "trend": "falling",
                "top_keywords": ["order", "degree", "homogeneous"]
            },
        ],

        "NEET": [
            {
                "topic": "Human Physiology",
                "probability": 94,
                "priority": "high",
                "reason": "Sabse zyada questions - 20+",
                "trend": "stable",
                "top_keywords": ["heart", "nervous", "kidney"]
            },
            {
                "topic": "Cell Biology",
                "probability": 86,
                "priority": "high",
                "reason": "Har saal consistent",
                "trend": "stable",
                "top_keywords": ["mitosis", "membrane", "organelle"]
            },
            {
                "topic": "Genetics",
                "probability": 79,
                "priority": "high",
                "reason": "High weightage - Mendel + Molecular",
                "trend": "rising",
                "top_keywords": ["mendel", "dna", "mutation"]
            },
            {
                "topic": "Organic Chemistry",
                "probability": 71,
                "priority": "high",
                "reason": "Chemistry mein highest",
                "trend": "stable",
                "top_keywords": ["biomolecule", "reaction", "enzyme"]
            },
            {
                "topic": "Plant Biology",
                "probability": 68,
                "priority": "medium",
                "reason": "Regular topic",
                "trend": "stable",
                "top_keywords": ["photosynthesis", "xylem", "stomata"]
            },
            {
                "topic": "Ecology",
                "probability": 55,
                "priority": "medium",
                "reason": "Trending up",
                "trend": "rising",
                "top_keywords": ["ecosystem", "food chain", "biodiversity"]
            },
            {
                "topic": "Biotechnology",
                "probability": 48,
                "priority": "medium",
                "reason": "Growing importance",
                "trend": "rising",
                "top_keywords": ["pcr", "recombinant dna", "cloning"]
            },
            {
                "topic": "Evolution",
                "probability": 28,
                "priority": "low",
                "reason": "Kam aata hai",
                "trend": "falling",
                "top_keywords": ["natural selection", "darwin", "fossil"]
            },
        ],

        "UPSC CSE": [
            {
                "topic": "Indian Economy",
                "probability": 92,
                "priority": "high",
                "reason": "Har saal 8-10 questions",
                "trend": "stable",
                "top_keywords": ["gdp", "rbi", "fiscal policy"]
            },
            {
                "topic": "Environment & Ecology",
                "probability": 87,
                "priority": "high",
                "reason": "Trending - Last 5 saal badha",
                "trend": "rising",
                "top_keywords": ["climate", "biodiversity", "paris"]
            },
            {
                "topic": "Polity",
                "probability": 83,
                "priority": "high",
                "reason": "Consistent - Constitutional questions",
                "trend": "stable",
                "top_keywords": ["constitution", "rights", "parliament"]
            },
            {
                "topic": "Modern History",
                "probability": 76,
                "priority": "high",
                "reason": "Freedom movement - Regular",
                "trend": "stable",
                "top_keywords": ["gandhi", "congress", "independence"]
            },
            {
                "topic": "Geography",
                "probability": 68,
                "priority": "medium",
                "reason": "Medium frequency",
                "trend": "stable",
                "top_keywords": ["monsoon", "river", "climate"]
            },
            {
                "topic": "Science & Tech",
                "probability": 65,
                "priority": "medium",
                "reason": "Rising - ISRO, AI, Space",
                "trend": "rising",
                "top_keywords": ["isro", "5g", "biotechnology"]
            },
            {
                "topic": "Ancient History",
                "probability": 42,
                "priority": "medium",
                "reason": "Thoda kam aata",
                "trend": "falling",
                "top_keywords": ["maurya", "gupta", "harappa"]
            },
            {
                "topic": "Medieval History",
                "probability": 35,
                "priority": "low",
                "reason": "Low in recent years",
                "trend": "falling",
                "top_keywords": ["mughal", "delhi sultanate", "akbar"]
            },
        ],

        "GATE": [
            {
                "topic": "Data Structures",
                "probability": 93,
                "priority": "high",
                "reason": "Core topic - Har saal highest",
                "trend": "stable",
                "top_keywords": ["tree", "graph", "hash table"]
            },
            {
                "topic": "Algorithms",
                "probability": 88,
                "priority": "high",
                "reason": "High weightage - 10-12 questions",
                "trend": "stable",
                "top_keywords": ["dynamic programming", "complexity", "sorting"]
            },
            {
                "topic": "Operating Systems",
                "probability": 84,
                "priority": "high",
                "reason": "Scheduling + Memory - Regular",
                "trend": "stable",
                "top_keywords": ["scheduling", "deadlock", "paging"]
            },
            {
                "topic": "Database",
                "probability": 79,
                "priority": "high",
                "reason": "SQL + Normalization - Regular",
                "trend": "stable",
                "top_keywords": ["sql", "normalization", "transaction"]
            },
            {
                "topic": "Computer Networks",
                "probability": 72,
                "priority": "high",
                "reason": "TCP/IP - Always present",
                "trend": "stable",
                "top_keywords": ["tcp", "routing", "protocol"]
            },
            {
                "topic": "Theory of Computation",
                "probability": 65,
                "priority": "medium",
                "reason": "Automata - Medium",
                "trend": "stable",
                "top_keywords": ["automata", "turing", "grammar"]
            },
            {
                "topic": "Digital Logic",
                "probability": 55,
                "priority": "medium",
                "reason": "Gates + Flip Flops",
                "trend": "falling",
                "top_keywords": ["boolean", "flip flop", "karnaugh"]
            },
            {
                "topic": "Compiler Design",
                "probability": 45,
                "priority": "medium",
                "reason": "Parsing - Sometimes",
                "trend": "stable",
                "top_keywords": ["lexical", "parsing", "grammar"]
            },
        ],

        "CAT": [
            {
                "topic": "Logical Reasoning",
                "probability": 94,
                "priority": "high",
                "reason": "LRDI section - Highest weightage",
                "trend": "stable",
                "top_keywords": ["puzzle", "arrangement", "seating"]
            },
            {
                "topic": "Data Interpretation",
                "probability": 90,
                "priority": "high",
                "reason": "LRDI combined - Must prepare",
                "trend": "rising",
                "top_keywords": ["graph", "table", "pie chart"]
            },
            {
                "topic": "Verbal Ability",
                "probability": 85,
                "priority": "high",
                "reason": "Reading Comprehension - Highest",
                "trend": "stable",
                "top_keywords": ["comprehension", "parajumbles", "grammar"]
            },
            {
                "topic": "Quantitative Aptitude",
                "probability": 80,
                "priority": "high",
                "reason": "Arithmetic + Algebra - Regular",
                "trend": "stable",
                "top_keywords": ["algebra", "geometry", "number system"]
            },
        ],

        "MAH CET MBA": [
            {
                "topic": "Logical Reasoning",
                "probability": 92,
                "priority": "high",
                "reason": "75 questions section",
                "trend": "stable",
                "top_keywords": ["puzzle", "arrangement", "blood relation"]
            },
            {
                "topic": "Abstract Reasoning",
                "probability": 85,
                "priority": "high",
                "reason": "High weightage - 25 questions",
                "trend": "stable",
                "top_keywords": ["pattern", "series", "analogy"]
            },
            {
                "topic": "Quantitative Aptitude",
                "probability": 78,
                "priority": "high",
                "reason": "Consistent presence",
                "trend": "stable",
                "top_keywords": ["percentage", "ratio", "algebra"]
            },
            {
                "topic": "Verbal Ability",
                "probability": 70,
                "priority": "high",
                "reason": "Reading + Grammar",
                "trend": "stable",
                "top_keywords": ["comprehension", "grammar", "vocabulary"]
            },
        ],

        "MHT CET": [
            {
                "topic": "Mathematics",
                "probability": 90,
                "priority": "high",
                "reason": "100 marks - Highest",
                "trend": "stable",
                "top_keywords": ["calculus", "algebra", "trigonometry"]
            },
            {
                "topic": "Physics",
                "probability": 88,
                "priority": "high",
                "reason": "50 marks section",
                "trend": "stable",
                "top_keywords": ["force", "electric", "optics"]
            },
            {
                "topic": "Chemistry",
                "probability": 85,
                "priority": "high",
                "reason": "50 marks - Organic heavy",
                "trend": "stable",
                "top_keywords": ["organic", "reaction", "equilibrium"]
            },
            {
                "topic": "Biology",
                "probability": 80,
                "priority": "high",
                "reason": "PCB students - 100 marks",
                "trend": "stable",
                "top_keywords": ["cell", "genetics", "physiology"]
            },
        ],

        "MPSC": [
            {
                "topic": "Maharashtra History",
                "probability": 88,
                "priority": "high",
                "reason": "Shivaji + Maratha - Har saal",
                "trend": "stable",
                "top_keywords": ["shivaji", "maratha", "peshwa"]
            },
            {
                "topic": "Maharashtra Geography",
                "probability": 82,
                "priority": "high",
                "reason": "Western Ghats + Rivers",
                "trend": "stable",
                "top_keywords": ["sahyadri", "konkan", "godavari"]
            },
            {
                "topic": "Indian Polity",
                "probability": 78,
                "priority": "high",
                "reason": "Constitution - Consistent",
                "trend": "stable",
                "top_keywords": ["constitution", "governor", "assembly"]
            },
            {
                "topic": "Current Affairs",
                "probability": 72,
                "priority": "high",
                "reason": "Maharashtra govt schemes",
                "trend": "rising",
                "top_keywords": ["yojana", "scheme", "government"]
            },
            {
                "topic": "Economy",
                "probability": 65,
                "priority": "medium",
                "reason": "Agriculture + Industry",
                "trend": "stable",
                "top_keywords": ["agriculture", "poverty", "budget"]
            },
        ],

        "SSC CGL": [
            {
                "topic": "Quantitative Aptitude",
                "probability": 90,
                "priority": "high",
                "reason": "50 questions - Highest weightage",
                "trend": "stable",
                "top_keywords": ["percentage", "geometry", "trigonometry"]
            },
            {
                "topic": "English",
                "probability": 85,
                "priority": "high",
                "reason": "50 questions - Grammar + Vocab",
                "trend": "stable",
                "top_keywords": ["grammar", "comprehension", "vocabulary"]
            },
            {
                "topic": "Reasoning",
                "probability": 82,
                "priority": "high",
                "reason": "50 questions - Must prepare",
                "trend": "stable",
                "top_keywords": ["analogy", "series", "coding"]
            },
            {
                "topic": "General Awareness",
                "probability": 78,
                "priority": "high",
                "reason": "50 questions - Static + Current",
                "trend": "rising",
                "top_keywords": ["history", "science", "current affairs"]
            },
        ],

        "IBPS PO": [
            {
                "topic": "Reasoning",
                "probability": 92,
                "priority": "high",
                "reason": "Puzzle heavy - Must solve fast",
                "trend": "stable",
                "top_keywords": ["puzzle", "floor", "box"]
            },
            {
                "topic": "Quantitative Aptitude",
                "probability": 88,
                "priority": "high",
                "reason": "DI + Arithmetic - High marks",
                "trend": "stable",
                "top_keywords": ["di", "quadratic", "series"]
            },
            {
                "topic": "English",
                "probability": 82,
                "priority": "high",
                "reason": "Reading Comprehension heavy",
                "trend": "stable",
                "top_keywords": ["comprehension", "cloze", "para jumble"]
            },
            {
                "topic": "Banking Awareness",
                "probability": 75,
                "priority": "high",
                "reason": "Bank specific - Must know",
                "trend": "rising",
                "top_keywords": ["rbi", "repo rate", "upi"]
            },
            {
                "topic": "Computer",
                "probability": 60,
                "priority": "medium",
                "reason": "Basic computer knowledge",
                "trend": "falling",
                "top_keywords": ["ms office", "internet", "hardware"]
            },
        ],

        "CLAT": [
            {
                "topic": "Legal Reasoning",
                "probability": 90,
                "priority": "high",
                "reason": "40 questions - Core section",
                "trend": "rising",
                "top_keywords": ["legal principle", "tort", "contract"]
            },
            {
                "topic": "Logical Reasoning",
                "probability": 85,
                "priority": "high",
                "reason": "28 questions - Critical reasoning",
                "trend": "stable",
                "top_keywords": ["argument", "assumption", "conclusion"]
            },
            {
                "topic": "English",
                "probability": 82,
                "priority": "high",
                "reason": "Comprehension based",
                "trend": "stable",
                "top_keywords": ["passage", "inference", "vocabulary"]
            },
            {
                "topic": "General Knowledge",
                "probability": 75,
                "priority": "high",
                "reason": "Legal GK + Current affairs",
                "trend": "rising",
                "top_keywords": ["supreme court", "amendment", "current"]
            },
            {
                "topic": "Quantitative",
                "probability": 45,
                "priority": "medium",
                "reason": "Only 13 questions",
                "trend": "stable",
                "top_keywords": ["percentage", "ratio", "data"]
            },
        ],

        "CA Final": [
            {
                "topic": "Financial Reporting",
                "probability": 92,
                "priority": "high",
                "reason": "Ind AS - Always present",
                "trend": "rising",
                "top_keywords": ["ind as", "ifrs", "consolidation"]
            },
            {
                "topic": "Taxation",
                "probability": 88,
                "priority": "high",
                "reason": "Income Tax + GST - Mandatory",
                "trend": "stable",
                "top_keywords": ["income tax", "gst", "tds"]
            },
            {
                "topic": "Audit",
                "probability": 82,
                "priority": "high",
                "reason": "SA standards - Regular",
                "trend": "stable",
                "top_keywords": ["auditor", "sa", "caro"]
            },
            {
                "topic": "Financial Management",
                "probability": 75,
                "priority": "high",
                "reason": "NPV + Capital structure",
                "trend": "stable",
                "top_keywords": ["npv", "wacc", "derivatives"]
            },
            {
                "topic": "Strategic Management",
                "probability": 60,
                "priority": "medium",
                "reason": "Theory based",
                "trend": "stable",
                "top_keywords": ["strategy", "governance", "swot"]
            },
        ],

        "NDA": [
            {
                "topic": "Mathematics",
                "probability": 95,
                "priority": "high",
                "reason": "300 marks paper - Highest",
                "trend": "stable",
                "top_keywords": ["algebra", "trigonometry", "calculus"]
            },
            {
                "topic": "General Knowledge",
                "probability": 82,
                "priority": "high",
                "reason": "History + Geography + Current",
                "trend": "stable",
                "top_keywords": ["history", "geography", "defence"]
            },
            {
                "topic": "Physics",
                "probability": 78,
                "priority": "high",
                "reason": "GAT Science section",
                "trend": "stable",
                "top_keywords": ["mechanics", "optics", "electric"]
            },
            {
                "topic": "English",
                "probability": 70,
                "priority": "high",
                "reason": "GAT English section",
                "trend": "stable",
                "top_keywords": ["grammar", "comprehension", "vocabulary"]
            },
            {
                "topic": "Chemistry",
                "probability": 65,
                "priority": "medium",
                "reason": "GAT - Medium questions",
                "trend": "stable",
                "top_keywords": ["organic", "element", "reaction"]
            },
        ],
    }

    result = demo_data.get(exam, demo_data["JEE Main"])
    logger.info(
        f"Demo data: {exam} - {len(result)} topics"
    )
    return result

# ============================================
# FILE CLEANUP
# ============================================

def cleanup_files(file_paths):
    """Files delete karna"""
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Deleted: {path}")
        except Exception as e:
            logger.error(f"Delete failed {path}: {e}")

# ============================================
# MAIN PROCESS FUNCTION
# ============================================

def process_papers(pdf_paths, exam):
    """Main function - PDFs process karna"""
    logger.info(
        f"Processing {len(pdf_paths)} PDFs for {exam}"
    )

    all_text = ""
    failed_files = []
    successful_files = []

    for pdf_path in pdf_paths:
        if not os.path.exists(pdf_path):
            logger.error(f"Not found: {pdf_path}")
            failed_files.append(pdf_path)
            continue

        try:
            text = extract_text_from_pdf(pdf_path)
            if len(text.strip()) > 50:
                all_text += text + "\n"
                successful_files.append(pdf_path)
            else:
                logger.warning(f"Little text: {pdf_path}")
                failed_files.append(pdf_path)
        except Exception as e:
            logger.error(f"Error {pdf_path}: {e}")
            failed_files.append(pdf_path)

    if len(all_text.strip()) < 50:
        logger.warning("Insufficient text - demo data")
        return {
            'predictions': get_demo_data(exam),
            'mode': 'demo_fallback',
            'successful_files': 0,
            'failed_files': len(pdf_paths)
        }

    topic_counts = analyze_topics(all_text, exam)
    predictions = generate_predictions(topic_counts, exam)
    difficulty = analyze_difficulty(all_text)
    question_patterns = identify_question_patterns(all_text)
    syllabus_coverage = track_syllabus_coverage(
        predictions, exam
    )

    logger.info(f"Analysis done: {len(predictions)} topics")

    return {
        'predictions': predictions,
        'mode': 'pdf',
        'difficulty_analysis': difficulty,
        'question_patterns': question_patterns,
        'syllabus_coverage': syllabus_coverage,
        'successful_files': len(successful_files),
        'failed_files': len(failed_files),
        'total_text_length': len(all_text)
    }