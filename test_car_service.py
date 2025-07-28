#!/usr/bin/env python3
"""
Quick test for Car Service video annotation.
Tests both frontend integration and backend API.
"""

import requests
import json
import time

def test_car_service_video():
    """Test car service video annotation with minimal processing."""
    
    print("🚗 Testing Car Service Video Integration")
    print("=" * 50)
    
    # Test configuration
    video_url = "https://videodata3.s3.us-east-2.amazonaws.com/car_service.mp4"
    frame_rate = 0.005  # Very low frame rate for quick test
    
    print(f"📹 Video: {video_url.split('/')[-1]}")
    print(f"⚡ Frame Rate: {frame_rate} FPS (ultra-low for quick test)")
    print(f"🎯 Expected: ~1-2 frames total")
    print()
    
    payload = {
        "video_url": video_url,
        "frame_rate": frame_rate
    }
    
    print("🚀 Starting annotation test...")
    start_time = time.time()
    
    try:
        response = requests.post(
            "http://localhost:8000/api/annotate",
            json=payload,
            timeout=120  # 2 minute timeout
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n✅ SUCCESS in {elapsed:.1f}s")
            print(f"📊 Status: {data['status']}")
            print(f"⏱️  Duration: {data['duration_seconds']:.1f}s")
            print(f"🖼️  Frames: {data['total_frames_processed']}")
            print(f"📍 Annotations: {len(data['annotations'])}")
            print(f"⚡ Processing: {data['processing_time_seconds']:.1f}s")
            
            if data['annotations']:
                print(f"\n🎯 Sample Annotations:")
                for i, ann in enumerate(data['annotations'][:3]):
                    print(f"  {i+1}. {ann['object']} at {ann['timestamp']}s (confidence: {ann['confidence']})")
                
                print(f"\n✅ Car Service Video API Integration WORKING!")
                return True
            else:
                print(f"\n⚠️  No annotations found - check Gemini quota")
                return False
                
        else:
            print(f"\n❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"\n⏰ Timeout after {elapsed:.1f}s - processing might still be running")
        return False
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

def test_frontend_integration():
    """Test that frontend has car service video."""
    print("\n🎬 Testing Frontend Integration")
    print("=" * 30)
    
    try:
        with open('video-annotator.html', 'r') as f:
            content = f.read()
        
        tests = [
            ("Car Service in navigation", '"Car Service"' in content),
            ("Car service URL", 'car_service.mp4' in content),
            ("6 videos total", '"1 / 6"' in content),
            ("Keyboard shortcut 6", "'6'" in content and "key <= '6'" in content)
        ]
        
        all_passed = True
        for test_name, result in tests:
            status = "✅" if result else "❌"
            print(f"{status} {test_name}")
            if not result:
                all_passed = False
        
        print(f"\n{'✅ Frontend Integration WORKING!' if all_passed else '❌ Frontend Issues Found'}")
        return all_passed
        
    except Exception as e:
        print(f"❌ Could not test frontend: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Car Service Video Complete Test Suite")
    print("=" * 60)
    
    # Test 1: Frontend
    frontend_ok = test_frontend_integration()
    
    # Test 2: Backend API
    backend_ok = test_car_service_video()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"🎬 Frontend Integration: {'✅ PASS' if frontend_ok else '❌ FAIL'}")
    print(f"🚀 Backend API: {'✅ PASS' if backend_ok else '❌ FAIL'}")
    
    if frontend_ok and backend_ok:
        print(f"\n🎉 ALL TESTS PASSED! Car Service Video Integration Complete!")
        print(f"📹 Frontend: 6 videos including Car Service")
        print(f"🤖 Backend: Real Gemini AI analysis working")
        print(f"🔗 Full Integration: Working end-to-end")
    else:
        print(f"\n⚠️  Some tests failed - check logs above")
    
    return frontend_ok and backend_ok

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 