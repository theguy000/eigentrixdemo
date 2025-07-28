#!/usr/bin/env python3
"""
Test script for Video Annotation Backend
Tests the /annotate endpoint with real video URLs
"""

import requests
import json
import time
import sys

def test_health_check(base_url):
    """Test the health check endpoints"""
    print("🏥 Testing health check...")
    
    try:
        response = requests.get(f"{base_url}/")
        assert response.status_code == 200
        print("✅ Root endpoint OK")
        
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200
        health_data = response.json()
        print(f"✅ Health check OK: {health_data}")
        
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_annotate_endpoint(base_url, video_url):
    """Test the /annotate endpoint"""
    print(f"🎬 Testing annotation for: {video_url}")
    
    payload = {
        "video_url": video_url
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{base_url}/api/annotate",
            json=payload,
            timeout=300  # 5 minute timeout
        )
        
        if response.status_code != 200:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        result = response.json()
        processing_time = time.time() - start_time
        
        print(f"✅ Annotation completed in {processing_time:.2f}s")
        print(f"📊 Results:")
        print(f"   - Status: {result['status']}")
        print(f"   - Duration: {result['duration_seconds']:.2f}s")
        print(f"   - Frames processed: {result['total_frames_processed']}")
        print(f"   - Annotations: {len(result['annotations'])}")
        print(f"   - Processing time: {result['processing_time_seconds']:.2f}s")
        
        # Show sample annotations
        if result['annotations']:
            print(f"📝 Sample annotations:")
            for i, ann in enumerate(result['annotations'][:3]):  # Show first 3
                print(f"   {i+1}. {ann['timestamp']} - {ann['object']} @ {ann['bbox']}")
        
        return True
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out (>5 minutes)")
        return False
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    """Run tests against the backend"""
    base_url = "http://localhost:8000"
    
    print("🧪 Video Annotation Backend Test Suite")
    print("=" * 50)
    
    # Check if server is running
    try:
        requests.get(base_url, timeout=5)
    except:
        print(f"❌ Server not running at {base_url}")
        print("💡 Start server with: python run_server.py")
        sys.exit(1)
    
    # Test health check
    if not test_health_check(base_url):
        sys.exit(1)
    
    print()
    
    # Test video URLs
    test_videos = [
        "https://videodata3.s3.us-east-2.amazonaws.com/Medical+Content.mp4",
        "https://videodata3.s3.us-east-2.amazonaws.com/Medical+Training+Day.mp4"
    ]
    
    for video_url in test_videos:
        print("-" * 50)
        success = test_annotate_endpoint(base_url, video_url)
        if not success:
            print(f"❌ Test failed for {video_url}")
        else:
            print(f"✅ Test passed for {video_url}")
        print()
    
    print("🎉 Test suite completed!")

if __name__ == "__main__":
    main() 