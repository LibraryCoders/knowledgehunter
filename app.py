from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
import yt_dlp
import re
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# All ISO 639-1 language codes (as supported by YouTube transcripts)
ALL_LANGUAGES = [
    'af', 'sq', 'am', 'ar', 'hy', 'az', 'eu', 'be', 'bn', 'bs', 'bg', 'my', 'ca', 'ceb', 'zh', 'zh-Hans', 'zh-Hant',
    'co', 'hr', 'cs', 'da', 'nl', 'en', 'eo', 'et', 'fi', 'fr', 'fy', 'gl', 'ka', 'de', 'el', 'gu', 'ht', 'ha',
    'haw', 'he', 'hi', 'hmn', 'hu', 'is', 'ig', 'id', 'ga', 'it', 'ja', 'jw', 'kn', 'kk', 'km', 'rw', 'ko', 'ku',
    'ky', 'lo', 'la', 'lv', 'lt', 'lb', 'mk', 'mg', 'ms', 'ml', 'mt', 'mi', 'mr', 'mn', 'ne', 'no', 'ny', 'or',
    'ps', 'fa', 'pl', 'pt', 'pa', 'ro', 'ru', 'sm', 'gd', 'sr', 'st', 'sn', 'sd', 'si', 'sk', 'sl', 'so', 'es',
    'su', 'sw', 'sv', 'tl', 'tg', 'ta', 'tt', 'te', 'th', 'tr', 'tk', 'uk', 'ur', 'ug', 'uz', 'vi', 'cy', 'xh',
    'yi', 'yo', 'zu'
]

