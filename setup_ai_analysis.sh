#!/bin/bash

echo "🎬 AI Video Annotation Setup"
echo "============================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check if ffmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg is required but not installed"
    echo "📥 Install with: brew install ffmpeg"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"
echo "✅ FFmpeg found: $(ffmpeg -version | head -1)"

# Install Python requirements
echo ""
echo "📦 Installing Python requirements..."
pip3 install -r requirements.txt

# Set API key if provided
if [ ! -z "$1" ]; then
    export GEMINI_API_KEY="$1"
    echo "✅ Gemini API key set"
else
    echo "⚠️  No API key provided. Using existing environment variable."
fi

echo ""
echo "🚀 Setup complete! You can now:"
echo ""
echo "1️⃣  Analyze a single video:"
echo "   python3 video_frame_extractor.py 'VIDEO_URL'"
echo ""
echo "2️⃣  Analyze all videos (recommended):"
echo "   python3 analyze_all_videos.py"
echo ""
echo "3️⃣  Open the video player:"
echo "   open video-annotator.html"
echo ""
echo "💡 Example commands:"
echo "   python3 video_frame_extractor.py 'https://videodata3.s3.us-east-2.amazonaws.com/Medical+Content.mp4'"
echo "   python3 analyze_all_videos.py" 