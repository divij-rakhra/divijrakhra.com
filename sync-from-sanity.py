#!/usr/bin/env python3
"""Sync blog posts from Sanity CMS"""
import json
import requests
from pathlib import Path
from datetime import datetime
import base64

# Load Sanity config
SANITY_TOKEN = json.load(open('/Users/divijrakhra/.openclaw/workspace/.secrets/sanity.json'))['token']
PROJECT_ID = 'n7kwozrn'
DATASET = 'production'

SITE_PATH = Path('/Users/divijrakhra/.openclaw/workspace/projects/personal-site')

def fetch_posts():
    """Fetch all blog posts from Sanity"""
    query = '''
    *[_type == "post"] | order(date desc) {
      title,
      "slug": slug.current,
      date,
      readTime,
      body,
      mainImage{
        asset->{
          _id,
          url
        }
      }
    }
    '''

    response = requests.get(
        f'https://{PROJECT_ID}.api.sanity.io/v1/data/query/{DATASET}',
        headers={
            'Authorization': f'Bearer {SANITY_TOKEN}'
        },
        params={'query': query}
    )

    if response.status_code == 200:
        return response.json()['result']
    else:
        print(f"Error fetching posts: {response.text}")
        return []

def download_image(url, slug):
    """Download image and save locally"""
    response = requests.get(url)
    if response.status_code == 200:
        img_path = SITE_PATH / 'images' / f'{slug}.jpg'
        img_path.parent.mkdir(exist_ok=True)
        img_path.write_bytes(response.content)
        return f'images/{slug}.jpg'
    return None

def convert_block_to_html(block):
    """Convert Sanity block to HTML"""
    if block['_type'] == 'block':
        # Text block
        children = block.get('children', [])
        text = ''.join([child.get('text', '') for child in children])

        style = block.get('style', 'normal')

        if style == 'h2':
            return f'<h2>{text}</h2>'
        elif style == 'normal':
            return f'<p>{text}</p>'
        elif style == 'blockquote':
            return f'<blockquote>{text}</blockquote>'

    elif block['_type'] == 'image':
        # Image block - return placeholder, will be handled separately
        return ''

    return ''

def generate_post_html(post):
    """Generate HTML for a blog post"""
    title = post['title']
    slug = post['slug']
    date = post['date']
    read_time = post.get('readTime', '5 min')

    # Format date
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    date_display = date_obj.strftime('%B %Y')

    # Download main image if exists
    image_html = ''
    if post.get('mainImage') and post['mainImage'].get('asset'):
        img_path = download_image(post['mainImage']['asset']['url'], slug)
        if img_path:
            image_html = f'<img src="{img_path}" alt="{title}" class="post-image">\n    '

    # Convert body to HTML
    body_html = []
    for block in post.get('body', []):
        html = convert_block_to_html(block)
        if html:
            body_html.append(html)

    content_html = '\n    '.join(body_html)

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

    {image_html}<div class="post-body">
{content_html}
    </div>
  </div>
</body>
</html>"""

    return slug, html

def update_index_html(posts):
    """Update index.html with latest posts"""
    index_path = SITE_PATH / 'index.html'
    index_content = index_path.read_text()

    # Find the writing section
    writing_start = index_content.find('<div class="section-label">Writing</div>')
    writing_end = index_content.find('</div>', index_content.find('</div>', writing_start) + 6)

    # Generate blog list
    blog_items = []
    for post in posts:
        title = post['title']
        slug = post['slug']
        date = post['date']

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
    print("Fetching posts from Sanity...")
    posts = fetch_posts()

    if not posts:
        print("No posts found. Make sure you have posts in Sanity with _type='post'")
        print("\nTo add posts, go to: https://www.sanity.io/manage")
        print(f"Project: {PROJECT_ID}")
    else:
        print(f"Found {len(posts)} posts to sync")

        for post in posts:
            slug, html = generate_post_html(post)

            # Create directory and write file
            post_dir = SITE_PATH / 'blog' / slug
            post_dir.mkdir(parents=True, exist_ok=True)

            (post_dir / 'index.html').write_text(html)
            print(f"✓ Generated: {slug}")

        # Update index.html
        print("\nUpdating index.html...")
        update_index_html(posts)

        print("\n✓ Sync complete")
