from flask import Flask, render_template, request, jsonify
from apify_client import ApifyClient
import os
from dotenv import load_dotenv
from collections import Counter
import re
from datetime import datetime, timedelta
import numpy as np
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import bcrypt


# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///users.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "secret_key"

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    def __repr__(self):
        return f'<User {self.name}>'
    
    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

with app.app_context():
    db.create_all()


# Initialize the ApifyClient with your API token
client = ApifyClient("apify_api_KHXHucwuRukhv77x53Phu378m64N7o0zJKwP")

def analyze_sentiment(text):
    if not text:
        return 'neutral'

    # Convert text to lowercase for better matching
    text = text.lower()

    # Expanded word lists including emojis and common expressions
    positive_words = {
        # English positive
        'love', 'great', 'awesome', 'amazing', 'good', 'beautiful', 'perfect', 'best', 'nice',
        'wonderful', 'excellent', 'fantastic', 'happy', 'excited', 'blessed', 'thank', 'thanks',
        'gorgeous', 'stunning', 'incredible', 'superb', 'brilliant', 'outstanding',
        # Hindi/Hinglish positive
        'bahut', 'accha', 'acha', 'badhiya', 'mast', 'zabardast', 'kamaal', 'kamal', 'dil',
        'pyaar', 'pyar', 'shandaar', 'shandar', 'kya', 'baat', 'ekdum',
        # Emojis positive
        '❤️', '😍', '🥰', '👍', '🔥', '💯', '🙌', '👏', '💪', '✨', '💖', '💝', '💕', '💓',
        '🤗', '😊', '😇', '🥺', '💫', '⭐', '🌟', '👌', '💙', '♥️', '😘'
    }

    negative_words = {
        # English negative
        'hate', 'bad', 'terrible', 'worst', 'poor', 'awful', 'horrible', 'disgusting', 'pathetic',
        'waste', 'boring', 'disappointed', 'disappointing', 'useless', 'rubbish', 'garbage',
        # Hindi/Hinglish negative
        'bakwas', 'bekaar', 'bekar', 'ghatiya', 'wahiyat', 'bura', 'faltu', 'zeher', 'tatti',
        'bkwas', 'chutiya', 'chutiye', 'bhasad',
        # Emojis negative
        '👎', '😡', '🤮', '😠', '😤', '😒', '🙄', '😩', '😫', '😤', '💩', '🤢', '😑',
        '🤦', '🤦‍♂️', '🤦‍♀️', '😕', '👊', '😪'
    }

    neutral_words = {
        # English neutral
        'ok', 'okay', 'fine', 'normal', 'average', 'decent', 'not bad', 'alright',
        # Hindi/Hinglish neutral
        'theek', 'thik', 'chalega', 'chalta', 'hai',
        # Emojis neutral
        '🤔', '😐', '😶', '🤷', '🤷‍♂️', '🤷‍♀️', '😌', '😏'
    }

    # Count word and emoji matches
    pos_count = 0
    neg_count = 0
    neu_count = 0

    # Check for word matches
    words = text.split()
    for word in words:
        if word in positive_words:
            pos_count += 1
        elif word in negative_words:
            neg_count += 1
        elif word in neutral_words:
            neu_count += 1

    # Check for emoji matches (some might be part of words)
    for emoji in positive_words:
        if emoji in text and len(emoji.strip()) == 1:  # Only single character emojis
            pos_count += 1
    for emoji in negative_words:
        if emoji in text and len(emoji.strip()) == 1:
            neg_count += 1
    for emoji in neutral_words:
        if emoji in text and len(emoji.strip()) == 1:
            neu_count += 1

    # Common phrases and expressions (both English and Hindi/Hinglish)
    if any(phrase in text for phrase in ['very good', 'so good', 'bahut acha', 'bohot acha', 'kya baat', 'dil se']):
        pos_count += 2
    if any(phrase in text for phrase in ['very bad', 'so bad', 'bahut bura', 'bohot bura', 'ekdum bakwas']):
        neg_count += 2

    # Return sentiment based on counts
    if pos_count > neg_count:
        return 'positive'
    elif neg_count > pos_count:
        return 'negative'
    elif pos_count == 0 and neg_count == 0 and neu_count > 0:
        return 'neutral'
    else:
        # If no clear sentiment is detected, check for common patterns
        if '?' in text:  # Questions are often neutral
            return 'neutral'
        if len(text) < 5:  # Very short comments without clear sentiment
            return 'neutral'
        # Default to neutral if no clear sentiment
        return 'neutral'

