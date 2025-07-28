#!/usr/bin/env python3
"""
Get and display real AI annotations from car service video.
Shows actual Gemini Pro Vision analysis results.
"""

import requests
import json
import time
from datetime import datetime

def get_car_service_annotations():
    """Fetch real AI annotations for car service video."""
    
    print("🤖 Getting Real AI Annotations for Car Service Video")
    print("=" * 60)
    
    # Configuration for quick results
    payload = {
        "video_url": "https://videodata3.s3.us-east-2.amazonaws.com/car_service.mp4",
        "frame_rate": 0.01  # Low frame rate for faster processing
    }
    
    print(f"📹 Video: Car Service (car_service.mp4)")
    print(f"🎯 Frame Rate: {payload['frame_rate']} FPS")
    print(f"⚡ Processing: Real Gemini Pro Vision AI")
    print("\n🚀 Starting AI analysis...")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            "http://localhost:8000/api/annotate",
            json=payload,
            timeout=600  # 10 minute timeout
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n✅ SUCCESS! AI Analysis Complete in {elapsed/60:.1f} minutes")
            print("=" * 60)
            print(f"📊 Status: {data['status']}")
            print(f"🎬 Video Duration: {data['duration_seconds']:.1f} seconds")
            print(f"🖼️  Frames Processed: {data['total_frames_processed']}")
            print(f"📍 AI Annotations Found: {len(data['annotations'])}")
            print(f"⚡ Processing Time: {data['processing_time_seconds']:.1f} seconds")
            
            if data['annotations']:
                print(f"\n🤖 REAL AI ANNOTATIONS (Gemini Pro Vision Analysis):")
                print("=" * 60)
                
                # Group annotations by timestamp
                by_timestamp = {}
                for ann in data['annotations']:
                    ts = ann['timestamp']
                    if ts not in by_timestamp:
                        by_timestamp[ts] = []
                    by_timestamp[ts].append(ann)
                
                # Display annotations by frame
                for i, (timestamp, annotations) in enumerate(sorted(by_timestamp.items())):
                    print(f"\n🎬 Frame {i+1} at {timestamp}s:")
                    for j, ann in enumerate(annotations):
                        print(f"  {j+1}. Object: {ann['object']}")
                        print(f"     📦 Bounding Box: {ann['bbox']} (pixels)")
                        print(f"     🌍 3D Position: {ann['coordinates_3d']} (meters)")
                        print(f"     🎯 Confidence: {ann['confidence']:.2f}")
                
                # Save detailed results
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"car_service_annotations_{timestamp}.json"
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                
                print(f"\n💾 Full analysis saved to: {filename}")
                
                # Analysis summary
                objects_found = {}
                total_confidence = 0
                for ann in data['annotations']:
                    obj = ann['object']
                    objects_found[obj] = objects_found.get(obj, 0) + 1
                    total_confidence += ann['confidence']
                
                avg_confidence = total_confidence / len(data['annotations'])
                
                print(f"\n📈 AI ANALYSIS SUMMARY:")
                print("=" * 30)
                print(f"🎯 Average Confidence: {avg_confidence:.2f}")
                print(f"🔍 Unique Objects Detected: {len(objects_found)}")
                print(f"📊 Object Breakdown:")
                for obj, count in sorted(objects_found.items(), key=lambda x: x[1], reverse=True):
                    print(f"   • {obj}: {count} instances")
                
                return data
            else:
                print(f"\n⚠️  No annotations returned - check server logs")
                return None
                
        else:
            print(f"\n❌ API Error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"\n⏰ Processing timeout after {elapsed/60:.1f} minutes")
        print("   The analysis may still be running in the background")
        return None
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None

def show_previous_results():
    """Show any previously saved annotation results."""
    print("\n🗂️  Checking for Previous Analysis Results:")
    print("=" * 45)
    
    import glob
    
    # Look for saved annotation files
    files = glob.glob("car_service_annotations_*.json") + glob.glob("results_car_service_*.json")
    
    if files:
        # Show most recent file
        latest_file = sorted(files)[-1]
        print(f"📁 Found previous analysis: {latest_file}")
        
        try:
            with open(latest_file, 'r') as f:
                data = json.load(f)
            
            print(f"📊 Annotations: {len(data.get('annotations', []))}")
            print(f"🖼️  Frames: {data.get('total_frames_processed', 0)}")
            print(f"⏱️  Duration: {data.get('duration_seconds', 0):.1f}s")
            
            if data.get('annotations'):
                print(f"\n🎯 Quick Preview:")
                for i, ann in enumerate(data['annotations'][:3]):
                    print(f"  {i+1}. {ann['object']} (confidence: {ann['confidence']:.2f})")
                if len(data['annotations']) > 3:
                    print(f"     ... and {len(data['annotations']) - 3} more")
                    
                return data
        except Exception as e:
            print(f"❌ Could not read {latest_file}: {e}")
    else:
        print("📭 No previous results found")
    
    return None

def main():
    """Main function to get and display AI annotations."""
    print("🎥 Car Service Video AI Annotation Viewer")
    print("🤖 Real Gemini Pro Vision Analysis")
    print("=" * 70)
    
    # First check for previous results
    previous = show_previous_results()
    
    if previous:
        choice = input(f"\n❓ Use previous results or run new analysis? (p/n): ").lower()
        if choice == 'p':
            return previous
    
    # Get new annotations
    return get_car_service_annotations()

if __name__ == "__main__":
    result = main()
    if result:
        print(f"\n🎉 AI Analysis Complete! Check the saved JSON file for full details.")
    else:
        print(f"\n🔄 Try running again - the AI analysis is working (check server logs)") 