import requests
from bs4 import BeautifulSoup
import re
import time
import os

def is_valid_article(url):
    """
    Validate if the URL is a valid Wikipedia article.
    
    Args:
        url (str): The URL to validate.
    
    Returns:
        bool: True if the URL is a valid Wikipedia article, False otherwise.
    """
    # Patterns to exclude non-article pages
    exclude_patterns = [
        r'/wiki/Special:',     # Special pages
        r'/wiki/Help:',        # Help pages
        r'/wiki/Wikipedia:',   # Wikipedia project pages
        r'/wiki/Portal:',      # Portal pages
        r'/wiki/Category:',    # Category pages
        r'/wiki/Template:',    # Template pages
        r'/wiki/File:',        # File pages
        r'/wiki/Talk:',        # Talk/discussion pages
        r'/wiki/User:',        # User pages
        r'/wiki/Main_Page'     # Main page
    ]
    
    # Check if URL matches any exclude patterns
    for pattern in exclude_patterns:
        if re.search(pattern, url):
            return False
    
    return True

def extract_article_content(url):
    """
    Extract the main content of a Wikipedia article, organized by headings.
    
    Args:
        url (str): The URL of the Wikipedia article.
    
    Returns:
        dict: A dictionary containing article details.
    """
    try:
        # Add a small delay to avoid overwhelming the server
        time.sleep(0.5)
        
        # Send a request to the URL
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = soup.find('h1', {'id': 'firstHeading'})
        title = title.text.strip() if title else 'No Title'
        
        # Extract main content
        content_div = soup.find('div', {'class': 'mw-parser-output'})
        if not content_div:
            return None
        
        # Debug: Print the HTML structure of the content div
        print(content_div.prettify())  # Add this line to inspect the HTML structure
        
        # Initialize variables to store content
        content = []
        current_heading = title
        current_content = []
        
        # Function to recursively extract text from an element
        def extract_text(element):
            if element.name in ['script', 'style', 'table', 'figure']:  # Skip scripts, styles, tables, and figures
                return ''
            if element.name == 'p':  # Paragraphs
                return element.get_text(strip=True)
            if element.name == 'ul':  # Lists
                list_items = element.find_all('li')
                return '\n'.join([f"- {li.get_text(strip=True)}" for li in list_items])
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:  # Headings
                return f"\n{element.get_text(strip=True)}\n"
            # Recursively extract text from nested elements
            return ''.join([extract_text(child) for child in element.children if child.name is not None])
        
        # Iterate through all elements in the content div
        for element in content_div.children:
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:  # Headings
                # Save the previous heading and content
                if current_content:
                    content.append({'heading': current_heading, 'content': current_content})
                    current_content = []
                # Update the current heading
                current_heading = element.get_text(strip=True)
            else:
                # Extract text from the element
                text = extract_text(element)
                if text.strip():
                    current_content.append(text)
        
        # Add the last heading and content
        if current_content:
            content.append({'heading': current_heading, 'content': current_content})
        
        # If no content was found, return None
        if not content:
            return None
        
        return {
            'url': url,
            'title': title,
            'content': content
        }
    
    except Exception as e:
        print(f"Error extracting content from {url}: {e}")
        return None

def get_all_links(url):
    '''
    Get all internal Wikipedia links from a given URL, filtered for valid articles.
    
    Args:
        url (str): The URL to scrape for links.
    
    Returns:
        list: A list of internal Wikipedia article links.
    '''
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all internal Wikipedia links
        links = soup.find_all('a', href=re.compile(r'^/wiki/'))
        
        # Convert relative links to full URLs and filter for valid articles
        full_links = [
            f'https://zh.wikipedia.org{link["href"]}' 
            for link in links 
            if is_valid_article(link['href'])
        ]
        
        return full_links
    except Exception as e:
        print(f"Error fetching links from {url}: {e}")
        return []

def scrape_all_links_and_content(start_url, depth=2, max_urls=100):
    '''
    Scrape all links from the start URL and extract their content.
    
    Args:
        start_url (str): The starting URL to scrape.
        depth (int): The depth of link traversal.
        max_urls (int): Maximum number of URLs to scrape.
    
    Returns:
        dict: A dictionary of scraped URLs and their content.
    '''
    visited = set()
    results = {}

    def crawl(current_url, current_depth):
        # Stop if we've reached max URLs or max depth
        if (len(results) >= max_urls or 
            current_depth > depth or 
            current_url in visited):
            return
        
        visited.add(current_url)
        print(f"Crawling: {current_url} (Depth: {current_depth}, Total URLs: {len(results)})")
        
        # Extract content from the current URL
        article_content = extract_article_content(current_url)
        if article_content:
            results[current_url] = article_content
        
        # Get all links from the current URL
        links = get_all_links(current_url)
        
        # Recursively crawl links found on the current page
        for link in links:
            if (link not in visited and 
                len(results) < max_urls):
                crawl(link, current_depth + 1)
    
    crawl(start_url, 0)
    return results

def save_results_to_txt(data, filename='wikipedia_content.txt'):
    '''
    Save the scraped content to a text file, organized by headings.
    
    Args:
        data (dict): A dictionary of URLs and their content.
        filename (str): The name of the output file.
    '''
    # Check if path has a directory component
    dir_name = os.path.dirname(filename)
    
    # Only try to create directory if there is a directory component
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as file:
        for url, article in data.items():
            # Write URL
            file.write(f"URL: {url}\n")
            
            # Write Title
            file.write(f"Title: {article['title']}\n")
            
            # Write Content
            file.write("Content:\n")
            for section in article['content']:
                file.write(f"  {section['heading']}\n")
                for paragraph in section['content']:
                    file.write(f"    {paragraph}\n")
                file.write("\n")
            
            # Add a separator between articles
            file.write("\n" + "="*50 + "\n\n")
    
    print(f"Saved {len(data)} articles to {filename}")

def main():
    start_url = 'https://zh.wikipedia.org/zh-hans/音乐'
    scraped_data = scrape_all_links_and_content(start_url, depth=2, max_urls=5)
    save_results_to_txt(scraped_data)

if __name__ == '__main__':
    main()