def calculate_engagement_rate(followers, likes, comments):
    if followers == 0:
        return 0
    return ((likes + comments) / followers) * 100

def analyze_posting_frequency(posts):
    if not posts:
        return {"frequency": "No posts available"}
    
    # Get timestamps of posts and convert to integers
    timestamps = []
    for post in posts:
        timestamp = post.get('timestamp')
        if timestamp:
            # Convert string timestamp to integer if it's a string
            if isinstance(timestamp, str):
                try:
                    timestamp = int(timestamp)
                except ValueError:
                    continue
            timestamps.append(timestamp)
    
    if not timestamps:
        return {"frequency": "No valid timestamps found"}

    timestamps.sort(reverse=True)
    
    if len(timestamps) < 2:
        return {"frequency": "Not enough posts for analysis"}
    
    # Calculate average time between posts
    time_diffs = []
    for i in range(len(timestamps)-1):
        try:
            diff = int(timestamps[i]) - int(timestamps[i+1])
            if diff > 0:  # Only add valid time differences
                time_diffs.append(diff)
        except (ValueError, TypeError):
            continue
    
    if not time_diffs:
        return {"frequency": "Could not calculate posting frequency"}
    
    avg_diff = sum(time_diffs) / len(time_diffs)
    avg_days = avg_diff / (24 * 3600)  # Convert seconds to days
    
    if avg_days < 1:
        return {"frequency": f"Multiple posts per day (average {1/avg_days:.1f} posts/day)"}
    else:
        return {"frequency": f"Posts every {avg_days:.1f} days"}

def analyze_best_posting_times(posts):
    if not posts:
        return {}
    
    hours = []
    for post in posts:
        timestamp = post.get('timestamp')
        if timestamp:
            # Convert string timestamp to integer if it's a string
            if isinstance(timestamp, str):
                try:
                    timestamp = int(timestamp)
                except ValueError:
                    continue
            try:
                dt = datetime.fromtimestamp(timestamp)
                hours.append(dt.hour)
            except (ValueError, TypeError, OSError):
                continue
    
    if not hours:
        return {}
    
    hour_counts = Counter(hours)
    if hour_counts:
        best_hour = max(hour_counts.items(), key=lambda x: x[1])[0]
        return {
            "best_hour": best_hour,
            "hour_distribution": dict(hour_counts)
        }
    return {}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/instagram')
def instagram():
    return render_template('instagram.html')

