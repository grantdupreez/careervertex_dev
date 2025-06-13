CUSTOM_CSS = """
:root {
    --primary: #0A1F3D;
    --secondary: #B8860B;
    --secondary-light: #D4AF37;
    --light: #F8F9FA;
    --dark: #0D1117;
    --accent: #1E5A94;
    --gray-light: #F0F2F5;
    --gray: #E1E5EA;
    --success: #10B981;
    --error: #EF4444;
}

/* Global styles */
.stApp {
    background-color: var(--light);
    color: var(--dark);
}

/* Headers with Playfair Display feel */
h1, h2, h3, h4, h5 {
    color: var(--primary);
    font-weight: 600;
    font-family: 'Playfair Display', serif;
}

/* Gold gradient text */
.gold-gradient {
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    display: inline;
}

/* Primary buttons with gold gradient */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 100%);
    color: var(--dark);
    border: none;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    box-shadow: 0 5px 15px rgba(184, 134, 11, 0.2);
    transition: all 0.4s ease;
    border-radius: 2px;
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
}

.stButton > button:hover {
    border-color: var(--secondary);
    color: var(--secondary);
}

/* Cards */
.card {
    background-color: white;
    border-radius: 5px;
    padding: 2rem;
    box-shadow: 0 10px 30px rgba(0,0,0,0.03);
    border: 1px solid var(--gray);
    margin-bottom: 1.5rem;
    transition: all 0.4s ease;
}

.card:hover {
    box-shadow: 0 20px 40px rgba(0,0,0,0.08);
    transform: translateY(-5px);
}

/* Input fields */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background-color: white;
    border: 1px solid var(--gray);
    border-radius: 2px;
    color: var(--dark);
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--secondary);
    box-shadow: 0 0 0 2px rgba(184, 134, 11, 0.1);
}

/* File uploader */
.stFileUploader {
    border: 2px dashed var(--gray);
    border-radius: 5px;
    background-color: white;
    transition: all 0.3s ease;
}

.stFileUploader:hover {
    border-color: var(--secondary);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background-color: transparent;
    gap: 2px;
}

.stTabs [data-baseweb="tab"] {
    background-color: white;
    color: var(--primary);
    border-radius: 4px 4px 0 0;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: 1px solid var(--gray);
    border-bottom: none;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 100%) !important;
    color: var(--dark) !important;
    border: none;
}

/* Success/Error messages */
.stSuccess {
    background-color: rgba(16, 185, 129, 0.1);
    border: 1px solid var(--success);
    color: var(--success);
    padding: 12px;
    border-radius: 5px;
}

.stError {
    background-color: rgba(239, 68, 68, 0.1);
    border: 1px solid var(--error);
    color: var(--error);
    padding: 12px;
    border-radius: 5px;
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
}

[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    color: var(--primary);
    font-weight: 500;
    text-transform: uppercase;
    font-size: 12px;
    letter-spacing: 1px;
}

[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--secondary);
    font-weight: 700;
    font-size: 2rem;
}

/* Custom classes */
.hero-section {
    background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
    color: white;
    padding: 3rem;
    border-radius: 5px;
    margin-bottom: 2rem;
    text-align: center;
}

.status-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.875rem;
    font-weight: 600;
}

.status-active {
    background-color: var(--success);
    color: white;
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

/* Spinner overlay */
.spinner-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
}

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
"""
