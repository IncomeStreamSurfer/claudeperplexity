import os
from dotenv import load_dotenv
import anthropic
import signal
import sys
import csv
import requests

# Setup KeyboardInterrupt handling
def signal_handler(signal, frame):
    print("Interrupt received, shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Load variables from .env file
load_dotenv()

# Get variables from environment
brand_name = os.getenv("BRAND_NAME")
keywords_file_path = os.getenv("KEYWORDS_FILE_PATH")
sample_article_file_path = os.getenv("SAMPLE_ARTICLE_FILE_PATH")
image_urls_file_path = os.getenv("IMAGE_URLS_FILE_PATH")
blogs_file_path = os.getenv("BLOGS_FILE_PATH")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
use_perplexity = os.getenv("USE_PERPLEXITY", "false").lower() == "true"
content_type = os.getenv("CONTENT_TYPE", "article")
business_type = os.getenv("BUSINESS_TYPE", "")
article_framing = os.getenv("ARTICLE_FRAMING", "")
brand_guidelines_file_path = os.getenv("BRAND_GUIDELINES_FILE_PATH")
article_tone = os.getenv("ARTICLE_TONE", "")
famous_person = os.getenv("FAMOUS_PERSON", "")
perplexity_prompt = os.getenv("PERPLEXITY_PROMPT", "")

print("Variables loaded from environment.")

# Read file contents
def read_file_content(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()

keywords = read_file_content(keywords_file_path).splitlines()
sample_article = read_file_content(sample_article_file_path)
blogs = read_file_content(blogs_file_path)
brand_guidelines = read_file_content(brand_guidelines_file_path)

print("File contents read.")

def read_csv_file(file_path):
    data = []
    with open(file_path, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header row
        for row in reader:
            if len(row) == 2:
                data.append({"page_url": row[0], "image_url": row[1]})
    return data

image_urls = read_csv_file(image_urls_file_path)

print("Image URLs read from CSV file.")

def get_user_input(prompt):
    global user_input
    user_input = input(prompt)

def stream_content(stream):
    content = ""
    for text in stream.text_stream:
        print(text, end="", flush=True)
        content += text
    return content

def generate_content(system_prompt, user_prompt, api_key):
    client = anthropic.Client(api_key=api_key)
    while True:
        try:
            print("Generating content...")
            with client.messages.stream(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            ) as stream:
                content = stream_content(stream)
        except KeyboardInterrupt:
            print("\nGeneration paused.")
            feedback = input("Please provide your feedback (or press Enter to continue): ")
            if feedback.strip() == "":
                break
            else:
                print("Feedback received. Restarting the generation with the updated prompt.")
                user_prompt += f"\nUser Feedback: {feedback}"
        else:
            print("\nContent generation completed.")
            break
    return content

def perplexity_chat_completion(messages, api_key):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "mistral-7b-instruct",
        "messages": messages
    }
    print("Sending request to Perplexity API...")
    response = requests.post(url, json=payload, headers=headers)
    print(f"Perplexity API response status code: {response.status_code}")
    if response.status_code == 200:
        print("Perplexity API request successful.")
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"Perplexity API request failed with status code {response.status_code}: {response.text}")

if __name__ == "__main__":
    output_file = "generated_content.csv"
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Keyword", "Content"])  # Write the header row

        for keyword in keywords:
            print(f"Processing keyword: {keyword}")
            perplexity_info = ""
            if use_perplexity:
                print("Using Perplexity API.")
                messages = [
                    {"role": "system", "content": "Be precise and concise."},
                    {"role": "user", "content": f"{perplexity_prompt} {keyword}"}
                ]
                print(f"Perplexity prompt: {perplexity_prompt} {keyword}")
                perplexity_info = perplexity_chat_completion(messages, perplexity_api_key)
                print(f"Perplexity information: {perplexity_info}")
            else:
                print("Perplexity API not used.")

            user_prompt = f"""
            DO NOT INCLUDE ANY EXTERNAL LINKS TO COMPETITORS. Include internal links from {image_urls_file_path} Start writing immediately with <h1> DO NOT START BY TALKING TO ME.  Please write a long-form SEO-optimized article with 1500 words about the following keyword: {keyword}. Answer in HTML, starting with one single <h1> tag, as this is going on wordpress, do not give unecessary HTML tags. Please use a lot of formatting, tables are great for ranking on Google. Always include a key takeaways table at the top giving the key information for this topic at the very top of the article.

            Include the following information from Perplexity AI:
            {perplexity_info}

            The article should be written in a {article_tone} tone and framed as {article_framing}.
            Incorporate the brand guidelines:
            {brand_guidelines}

            This is a {business_type} so write from the perspective of that business.
            Please closely follow the tone of {famous_person}
            """

            print(f"User prompt: {user_prompt}")

            content = generate_content("System Prompt Here", user_prompt, anthropic_api_key)

            if content:
                if isinstance(content, list):
                    content = "\n".join([block.text for block in content])  # Extract text from ContentBlock objects and join them
                writer.writerow([keyword, content])  # Write the keyword and content to the CSV file
                print(f"Content generated for keyword: {keyword}, and saved to {output_file}.")
            else:
                print("Failed to generate content for keyword:", keyword)

    print(f"All generated content saved to {output_file}.")