@app.route('/facebook')
def facebook():
    return render_template('facebook.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            return jsonify({"success": False, "error": "Email and password are required"})

        # Authenticate user
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            return jsonify({"success": True, "message": "Login successful"})
        else:
            return jsonify({"success": False, "error": "Invalid email or password"})

    return render_template('loginpage.html', mode='login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if not name or not email or not password:
            return jsonify({"success": False, "error": "All fields are required for signup"})

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({"success": False, "error": "User already exists"})

        # Create new user
        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({"success": True, "message": "User registered successfully"})

    return render_template('loginpage.html', mode='signup')

@app.route('/scrape_instagram', methods=['POST'])
def scrape_instagram():
    try:
        username = request.form.get('username').strip()
        if not username:
            return jsonify({"success": False, "error": "Username is required"})

        print(f"\n=== Starting analysis for username: {username} ===")

        # First get basic profile info
        profile_input = {
            "usernames": [username],
            "resultsType": "userProfile",
        }

        profile_run = client.actor("zuzka/instagram-profile-scraper").call(run_input=profile_input)
        profile_results = []
        for item in client.dataset(profile_run["defaultDatasetId"]).iterate_items():
            profile_results.append(item)

        if not profile_results:
            return jsonify({"success": False, "error": "No profile data found"})

        print("Profile data fetched successfully")

        # Get posts data with more posts to ensure we get enough comments
        posts_input = {
            "usernames": [username],
            "resultsType": "posts",
            "resultsLimit": 10,  # Reduced to 10 most recent posts
            "addHighlights": False,
            "addStories": False
        }

        posts_run = client.actor("zuzka/instagram-profile-scraper").call(run_input=posts_input)
        posts_results = []
        for item in client.dataset(posts_run["defaultDatasetId"]).iterate_items():
            posts_results.append(item)

        print("Posts data fetched successfully")

        # Extract post URLs for comment scraping
        post_urls = []
        posts_data = []
        
        if posts_results and posts_results[0].get("latestPosts"):
            latest_posts = posts_results[0]["latestPosts"][:10]
            print(f"Found {len(latest_posts)} posts to analyze")
            
            for post in latest_posts:
                if post.get("url"):
                    post_urls.append(post.get("url"))
                    posts_data.append({
                        "url": post.get("url"),
                        "displayUrl": post.get("displayUrl"),
                        "caption": post.get("caption", ""),
                        "likesCount": int(post.get("likesCount", 0)),
                        "commentsCount": int(post.get("commentsCount", 0)),
                        "timestamp": post.get("timestamp"),
                        "type": post.get("type", "image"),
                    })

        print(f"Extracted {len(post_urls)} valid post URLs")

        # Get comments with increased limit
        if post_urls:
            comments_input = {
                "directUrls": post_urls[:5],  # Get comments from top 5 posts
                "resultsLimit": 100  # Increased limit to get more comments
            }

            print("Fetching comments...")
            comments_run = client.actor("apify/instagram-comment-scraper").call(run_input=comments_input)
            
            comments_results = []
            for item in client.dataset(comments_run["defaultDatasetId"]).iterate_items():
                comments_results.append(item)
            print(f"Fetched {len(comments_results)} comment results")

            # Match comments with posts
            for post in posts_data[:5]:
                post["comments"] = []
                for comment_data in comments_results:
                    if comment_data.get("postUrl") == post["url"]:
                        comments = comment_data.get("comments", [])
                        print(f"Found {len(comments)} comments for post {post['url']}")
                        post["comments"] = comments
                        break

        # Analyze comments sentiment
        all_comments = []
        for post in posts_data[:5]:
            all_comments.extend(post.get("comments", []))

        print(f"\n=== Processing {len(all_comments)} total comments ===")
        
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        
        for i, comment in enumerate(all_comments):
            text = comment.get("text", "").strip()
            if text:  # Only analyze non-empty comments
                sentiment = analyze_sentiment(text)
                sentiment_counts[sentiment] += 1
                print(f"Comment {i+1}: {text[:50]}... | Sentiment: {sentiment}")

        print("\n=== Final Sentiment Analysis ===")
        print(f"Positive comments: {sentiment_counts['positive']}")
        print(f"Neutral comments: {sentiment_counts['neutral']}")
        print(f"Negative comments: {sentiment_counts['negative']}")

        # Calculate analytics
        profile_info = profile_results[0]
        total_likes = sum(post.get("likesCount", 0) for post in posts_data)
        total_comments = sum(post.get("commentsCount", 0) for post in posts_data)
        avg_likes = total_likes / len(posts_data) if posts_data else 0
        avg_comments = total_comments / len(posts_data) if posts_data else 0

        # Calculate engagement metrics
        engagement_rates = []
        followers_count = int(profile_info.get("followersCount", 0))
        for post in posts_data:
            rate = calculate_engagement_rate(
                followers_count,
                int(post.get("likesCount", 0)),
                int(post.get("commentsCount", 0))
            )
            engagement_rates.append(rate)

        avg_engagement_rate = sum(engagement_rates) / len(engagement_rates) if engagement_rates else 0

        # Analyze posting patterns
        posting_frequency = analyze_posting_frequency(posts_data)
        posting_times = analyze_best_posting_times(posts_data)

        analytics = {
            "overview": {
                "total_posts": int(profile_info.get("postsCount", 0)),
                "total_followers": followers_count,
                "total_following": int(profile_info.get("followsCount", 0)),
                "avg_likes_per_post": round(avg_likes, 2),
                "avg_comments_per_post": round(avg_comments, 2),
                "avg_engagement_rate": round(avg_engagement_rate, 2)
            },
            "engagement": {
                "engagement_rate": round(avg_engagement_rate, 2),
                "engagement_quality": "High" if avg_engagement_rate > 5 else "Medium" if avg_engagement_rate > 2 else "Low"
            },
            "sentiment_analysis": sentiment_counts,
            "content_analysis": {
                "content_types": dict(Counter(post.get("type", "image") for post in posts_data)),
                "posting_frequency": posting_frequency,
                "best_posting_time": posting_times
            }
        }

        print("\n=== Analysis Complete ===")

        return jsonify({
            "success": True,
            "data": {
                "profile_info": {
                    "username": profile_info.get("username", ""),
                    "fullName": profile_info.get("fullName", ""),
                    "biography": profile_info.get("biography", ""),
                    "followersCount": followers_count,
                    "followsCount": int(profile_info.get("followsCount", 0)),
                    "postsCount": int(profile_info.get("postsCount", 0)),
                    "profilePicUrl": profile_info.get("profilePicUrl", ""),
                    "isVerified": profile_info.get("isVerified", False),
                    "isPrivate": profile_info.get("isPrivate", False),
                    "externalUrl": profile_info.get("externalUrl", "")
                },
                "posts": posts_data[:5],
                "analytics": analytics
            }
        })
    except Exception as e:
        print(f"\n=== Error occurred: {str(e)} ===")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)})

