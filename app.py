from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretmre'


@app.route('/')
def index():
    flash('Welcome to the Flask App', 'info')
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/loginpage')
def login():
    return render_template('loginpage.html')
  
@app.route('/registration')
def registration():
    return render_template("registration.html")  

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
    @app.route('/instagram')
def instagram():
    return render_template('instagram.html')

@app.route('/facebook')
def facebook():
    return render_template('facebook.html')

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
        return jsonify({"success": False, "error": str(e)})