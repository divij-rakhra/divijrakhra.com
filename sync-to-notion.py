#!/usr/bin/env python3
"""Sync blog posts to Notion CMS"""
import json
import requests
from pathlib import Path

NOTION_TOKEN = json.load(open('/Users/divijrakhra/.openclaw/workspace/.secrets/notion.json'))['token']
DIVIJ_ROOT = json.load(open('/Users/divijrakhra/.openclaw/workspace/.secrets/notion.json'))['pages']['divij_root']

HEADERS = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Content-Type': 'application/json',
    'Notion-Version': '2022-06-28'
}

# Blog posts data
posts = [
    {
        'title': 'Why most B2B SaaS landing pages lose money',
        'slug': 'why-b2b-saas-landing-pages-lose-money',
        'date': '2026-03-15',
        'read_time': '4 min',
        'file': 'blog/why-b2b-saas-landing-pages-lose-money/index.html'
    },
    {
        'title': 'The agency playbook I wish I had in year one',
        'slug': 'the-agency-playbook',
        'date': '2026-02-20',
        'read_time': '6 min',
        'file': 'blog/the-agency-playbook/index.html'
    },
    {
        'title': 'Revenue UX: the missing metric between design and growth',
        'slug': 'revenue-ux-missing-metric',
        'date': '2026-01-15',
        'read_time': '5 min',
        'file': 'blog/revenue-ux-missing-metric/index.html'
    },
    {
        'title': "Cold outreach is not dead. You're just doing it wrong.",
        'slug': 'cold-outreach-not-dead',
        'date': '2025-12-10',
        'read_time': '5 min',
        'file': 'blog/cold-outreach-not-dead/index.html'
    }
]

def extract_content(html_file):
    """Extract post body from HTML file"""
    content = Path(f'/Users/divijrakhra/.openclaw/workspace/projects/personal-site/{html_file}').read_text()
    # Extract content between <div class="post-body"> and </div>
    start = content.find('<div class="post-body">') + len('<div class="post-body">')
    end = content.find('</div>', start)
    return content[start:end].strip()

def create_blog_database():
    """Create a blog database under Divij's root page"""
    payload = {
        'parent': {'page_id': DIVIJ_ROOT},
        'title': [{'type': 'text', 'text': {'content': 'Blog Posts'}}],
        'properties': {
            'Title': {'title': {}},
            'Slug': {'rich_text': {}},
            'Date': {'date': {}},
            'Read Time': {'rich_text': {}},
            'Status': {'select': {'options': [{'name': 'Draft'}, {'name': 'Published'}]}}
        }
    }
    
    response = requests.post(
        'https://api.notion.com/v1/databases',
        headers=HEADERS,
        json=payload
    )
    
    if response.status_code == 200:
        return response.json()['id']
    else:
        print(f"Error creating database: {response.text}")
        return None

def add_post_to_database(database_id, post):
    """Add a blog post to the database"""
    content = extract_content(post['file'])
    
    # Convert HTML to Notion blocks (simplified - just paragraphs)
    children = []
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('<p>'):
            text = line.replace('<p>', '').replace('</p>', '')
            children.append({
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [{'type': 'text', 'text': {'content': text}}]
                }
            })
        elif line.startswith('<h2>'):
            text = line.replace('<h2>', '').replace('</h2>', '')
            children.append({
                'object': 'block',
                'type': 'heading_2',
                'heading_2': {
                    'rich_text': [{'type': 'text', 'text': {'content': text}}]
                }
            })
        elif line.startswith('<blockquote>'):
            text = line.replace('<blockquote>', '').replace('</blockquote>', '')
            children.append({
                'object': 'block',
                'type': 'quote',
                'quote': {
                    'rich_text': [{'type': 'text', 'text': {'content': text}}]
                }
            })
    
    payload = {
        'parent': {'database_id': database_id},
        'properties': {
            'Title': {'title': [{'type': 'text', 'text': {'content': post['title']}}]},
            'Slug': {'rich_text': [{'type': 'text', 'text': {'content': post['slug']}}]},
            'Date': {'date': {'start': post['date']}},
            'Read Time': {'rich_text': [{'type': 'text', 'text': {'content': post['read_time']}}]},
            'Status': {'select': {'name': 'Published'}}
        },
        'children': children
    }
    
    response = requests.post(
        'https://api.notion.com/v1/pages',
        headers=HEADERS,
        json=payload
    )
    
    if response.status_code == 200:
        print(f"✓ Added: {post['title']}")
    else:
        print(f"✗ Error adding {post['title']}: {response.text}")

if __name__ == '__main__':
    print("Creating Blog Posts database...")
    db_id = create_blog_database()
    
    if db_id:
        print(f"\nDatabase created: {db_id}\n")
        print("Adding blog posts...")
        for post in posts:
            add_post_to_database(db_id, post)
        print("\n✓ Sync complete")
        
        # Save database ID for future use
        secrets = json.load(open('/Users/divijrakhra/.openclaw/workspace/.secrets/notion.json'))
        secrets['databases']['blog_posts'] = db_id
        json.dump(secrets, open('/Users/divijrakhra/.openclaw/workspace/.secrets/notion.json', 'w'), indent=2)
    else:
        print("Failed to create database")
