import os
import sys

# Add the frontend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "frontend"))

# Set environment variable to indicate we're on Streamlit Cloud
os.environ["STREAMLIT_SHARING"] = "true"

# Import and run the frontend app
from frontend import frontend

# The frontend code will automatically be executed when imported 