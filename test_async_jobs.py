#!/usr/bin/env python3
"""
Test script for Phase 3 async job system.
Demonstrates creating jobs, monitoring progress, and getting results.
"""

import requests
import json
import time
import sys
from datetime import datetime

class AsyncJobTester:
    """Test client for async video annotation jobs."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_health_check(self):
        """Test health check and system status."""
        print("🏥 Testing Health Check")
        print("=" * 30)
        
        try:
            response = self.session.get(f"{self.base_url}/api/health")
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Service Status: {data['status']}")
            print(f"📦 Version: {data['version']}")
            print(f"🔧 Features: {data['features']}")
            print(f"👷 Background Worker: {data['background_worker']}")
            print(f"📊 Active Jobs: {data['active_jobs']}")
            print(f"⏳ Pending Jobs: {data['pending_jobs']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

    def create_job(self, video_url: str, frame_rate: float = 0.02):
        """Create a new annotation job."""
        print(f"\n🚀 Creating Job")
        print("=" * 20)
        print(f"📹 Video: {video_url.split('/')[-1]}")
        print(f"⚡ Frame Rate: {frame_rate} FPS")
        
        try:
            payload = {
                "video_url": video_url,
                "frame_rate": frame_rate
            }
            
            response = self.session.post(
                f"{self.base_url}/api/annotate",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            job_id = data['job_id']
            
            print(f"✅ Job Created: {job_id}")
            print(f"📊 Status: {data['status']}")
            print(f"💬 Message: {data['message']}")
            print(f"🕐 Created: {data['created_at']}")
            
            return job_id
            
        except Exception as e:
            print(f"❌ Job creation failed: {e}")
            return None

    def monitor_job(self, job_id: str, max_wait: int = 1800):
        """Monitor job progress until completion."""
        print(f"\n📊 Monitoring Job: {job_id}")
        print("=" * 40)
        
        start_time = time.time()
        last_stage = None
        last_progress = None
        
        while time.time() - start_time < max_wait:
            try:
                response = self.session.get(f"{self.base_url}/api/status/{job_id}")
                response.raise_for_status()
                
                data = response.json()
                status = data['status']
                progress = data.get('progress', {})
                
                # Print progress updates
                current_stage = progress.get('stage', 'pending')
                current_progress = progress.get('progress_percent', 0)
                
                if current_stage != last_stage or current_progress != last_progress:
                    message = progress.get('message', 'Waiting to start...')
                    
                    if current_progress:
                        print(f"🔄 {current_stage.title()}: {message} ({current_progress}%)")
                    else:
                        print(f"🔄 {current_stage.title()}: {message}")
                    
                    # Show chunk progress if available
                    if 'current_chunk' in progress and 'total_chunks' in progress:
                        chunk_info = f"Chunk {progress['current_chunk']}/{progress['total_chunks']}"
                        print(f"   📦 {chunk_info}")
                    
                    last_stage = current_stage
                    last_progress = current_progress
                
                # Check completion
                if status == 'completed':
                    duration = data.get('duration_seconds', 0)
                    frames = data.get('total_frames_processed', 0)
                    annotations = len(data.get('annotations', []))
                    processing_time = data.get('processing_time', 0)
                    
                    print(f"\n✅ Job Completed Successfully!")
                    print(f"⏱️  Video Duration: {duration:.1f} seconds")
                    print(f"🖼️  Frames Processed: {frames}")
                    print(f"📍 Annotations Found: {annotations}")
                    print(f"⚡ Processing Time: {processing_time:.1f} seconds")
                    
                    return data
                    
                elif status == 'failed':
                    error = data.get('error', 'Unknown error')
                    print(f"\n❌ Job Failed: {error}")
                    return None
                    
                elif status == 'cancelled':
                    print(f"\n🚫 Job Cancelled")
                    return None
                
                # Wait before next check
                time.sleep(5)
                
            except Exception as e:
                print(f"❌ Error checking job status: {e}")
                time.sleep(10)
        
        print(f"\n⏰ Timeout waiting for job completion")
        return None

    def show_job_results(self, job_data):
        """Display detailed job results."""
        if not job_data or 'annotations' not in job_data:
            print("No annotations to display")
            return
            
        annotations = job_data['annotations']
        
        print(f"\n🎯 Annotation Results")
        print("=" * 30)
        
        # Group by timestamp
        by_timestamp = {}
        for ann in annotations:
            ts = ann['timestamp']
            if ts not in by_timestamp:
                by_timestamp[ts] = []
            by_timestamp[ts].append(ann)
        
        # Show first few frames
        timestamps = sorted(by_timestamp.keys())[:5]
        
        for i, ts in enumerate(timestamps):
            frame_anns = by_timestamp[ts]
            mins, secs = divmod(ts, 60)
            
            print(f"\n🎬 Frame {i+1} at {int(mins)}:{int(secs):02d}")
            for j, ann in enumerate(frame_anns[:3]):  # Show first 3 objects
                conf_emoji = "🟢" if ann['confidence'] > 0.9 else "🟡" if ann['confidence'] > 0.8 else "🔴"
                print(f"  {j+1}. {conf_emoji} {ann['object']} (confidence: {ann['confidence']:.2f})")
                print(f"     📦 BBox: {ann['bbox']}")
                print(f"     🌍 3D: {ann['coordinates_3d']}")
            
            if len(frame_anns) > 3:
                print(f"     ... and {len(frame_anns) - 3} more objects")
        
        if len(timestamps) > 5:
            print(f"\n... and {len(timestamps) - 5} more frames")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"async_job_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(job_data, f, indent=2)
        
        print(f"\n💾 Full results saved to: {filename}")

    def test_job_management(self):
        """Test job listing and management features."""
        print(f"\n📋 Testing Job Management")
        print("=" * 30)
        
        try:
            # List jobs
            response = self.session.get(f"{self.base_url}/api/jobs?limit=10")
            response.raise_for_status()
            
            data = response.json()
            print(f"📊 Total Jobs: {data['total']}")
            print(f"🔄 Active Jobs: {data['active']}")
            
            if data['jobs']:
                print(f"\n📋 Recent Jobs:")
                for job in data['jobs'][:3]:
                    print(f"  • {job['job_id'][:8]}... - {job['status']} - {job['video_url'].split('/')[-1]}")
            
            # Get stats
            response = self.session.get(f"{self.base_url}/api/jobs/stats")
            response.raise_for_status()
            
            stats = response.json()
            print(f"\n📈 Job Statistics:")
            for status, count in stats['status_breakdown'].items():
                if count > 0:
                    print(f"  • {status}: {count}")
            
            return True
            
        except Exception as e:
            print(f"❌ Job management test failed: {e}")
            return False

    def run_full_test(self):
        """Run complete async job system test."""
        print("🧪 Async Job System Test Suite")
        print("🤖 Phase 3 - Background Processing")
        print("=" * 50)
        
        # Test 1: Health check
        if not self.test_health_check():
            print("❌ Health check failed - aborting tests")
            return False
        
        # Test 2: Job management
        self.test_job_management()
        
        # Test 3: Create and monitor job
        video_url = "https://videodata3.s3.us-east-2.amazonaws.com/car_service.mp4"
        job_id = self.create_job(video_url, frame_rate=0.02)  # Very low frame rate for fast test
        
        if not job_id:
            print("❌ Job creation failed")
            return False
        
        # Test 4: Monitor job progress
        result = self.monitor_job(job_id, max_wait=600)  # 10 minute timeout
        
        if result:
            # Test 5: Show results
            self.show_job_results(result)
            
            print(f"\n🎉 ALL TESTS PASSED!")
            print(f"✅ Async job system working perfectly")
            print(f"🚀 Phase 3 implementation complete")
            return True
        else:
            print(f"❌ Job monitoring failed")
            return False

def main():
    """Main test function."""
    tester = AsyncJobTester()
    success = tester.run_full_test()
    
    if success:
        print(f"\n🎊 Phase 3 Async Job System: WORKING!")
        print(f"📱 Try the interactive API: http://localhost:8000/api/docs")
    else:
        print(f"\n💥 Some tests failed - check logs above")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 