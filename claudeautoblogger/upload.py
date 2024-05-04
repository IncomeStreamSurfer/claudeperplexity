import os
import pandas as pd
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Extracting data from .env
site = os.getenv('WORDPRESS_SITE')
username = os.getenv('WORDPRESS_USERNAME')
password = os.getenv('WORDPRESS_APP_PASSWORD')

auth = requests.auth.HTTPBasicAuth(username, password)


def upload_post(title, content):
    """Upload a post to WordPress as a draft."""
    url = f"{site}/wp-json/wp/v2/posts"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    data = {
        'title': title,
        'content': content,
        'status': 'draft'  # Posts are uploaded as drafts
    }
    response = requests.post(url, auth=auth, headers=headers, json=data)
    return response.json()

# Correct path for the CSV file
df = pd.read_csv('generated_content.csv')

# Upload each row as a post
results = []
for index, row in df.iterrows():
    post_response = upload_post(row['Keyword'], row['Content'])
    results.append(post_response)

# Optionally, print results to check the responses from the server
for result in results:
    print(result)