@app.route('/scrape_facebook', methods=['POST'])
def scrape_facebook():
    try:
        username = request.form.get('username').strip()
        if not username:
            return jsonify({"success": False, "error": "Username or profile URL is required"})
        
        print(f"\n=== Starting Facebook analysis for: {username} ===")

        # Extract username/url if provided with full URL
        if 'facebook.com' in username:
            username = username.split('facebook.com/')[-1].rstrip('/')
        
        # Get profile and posts data
        scrape_input = {
            "startUrls": [{
                "url": f"https://www.facebook.com/{username}"
            }],
            "resultsLimit": 10
        }

        print("Starting scrape with meta-scraper...")
        scrape_run = client.actor("apify/meta-scraper").call(run_input=scrape_input)
        
        results = []
        for item in client.dataset(scrape_run["defaultDatasetId"]).iterate_items():
            results.append(item)

        if not results:
            return jsonify({"success": False, "error": "No profile data found"})

        profile_info = results[0]
        posts_data = []
        total_reactions = 0
        total_comments = 0
        total_shares = 0

        # Process posts data
        for item in results:
            if 'posts' in item:
                for post in item['posts']:
                    post_data = {
                        "text": post.get("text", ""),
                        "imageUrl": post.get("imageUrl", ""),
                        "reactions": post.get("reactions", {}).get("total", 0),
                        "comments": post.get("commentsCount", 0),
                        "shares": post.get("sharesCount", 0),
                        "timestamp": post.get("publishedDate")
                    }
                    posts_data.append(post_data)
                    total_reactions += post_data["reactions"]
                    total_comments += post_data["comments"]
                    total_shares += post_data["shares"]

        # Calculate analytics
        avg_reactions = total_reactions / len(posts_data) if posts_data else 0
        avg_comments = total_comments / len(posts_data) if posts_data else 0
        avg_shares = total_shares / len(posts_data) if posts_data else 0

        followers_count = profile_info.get("followersCount", 0)
        engagement_rate = ((total_reactions + total_comments + total_shares) / (len(posts_data) * followers_count) * 100) if followers_count and posts_data else 0

        posting_frequency = analyze_posting_frequency(posts_data)

        analytics = {
            "engagement_rate": round(engagement_rate, 2),
            "avg_reactions": round(avg_reactions, 2),
            "avg_comments": round(avg_comments, 2),
            "avg_shares": round(avg_shares, 2),
            "posting_frequency": posting_frequency.get("frequency", "N/A")
        }

        print("\n=== Analysis Complete ===")

        return jsonify({
            "success": True,
            "data": {
                "profile_info": {
                    "username": profile_info.get("username", username),
                    "name": profile_info.get("name", ""),
                    "about": profile_info.get("about", ""),
                    "profilePicUrl": profile_info.get("profilePicUrl", ""),
                    "followersCount": followers_count,
                    "isVerified": profile_info.get("verified", False)
                },
                "posts": posts_data,
                "analytics": analytics
            }
        })

    except Exception as e:
        print(f"\n=== Error occurred: {str(e)} ===")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run(debug=True)