#!/usr/bin/env python3
"""
Analyze All Videos Script
Automatically processes all videos with AI analysis
"""

import json
from video_frame_extractor import WebVideoAnalyzer

def main():
    print("🚀 Starting batch AI analysis of all videos...")
    
    # Video URLs from the web player
    videos = [
        {
            "title": "Medical Content",
            "src": "https://videodata3.s3.us-east-2.amazonaws.com/Medical+Content.mp4"
        },
        {
            "title": "Medical Training Day", 
            "src": "https://videodata3.s3.us-east-2.amazonaws.com/Medical+Training+Day.mp4"
        },
        {
            "title": "Clip 04 Web",
            "src": "https://videodata3.s3.us-east-2.amazonaws.com/clip_04_web.mp4"
        },
        {
            "title": "Clip 01 Final",
            "src": "https://videodata3.s3.us-east-2.amazonaws.com/clip_01_final.mkv"
        },
        {
            "title": "Bike Footage",
            "src": "https://videodata3.s3.us-east-2.amazonaws.com/bike_footage.mp4"
        }
    ]
    
    analyzer = WebVideoAnalyzer()
    all_video_analyses = {}
    
    for i, video in enumerate(videos):
        print(f"\n{'='*60}")
        print(f"📹 Processing video {i+1}/{len(videos)}: {video['title']}")
        print(f"{'='*60}")
        
        try:
            # Analyze video with timestamps at 15, 45, 75 seconds
            analyses = analyzer.analyze_video_url(video['src'], [15, 45, 75])
            
            if analyses:
                all_video_analyses[video['title']] = analyses
                print(f"✅ Successfully analyzed {video['title']}: {len(analyses)} annotations")
            else:
                print(f"❌ Failed to analyze {video['title']}")
                
        except Exception as e:
            print(f"❌ Error analyzing {video['title']}: {e}")
    
    # Save combined results
    if all_video_analyses:
        # Save detailed JSON
        with open('all_videos_analysis.json', 'w') as f:
            json.dump(all_video_analyses, f, indent=2)
        
        # Generate web-ready annotations for each video
        web_annotations_by_video = {}
        
        for video_title, analyses in all_video_analyses.items():
            web_annotations = []
            for analysis in analyses:
                web_annotation = {
                    "time": analysis['timestamp_formatted'],
                    "timestamp": analysis['timestamp'],
                    "text": f"🧠 {analysis.get('scene_description', 'AI Analysis')}",
                    "confidence": f"Confidence: {int(analysis.get('confidence_score', 0.85) * 100)}%",
                    "objects": analysis.get('objects', []),
                    "professional_assessment": analysis.get('professional_assessment', ''),
                    "x": 0.5,
                    "y": 0.4
                }
                web_annotations.append(web_annotation)
            web_annotations_by_video[video_title] = web_annotations
        
        # Save web format
        with open('all_videos_annotations.js', 'w') as f:
            f.write(f"const allVideoAnnotations = {json.dumps(web_annotations_by_video, indent=2)};")
        
        print(f"\n🎉 Batch analysis complete!")
        print(f"📊 Analyzed {len(all_video_analyses)} videos")
        print(f"💾 Results saved to:")
        print(f"   - all_videos_analysis.json (detailed)")
        print(f"   - all_videos_annotations.js (web format)")
        
        # Print summary
        print(f"\n📈 Analysis Summary:")
        for video_title, analyses in all_video_analyses.items():
            total_objects = sum(len(a.get('objects', [])) for a in analyses)
            print(f"   📹 {video_title}: {len(analyses)} annotations, {total_objects} total objects detected")
            
    else:
        print("\n❌ No videos were successfully analyzed")

if __name__ == "__main__":
    main() 