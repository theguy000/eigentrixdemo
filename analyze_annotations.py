#!/usr/bin/env python3
"""
Advanced AI annotation analysis tool.
Explore Gemini Pro Vision results in detail.
"""

import json
import sys
from collections import defaultdict

def load_latest_annotations():
    """Load the most recent annotation file."""
    import glob
    files = glob.glob("car_service_annotations_*.json")
    if not files:
        print("❌ No annotation files found. Run get_annotations.py first.")
        return None
    
    latest = sorted(files)[-1]
    print(f"📁 Loading: {latest}")
    
    with open(latest, 'r') as f:
        return json.load(f)

def analyze_by_time(data):
    """Analyze annotations by time progression."""
    print("\n🕒 TIME-BASED ANALYSIS")
    print("=" * 40)
    
    annotations = data['annotations']
    by_time = defaultdict(list)
    
    for ann in annotations:
        timestamp = ann['timestamp']
        by_time[timestamp].append(ann)
    
    for timestamp in sorted(by_time.keys()):
        time_anns = by_time[timestamp]
        mins, secs = divmod(timestamp, 60)
        print(f"\n⏰ {int(mins)}:{int(secs):02d} - {len(time_anns)} objects:")
        
        for ann in time_anns:
            conf_bar = "🟢" if ann['confidence'] > 0.9 else "🟡" if ann['confidence'] > 0.8 else "🔴"
            print(f"   {conf_bar} {ann['object']} ({ann['confidence']:.2f})")

def analyze_by_confidence(data):
    """Analyze annotations by confidence levels."""
    print("\n🎯 CONFIDENCE ANALYSIS")
    print("=" * 30)
    
    annotations = data['annotations']
    high_conf = [a for a in annotations if a['confidence'] >= 0.9]
    med_conf = [a for a in annotations if 0.8 <= a['confidence'] < 0.9]
    low_conf = [a for a in annotations if a['confidence'] < 0.8]
    
    print(f"🟢 High Confidence (≥90%): {len(high_conf)} objects")
    print(f"🟡 Medium Confidence (80-89%): {len(med_conf)} objects")
    print(f"🔴 Low Confidence (<80%): {len(low_conf)} objects")
    
    if high_conf:
        print(f"\n🏆 Most Confident Detections:")
        top_conf = sorted(high_conf, key=lambda x: x['confidence'], reverse=True)[:5]
        for i, ann in enumerate(top_conf, 1):
            print(f"   {i}. {ann['object']} at {ann['timestamp']}s ({ann['confidence']:.2f})")

def analyze_spatial_distribution(data):
    """Analyze 3D spatial distribution of objects."""
    print("\n🌍 3D SPATIAL ANALYSIS")
    print("=" * 30)
    
    annotations = data['annotations']
    
    # Analyze depth (z-coordinate)
    depths = [ann['coordinates_3d'][2] for ann in annotations]
    avg_depth = sum(depths) / len(depths)
    min_depth, max_depth = min(depths), max(depths)
    
    print(f"📏 Depth Range: {min_depth:.1f}m to {max_depth:.1f}m")
    print(f"📐 Average Depth: {avg_depth:.1f}m")
    
    # Categorize by distance
    close = [a for a in annotations if a['coordinates_3d'][2] <= 1.0]
    medium = [a for a in annotations if 1.0 < a['coordinates_3d'][2] <= 3.0]
    far = [a for a in annotations if a['coordinates_3d'][2] > 3.0]
    
    print(f"\n🔍 Distance Distribution:")
    print(f"   Near (≤1m): {len(close)} objects")
    print(f"   Medium (1-3m): {len(medium)} objects") 
    print(f"   Far (>3m): {len(far)} objects")

def analyze_object_relationships(data):
    """Analyze relationships between detected objects."""
    print("\n🔗 OBJECT RELATIONSHIP ANALYSIS")
    print("=" * 40)
    
    annotations = data['annotations']
    by_frame = defaultdict(list)
    
    for ann in annotations:
        by_frame[ann['timestamp']].append(ann['object'])
    
    print(f"📊 Co-occurrence Patterns:")
    
    # Find common object combinations
    combinations = defaultdict(int)
    for frame_objects in by_frame.values():
        if len(frame_objects) > 1:
            for i, obj1 in enumerate(frame_objects):
                for obj2 in frame_objects[i+1:]:
                    combo = tuple(sorted([obj1, obj2]))
                    combinations[combo] += 1
    
    top_combos = sorted(combinations.items(), key=lambda x: x[1], reverse=True)[:5]
    for combo, count in top_combos:
        print(f"   • {combo[0]} + {combo[1]}: {count} times")

def generate_timeline_summary(data):
    """Generate a timeline summary of the video."""
    print("\n📺 VIDEO TIMELINE SUMMARY")
    print("=" * 35)
    
    annotations = data['annotations']
    duration = data['duration_seconds']
    
    # Divide into segments
    segment_duration = duration / 4  # 4 segments
    segments = [[] for _ in range(4)]
    
    for ann in annotations:
        segment = min(3, int(ann['timestamp'] // segment_duration))
        segments[segment].append(ann)
    
    segment_names = ["Opening", "Early Middle", "Late Middle", "Ending"]
    
    for i, (name, segment_anns) in enumerate(zip(segment_names, segments)):
        start_time = i * segment_duration
        end_time = min((i + 1) * segment_duration, duration)
        
        print(f"\n🎬 {name} ({start_time/60:.1f}-{end_time/60:.1f} min):")
        
        if segment_anns:
            objects = [ann['object'] for ann in segment_anns]
            unique_objects = list(set(objects))
            print(f"   Objects: {', '.join(unique_objects[:5])}")
            if len(unique_objects) > 5:
                print(f"   ... and {len(unique_objects)-5} more")
        else:
            print(f"   No objects detected")

def export_for_visualization(data):
    """Export data for visualization tools."""
    print("\n📊 EXPORT OPTIONS")
    print("=" * 20)
    
    annotations = data['annotations']
    
    # CSV export
    csv_data = []
    csv_data.append("timestamp,object,x,y,width,height,x_3d,y_3d,z_3d,confidence")
    
    for ann in annotations:
        bbox = ann['bbox']
        coord_3d = ann['coordinates_3d']
        csv_data.append(f"{ann['timestamp']},{ann['object']},{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},{coord_3d[0]},{coord_3d[1]},{coord_3d[2]},{ann['confidence']}")
    
    with open('car_service_annotations.csv', 'w') as f:
        f.write('\n'.join(csv_data))
    
    print(f"✅ CSV exported: car_service_annotations.csv")
    print(f"   Use with Excel, Tableau, or Python pandas")

def main():
    """Main analysis function."""
    print("🎥 AI Annotation Analysis Tool")
    print("🤖 Gemini Pro Vision Results Explorer")
    print("=" * 50)
    
    data = load_latest_annotations()
    if not data:
        return
    
    print(f"📊 Dataset: {len(data['annotations'])} annotations from {data['total_frames_processed']} frames")
    print(f"⏱️  Video: {data['duration_seconds']/60:.1f} minutes")
    print(f"🎯 Processing: {data['processing_time_seconds']:.1f} seconds")
    
    # Run all analyses
    analyze_by_time(data)
    analyze_by_confidence(data)
    analyze_spatial_distribution(data)
    analyze_object_relationships(data)
    generate_timeline_summary(data)
    export_for_visualization(data)
    
    print(f"\n🎉 Analysis complete! Your AI annotations show rich automotive service content.")

if __name__ == "__main__":
    main() 