
// Auto-generated video annotations
const videoAnnotations = [
  {
    "time": "0:00:15",
    "timestamp": 15,
    "text": "Healthcare professional in clinical setting performing examination",
    "confidence": "Confidence: 92%",
    "objects": [
      "person",
      "medical equipment",
      "stethoscope",
      "white coat"
    ],
    "x": 0.6499999999999999,
    "y": 0.6000000000000001
  },
  {
    "time": "0:00:32",
    "timestamp": 32,
    "text": "Active medical procedure in sterile clinical environment",
    "confidence": "Confidence: 91%",
    "objects": [
      "medical procedure",
      "sterile environment",
      "medical tools"
    ],
    "x": 0.5,
    "y": 0.55
  },
  {
    "time": "0:01:05",
    "timestamp": 65,
    "text": "Active medical procedure in sterile clinical environment",
    "confidence": "Confidence: 91%",
    "objects": [
      "medical procedure",
      "sterile environment",
      "medical tools"
    ],
    "x": 0.5,
    "y": 0.55
  },
  {
    "time": "0:01:28",
    "timestamp": 88,
    "text": "Medical documentation and record-keeping activities",
    "confidence": "Confidence: 88%",
    "objects": [
      "medical chart",
      "clipboard",
      "documentation",
      "computer screen"
    ],
    "x": 0.5,
    "y": 0.4
  },
  {
    "time": "0:02:00",
    "timestamp": 120,
    "text": "Healthcare professional in clinical setting performing examination",
    "confidence": "Confidence: 92%",
    "objects": [
      "person",
      "medical equipment",
      "stethoscope",
      "white coat"
    ],
    "x": 0.6499999999999999,
    "y": 0.6000000000000001
  }
];

// Function to load annotations into your video player
function loadVideoAnnotations() {
    videoAnnotations.forEach(annotation => {
        addAnnotation(annotation);
    });
}

// Call this function after your video loads
// loadVideoAnnotations();
        