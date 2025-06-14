CUSTOM_CSS = """
/* Import fonts similar to index.html */
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700&family=Montserrat:wght@300;400;500;600;700&display=swap');

:root {
    --primary: #0A1F3D; /* Deep Navy Blue */
    --secondary: #B8860B; /* Dark Goldenrod */
    --secondary-light: #D4AF37; /* Pale Goldenrod */
    --light: #F8F9FA; /* Very Light Gray */
    --dark: #0D1117; /* Rich Black */
    --accent: #1E5A94; /* Steel Blue */
    --gray-light: #F0F2F5; /* Lightest Gray */
    --gray: #E1E5EA; /* Light Gray */
    --success: #10B981; /* Emerald Green */
    --error: #EF4444; /* Red */
}

/* Global styles */
.stApp {
    background-color: var(--light);
    color: var(--dark);
    font-family: 'Montserrat', sans-serif;
}

/* Override Streamlit's default main content area */
.main .block-container {
    max-width: 1240px;
    padding: 2rem 30px;
}

/* Headers with Playfair Display */
h1, h2, h3, h4, h5 {
    font-family: 'Playfair Display', serif !important;
    color: var(--primary);
    font-weight: 600;
}

h1 {
    font-size: 3rem;
    line-height: 1.2;
    letter-spacing: 0.5px;
}

h2 {
    font-size: 2.5rem;
    position: relative;
    padding-bottom: 1.5rem;
}

/* Section title underline like index.html */
h2::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 80px;
    height: 2px;
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 100%);
}

/* Gold gradient text */
.gold-gradient {
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    display: inline;
}

/* Primary buttons matching index.html CTA */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 80%);
    color: var(--dark);
    padding: 16px 32px;
    border-radius: 2px;
    font-weight: 600;
    font-family: 'Montserrat', sans-serif;
    text-decoration: none;
    transition: all 0.4s ease;
    border: none;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    font-size: 14px;
    box-shadow: 0 5px 15px rgba(184, 134, 11, 0.2);
}

.stButton > button[kind="primary"]:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 20px rgba(184, 134, 11, 0.3);
}

/* Regular buttons */
.stButton > button {
    border-radius: 2px;
    border: 1px solid var(--gray);
    transition: all 0.3s ease;
    font-family: 'Montserrat', sans-serif;
    font-weight: 500;
    background-color: white;
}

.stButton > button:hover {
    border-color: var(--secondary);
    color: var(--secondary);
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
}

/* Cards matching index.html feature cards */
.card {
    background-color: white;
    border-radius: 5px;
    padding: 40px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.03);
    transition: all 0.4s ease;
    border: 1px solid var(--gray);
    position: relative;
    overflow: hidden;
}

.card::before {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 3px;
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 100%);
    transform: scaleX(0);
    transform-origin: right;
    transition: transform 0.4s ease;
}

.card:hover {
    transform: translateY(-10px);
    box-shadow: 0 20px 40px rgba(0,0,0,0.08);
    border-color: transparent;
}

.card:hover::before {
    transform: scaleX(1);
    transform-origin: left;
}

/* Input fields */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {
    background-color: white;
    border: 1px solid var(--gray);
    border-radius: 2px;
    color: var(--dark);
    font-family: 'Montserrat', sans-serif;
    transition: all 0.3s ease;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--secondary);
    box-shadow: 0 0 0 2px rgba(184, 134, 11, 0.1);
}

/* File uploader */
.uploadedFile {
    border: 2px dashed var(--gray);
    border-radius: 5px;
    background-color: white;
    transition: all 0.3s ease;
}

.uploadedFile:hover {
    border-color: var(--secondary);
    background-color: rgba(184, 134, 11, 0.05);
}

/* Tabs matching index.html */
.stTabs [data-baseweb="tab-list"] {
    background-color: transparent;
    gap: 2px;
}

.stTabs [data-baseweb="tab"] {
    background-color: white;
    color: var(--primary);
    border-radius: 2px 2px 0 0;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-family: 'Montserrat', sans-serif;
    border: 1px solid var(--gray);
    border-bottom: none;
    transition: all 0.3s ease;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 100%) !important;
    color: var(--dark) !important;
    border: none;
}

/* Success/Error/Warning/Info messages */
.stAlert {
    border-radius: 5px;
    font-family: 'Montserrat', sans-serif;
}

div[data-testid="stAlert"][data-baseweb="notification"] > div[kind="success"] {
    background-color: rgba(16, 185, 129, 0.1);
    border: 1px solid var(--success);
    color: var(--success);
}

div[data-testid="stAlert"][data-baseweb="notification"] > div[kind="error"] {
    background-color: rgba(239, 68, 68, 0.1);
    border: 1px solid var(--error);
    color: var(--error);
}

/* Progress bars */
.stProgress > div > div > div > div {
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 100%);
}

/* Metrics */
[data-testid="metric-container"] {
    background-color: white;
    border: 1px solid var(--gray);
    padding: 1.5rem;
    border-radius: 5px;
    text-align: center;
    box-shadow: 0 5px 15px rgba(0,0,0,0.03);
    transition: all 0.3s ease;
}

[data-testid="metric-container"]:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 25px rgba(0,0,0,0.08);
}

[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    color: var(--primary);
    font-weight: 500;
    text-transform: uppercase;
    font-size: 12px;
    letter-spacing: 1px;
    font-family: 'Montserrat', sans-serif;
}

[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--secondary);
    font-weight: 700;
    font-size: 2rem;
    font-family: 'Playfair Display', serif;
}

/* Custom classes matching index.html */
.feature-icon {
    width: 70px;
    height: 70px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(184,134,11,0.1) 0%, rgba(212,175,55,0.1) 100%);
    border-radius: 50%;
    margin: 0 auto 25px auto;
    position: relative;
}

.feature-icon::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    border-radius: 50%;
    border: 1px solid rgba(184,134,11,0.2);
}

.status-badge {
    display: inline-block;
    padding: 8px 16px;
    border-radius: 2px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-family: 'Montserrat', sans-serif;
}

.status-active {
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 100%);
    color: var(--dark);
}

.status-inactive {
    background-color: var(--error);
    color: white;
}

.keyword-tag {
    display: inline-block;
    background: linear-gradient(135deg, rgba(184,134,11,0.1) 0%, rgba(212,175,55,0.1) 100%);
    border: 1px solid var(--secondary-light);
    border-radius: 20px;
    padding: 0.5rem 1rem;
    margin: 0.25rem;
    font-weight: 500;
    color: var(--primary);
    font-family: 'Montserrat', sans-serif;
    font-size: 14px;
}

.score-circle {
    width: 150px;
    height: 150px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 3rem;
    font-weight: 700;
    margin: 0 auto;
    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    font-family: 'Playfair Display', serif;
}

.score-high {
    background: linear-gradient(135deg, var(--success) 0%, #34D399 100%);
    color: white;
}

.score-medium {
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 100%);
    color: var(--dark);
}

.score-low {
    background: linear-gradient(135deg, var(--error) 0%, #F87171 100%);
    color: white;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background-color: var(--primary);
}

section[data-testid="stSidebar"] .stMarkdown {
    color: white;
}

/* Expander styling */
.streamlit-expanderHeader {
    background-color: white;
    border: 1px solid var(--gray);
    border-radius: 2px;
    font-family: 'Montserrat', sans-serif;
    font-weight: 500;
}

.streamlit-expanderHeader:hover {
    border-color: var(--secondary);
    color: var(--secondary);
}

/* Checkbox styling */
.stCheckbox > label {
    font-family: 'Montserrat', sans-serif;
}

/* Radio button styling */
.stRadio > div {
    font-family: 'Montserrat', sans-serif;
}

/* Download button */
.stDownloadButton > button {
    background: linear-gradient(135deg, var(--accent) 0%, #2B6CB0 100%);
    color: white;
    border: none;
    font-weight: 600;
    font-family: 'Montserrat', sans-serif;
    letter-spacing: 0.5px;
    transition: all 0.3s ease;
}

.stDownloadButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(30, 90, 148, 0.3);
}

/* Spinner styling */
div[data-testid="stSpinner"] > div {
    border-color: var(--secondary) transparent transparent transparent;
}

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Custom scrollbar */
::-webkit-scrollbar {
    width: 10px;
}

::-webkit-scrollbar-track {
    background: var(--gray-light);
}

::-webkit-scrollbar-thumb {
    background: var(--secondary);
    border-radius: 5px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--secondary-light);
}
"""
