#!/usr/bin/env python3
"""
Quick test script for video annotation API.
Handles longer processing times and provides real-time feedback.
"""

import requests
import json
import time
import sys

def test_video_annotation(video_url, frame_rate=0.1, timeout=600):
    """Test video annotation with progress tracking."""
    
    print(f"🎬 Testing video: {video_url.split('/')[-1]}")
    print(f"🎯 Frame rate: {frame_rate} FPS")
    print(f"⏱️  Timeout: {timeout}s")
    print("🚀 Starting annotation...")
    
    payload = {
        "video_url": video_url,
        "frame_rate": frame_rate
    }
    
    start_time = time.time()
    
    try:
        print("📡 Sending request...")
        response = requests.post(
            "http://localhost:8000/api/annotate",
            json=payload,
            timeout=timeout
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n✅ SUCCESS in {elapsed:.1f}s")
            print(f"📊 Status: {data['status']}")
            print(f"⏱️  Video Duration: {data['duration_seconds']:.1f}s")
            print(f"🖼️  Frames Processed: {data['total_frames_processed']}")
            print(f"📍 Annotations Found: {len(data['annotations'])}")
            print(f"⚡ Processing Time: {data['processing_time_seconds']:.1f}s")
            
            if data['annotations']:
                print(f"\n🎯 Sample Annotation:")
                sample = data['annotations'][0]
                print(f"   Time: {sample['timestamp']}s")
                print(f"   Object: {sample['object']}")
                print(f"   Bbox: {sample['bbox']}")
                print(f"   3D: {sample['coordinates_3d']}")
                print(f"   Confidence: {sample['confidence']}")
                
                # Save full results
                filename = f"results_{video_url.split('/')[-1].replace('.mp4', '')}_{int(time.time())}.json"
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"\n💾 Full results saved to: {filename}")
            
            return True
            
        else:
            print(f"❌ ERROR: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"⏰ TIMEOUT after {elapsed:.1f}s")
        print("   (Processing is still running in background)")
        return False
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ FAILED after {elapsed:.1f}s: {e}")
        return False

def main():
    print("🎥 Video Annotation API Tester")
    print("=" * 40)
    
    # Test 1: Car service video (very low frame rate)
    print("\n🚗 Test 1: Car Service Video")
    test_video_annotation(
        "https://videodata3.s3.us-east-2.amazonaws.com/car_service.mp4",
        frame_rate=0.1,  # Very low frame rate
        timeout=300
    )
    
    print("\n" + "="*40)
    
    # Test 2: Medical video (reference)
    print("\n🏥 Test 2: Medical Video")
    test_video_annotation(
        "https://videodata3.s3.us-east-2.amazonaws.com/Medical+Content.mp4",
        frame_rate=0.1,  # Very low frame rate
        timeout=300
    )

if __name__ == "__main__":
    main() 