def download_info(url):
    """Get basic video information using yt-dlp"""
    opts = {'skip_download': True, 'quiet': True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    # Regular expressions to match various YouTube URL formats using raw string
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    match = re.match(youtube_regex, url)
    if match:
        return match.group(6)
    return None

@app.route('/api/transcript', methods=['GET'])
def get_transcript():
    """API endpoint to get transcript from a YouTube URL"""
    url = request.args.get('url')
    
    if not url:
        return jsonify({
            'success': False,
            'error': 'Missing URL parameter'
        }), 400
    
    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({
            'success': False,
            'error': 'Invalid YouTube URL or couldn\'t extract video ID'
        }), 400
    
    try:
        # Get transcript using youtube_transcript_api
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get transcript in the original language first
            try:
                transcript = transcript_list.find_transcript(['en'])  # Default to English
            except:
                # If English not available, get any available transcript
                transcript = transcript_list.find_transcript([])
            
            transcript_parts = transcript.fetch()
            full_text = " ".join([part['text'] for part in transcript_parts])
        except TranscriptsDisabled:
            return jsonify({
                'success': False,
                'error': 'Transcripts are disabled for this video'
            }), 404
        except NoTranscriptFound:
            return jsonify({
                'success': False,
                'error': 'No transcript found for this video'
            }), 404
        except VideoUnavailable:
            return jsonify({
                'success': False,
                'error': 'The video is unavailable'
            }), 404
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error fetching transcript: {str(e)}'
            }), 500
        
        # Get video info for metadata - try/except to handle yt-dlp errors
        try:
            info = download_info(url)
            video_details = {
                'title': info.get('title', 'Unknown Title'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': str(info.get('duration', 0)),
                'views': str(info.get('view_count', 0)),
                'upload_date': info.get('upload_date', ''),
                'channel': info.get('channel', ''),
                'likes': str(info.get('like_count', 0))
            }
        except Exception as e:
            # Create a minimal video details object with info from the transcript
            video_details = {
                'title': f"Video {video_id}",
                'thumbnail': f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                'duration': "Unknown",
                'views': "Unknown",
                'upload_date': "Unknown",
                'channel': "Unknown",
                'likes': "Unknown"
            }
        
        if not full_text or full_text.strip() == '':
            return jsonify({
                'success': False,
                'error': 'Transcript is empty',
                'video': video_details
            }), 404
        
        return jsonify({
            'success': True,
            'video': video_details,
            'transcript': full_text
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/video-info', methods=['GET'])
def get_video_info():
    """API endpoint to get basic video information"""
    url = request.args.get('url')
    
    if not url:
        return jsonify({
            'success': False,
            'error': 'Missing URL parameter'
        }), 400
    
    try:
        info = download_info(url)
        
        return jsonify({
            'success': True,
            'video_id': info.get('id'),
            'title': info.get('title'),
            'thumbnail': info.get('thumbnail'),
            'duration': info.get('duration'),
            'channel': info.get('channel'),
            'upload_date': info.get('upload_date')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/video-data', methods=['GET'])
def get_video_data():
    """Unified API endpoint to get both video information and transcript in one request"""
    url = request.args.get('url')
    
    if not url:
        return jsonify({
            'success': False,
            'error': 'Missing URL parameter'
        }), 400
    
    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({
            'success': False,
            'error': 'Invalid YouTube URL or couldn\'t extract video ID'
        }), 400
    
    result = {
        'success': True,
        'video_id': video_id,
        'video_info': None,
        'transcript': None,
        'transcript_error': None
    }
    
    # Get video information using yt-dlp
    try:
        info = download_info(url)
        result['video_info'] = {
            'title': info.get('title'),
            'thumbnail': info.get('thumbnail'),
            'duration': info.get('duration'),
            'views': info.get('view_count'),
            'upload_date': info.get('upload_date'),
            'channel': info.get('channel'),
            'likes': info.get('like_count'),
            'description': info.get('description')
        }
    except Exception as e:
        result['success'] = False
        result['video_info_error'] = f"Error fetching video info: {str(e)}"
        # Create a minimal video details object from the video ID
        result['video_info'] = {
            'title': f"Video {video_id}",
            'thumbnail': f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        }
    
    # Get transcript using the specified approach
    try:
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=ALL_LANGUAGES)
        result['transcript'] = transcript_data
        
        # Also include a plain text version for convenience
        plain_text = "\n".join([f"{item['start']:.2f} - {(item['start'] + item['duration']):.2f}: {item['text']}" 
                              for item in transcript_data])
        result['transcript_text'] = plain_text
        
    except TranscriptsDisabled:
        result['transcript_error'] = "Transcripts are disabled for this video"
    except NoTranscriptFound:
        result['transcript_error'] = "No transcript found for this video in any supported language"
    except VideoUnavailable:
        result['transcript_error'] = "The video is unavailable"
    except Exception as e:
        result['transcript_error'] = f"Error fetching transcript: {str(e)}"
    
    # If both video info and transcript failed, mark as overall failure
    if (not result['video_info'] or 'video_info_error' in result) and 'transcript_error' in result:
        result['success'] = False
        result['error'] = "Failed to retrieve both video information and transcript"
    
    return jsonify(result)

@app.route('/', methods=['GET'])
def index():
    """Simple documentation page for the API"""
    return '''
    <html>
        <head>
            <title>YouTube Transcript API</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }
                pre { background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }
                code { background: #f5f5f5; padding: 2px 5px; border-radius: 3px; }
                h1, h2 { border-bottom: 1px solid #eee; padding-bottom: 10px; }
                .endpoint { margin-bottom: 30px; }
                .method { display: inline-block; background: #34a853; color: white; padding: 3px 8px; border-radius: 3px; }
                .url { font-family: monospace; margin-left: 10px; }
            </style>
        </head>        <body>
            <h1>YouTube Transcript API</h1>
            <p>This API allows you to extract transcripts and video details from YouTube videos using the official youtube-transcript-api library.</p>
            
            <h2>Endpoints</h2>
            
            <div class="endpoint">
                <h3><span class="method">GET</span><span class="url">/api/transcript?url={youtube_url}</span></h3>
                <p>Get the transcript and details of a YouTube video.</p>
                <p><strong>Parameters:</strong></p>
                <ul>
                    <li><code>url</code> (required): The YouTube video URL</li>
                </ul>
                <p><strong>Example Response:</strong></p>
                <pre>
{
  "success": true,
  "video": {
    "title": "Video Title",
    "thumbnail": "https://example.com/thumbnail.jpg",
    "duration": "10:30",
    "views": "1,234,567",
    "upload_date": "2023-01-15",
    "channel": "Channel Name",
    "likes": "12,345"
  },
  "transcript": "Full video transcript text..."
}
                </pre>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span><span class="url">/api/video-info?url={youtube_url}</span></h3>
                <p>Get basic information about a YouTube video.</p>
                <p><strong>Parameters:</strong></p>
                <ul>
                    <li><code>url</code> (required): The YouTube video URL</li>
                </ul>
                <p><strong>Example Response:</strong></p>
                <pre>
{
  "success": true,
  "video_id": "dQw4w9WgXcQ",
  "title": "Video Title",
  "thumbnail": "https://example.com/thumbnail.jpg",
  "duration": 630,
  "channel": "Channel Name",
  "upload_date": "20230115"
}
                </pre>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span><span class="url">/api/video-data?url={youtube_url}</span></h3>
                <p>Get both video information and transcript in a single API call.</p>
                <p><strong>Parameters:</strong></p>
                <ul>
                    <li><code>url</code> (required): The YouTube video URL</li>
                </ul>
                <p><strong>Example Response:</strong></p>
                <pre>
{
  "success": true,
  "video_id": "dQw4w9WgXcQ",
  "video_info": {
    "title": "Video Title",
    "thumbnail": "https://example.com/thumbnail.jpg",
    "duration": 630,
    "views": 12345678,
    "upload_date": "20230115",
    "channel": "Channel Name",
    "likes": 123456,
    "description": "Video description text..."
  },
  "transcript": [
    {
      "start": 0.0,
      "duration": 5.28,
      "text": "First line of transcript"
    },
    {
      "start": 5.28,
      "duration": 3.42,
      "text": "Second line of transcript"
    }
  ],
  "transcript_text": "0.00 - 5.28: First line of transcript\n5.28 - 8.70: Second line of transcript"
}
                </pre>
            </div>
            
            <h2>Error Responses</h2>
            <p>All endpoints return the following format for errors:</p>
            <pre>
{
  "success": false,
  "error": "Error message"
}
            </pre>
            
            <h2>Usage Example</h2>
            <p>Using cURL:</p>
            <pre>curl "https://your-vercel-app.vercel.app/api/transcript?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"</pre>
            
            <p>Using JavaScript:</p>
            <pre>
fetch('https://your-vercel-app.vercel.app/api/transcript?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ')
  .then(response => response.json())
  .then(data => console.log(data));
            </pre>
        </body>
    </html>
    '''

# Necessary for Vercel serverless functions
def handler(environ, start_response):
    return app.wsgi_app(environ, start_response)

# Simple export for Vercel serverless
app.debug = False
application = app

# For local development 
if __name__ == '__main__':
    app.run(debug=True)
