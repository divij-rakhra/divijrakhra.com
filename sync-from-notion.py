#!/usr/bin/env python3
"""Pull blog posts from Notion and generate static HTML"""
import json
import requests
from pathlib import Path
from datetime import datetime

NOTION_TOKEN = json.load(open('/Users/divijrakhra/.openclaw/workspace/.secrets/notion.json'))['token']
BLOG_DB = '33a1293d-b543-817b-ba9d-cc31916a1a2c'

HEADERS = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Content-Type': 'application/json',
    'Notion-Version': '2022-06-28'
}

SITE_PATH = Path('/Users/divijrakhra/.openclaw/workspace/projects/personal-site')

def get_ready_posts():
    """Fetch all posts with Status = 'Ready'"""
    payload = {
        'filter': {
            'property': 'Status',
            'select': {'equals': 'Ready'}
        }
    }
    
    response = requests.post(
        f'https://api.notion.com/v1/databases/{BLOG_DB}/query',
        headers=HEADERS,
        json=payload
    )
    
    if response.status_code == 200:
        return response.json()['results']
    else:
        print(f"Error fetching posts: {response.text}")
        return []

def get_post_content(page_id):
    """Get block content from a page"""
    response = requests.get(
        f'https://api.notion.com/v1/blocks/{page_id}/children',
        headers=HEADERS
    )
    
    if response.status_code == 200:
        return response.json()['results']
    else:
        return []

def convert_blocks_to_html(blocks):
    """Convert Notion blocks to HTML"""
    html = []
    
    for block in blocks:
        block_type = block['type']
        
        if block_type == 'paragraph':
            text = ''.join([t['text']['content'] for t in block['paragraph']['rich_text']])
            html.append(f"<p>{text}</p>")
        
        elif block_type == 'heading_2':
            text = ''.join([t['text']['content'] for t in block['heading_2']['rich_text']])
            html.append(f"<h2>{text}</h2>")
        
        elif block_type == 'quote':
            text = ''.join([t['text']['content'] for t in block['quote']['rich_text']])
            html.append(f"<blockquote>{text}</blockquote>")
        
        elif block_type == 'bulleted_list_item':
            text = ''.join([t['text']['content'] for t in block['bulleted_list_item']['rich_text']])
            html.append(f"<li>{text}</li>")
    
    return '\n'.join(html)

def generate_post_html(post):
    """Generate HTML file for a post"""
    props = post['properties']
    
    title = props['Title']['title'][0]['text']['content']
    slug = props['Slug']['rich_text'][0]['text']['content']
    date = props['Date']['date']['start']
    read_time = props['Read Time']['rich_text'][0]['text']['content']
    
    # Format date for display
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    date_display = date_obj.strftime('%B %Y')
    
    # Get content
    blocks = get_post_content(post['id'])
    content_html = convert_blocks_to_html(blocks)
    
    # Generate full HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Divij Rakhra</title>
  <link rel="stylesheet" href="../../style.css">
</head>
<body>
  <div class="container">
    <a href="../../index.html" class="back-link">← Back</a>
    
    <h1 class="post-title">{title}</h1>
    <div class="post-meta">{date_display} · {read_time}</div>
    
    <div class="post-body">
{content_html}
    </div>
  </div>
</body>
</html>"""
    
    return slug, html

def mark_as_published(page_id):
    """Update post status to Published"""
    payload = {
        'properties': {
            'Status': {'select': {'name': 'Published'}}
        }
    }
    
    requests.patch(
        f'https://api.notion.com/v1/pages/{page_id}',
        headers=HEADERS,
        json=payload
    )

def update_index_html(posts):
    """Update index.html with latest posts"""
    # Read current index
    index_path = SITE_PATH / 'index.html'
    index_content = index_path.read_text()
    
    # Find the writing section
    # This is a simple approach - you might want to use an HTML parser
    writing_start = index_content.find('<div class="section-label">Writing</div>')
    writing_end = index_content.find('</div>', index_content.find('</div>', writing_start) + 6)
    
    # Generate new blog list
    blog_items = []
    for post in sorted(posts, key=lambda p: p['properties']['Date']['date']['start'], reverse=True):
        props = post['properties']
        title = props['Title']['title'][0]['text']['content']
        slug = props['Slug']['rich_text'][0]['text']['content']
        date = props['Date']['date']['start']
        
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        date_display = date_obj.strftime('%b %Y')
        
        blog_items.append(f"""      <div class="blog-item">
        <div class="blog-date">{date_display}</div>
        <a href="blog/{slug}/" class="blog-link">{title}</a>
      </div>""")
    
    new_writing_section = f"""<div class="section-label">Writing</div>
    <div class="blog-list">
{chr(10).join(blog_items)}
    </div>"""
    
    # Replace the section
    new_index = index_content[:writing_start] + new_writing_section + index_content[writing_end+6:]
    index_path.write_text(new_index)

if __name__ == '__main__':
    print("Fetching posts with Status = 'Ready'...")
    posts = get_ready_posts()
    
    if not posts:
        print("No posts to sync")
    else:
        print(f"Found {len(posts)} posts to sync")
        
        for post in posts:
            slug, html = generate_post_html(post)
            
            # Create directory and write file
            post_dir = SITE_PATH / 'blog' / slug
            post_dir.mkdir(parents=True, exist_ok=True)
            
            (post_dir / 'index.html').write_text(html)
            print(f"✓ Generated: {slug}")
            
            # Mark as published in Notion
            mark_as_published(post['id'])
        
        # Update index.html
        print("\nUpdating index.html...")
        update_index_html(posts)
        
        print("\n✓ Sync complete")
