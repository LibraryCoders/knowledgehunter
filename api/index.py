from flask import Flask, request, jsonify
from apify_client import ApifyClient
from flask_cors import CORS
from vercel_proxy import VercelProxy  # Required for Vercel support

app = Flask(__name__)
CORS(app)
VercelProxy(app)  # 👈 Add this line

apify_client = ApifyClient("apify_api_ByzOzUbcyNjiI163g5rKzHxWbbtDQs0mYnDa")

@app.route('/transcript', methods=['POST'])
def get_transcript():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing YouTube video URL'}), 400

    try:
        video_url = data['url']
        run_input = {"urls": [video_url]}
        run = apify_client.actor("fastcrawler/youtube-transcript-extractor-video-text-3-1k-pay-per-result").call(run_input=run_input)
        dataset_id = run["defaultDatasetId"]
        results = list(apify_client.dataset(dataset_id).iterate_items())

        return jsonify({
            "dataset_id": dataset_id,
            "transcript": results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
