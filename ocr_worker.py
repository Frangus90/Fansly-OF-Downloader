"""Persistent OCR worker process.

Runs under the embedded Python (ocr_env/), not the frozen exe.
Reads JSON-line requests from stdin, writes JSON-line responses to stdout.
The easyocr Reader is initialized once and reused across all requests.
"""

import json
import sys


def _init_reader():
    """Initialize EasyOCR reader with GPU if available, else CPU."""
    import easyocr

    gpu = False
    try:
        import torch
        gpu = torch.cuda.is_available()
    except Exception:
        pass

    return easyocr.Reader(["en"], gpu=gpu)


def _handle_detect(reader, request):
    """Run OCR on an image and return detections."""
    image_path = request["image_path"]
    text_threshold = request.get("text_threshold", 0.7)
    low_text = request.get("low_text", 0.4)
    mag_ratio = request.get("mag_ratio", 1.0)

    results = reader.readtext(
        image_path,
        text_threshold=text_threshold,
        low_text=low_text,
        mag_ratio=mag_ratio,
    )

    detections = []
    for bbox, text, confidence in results:
        ys = [int(point[1]) for point in bbox]
        xs = [int(point[0]) for point in bbox]
        detections.append({
            "bbox": [min(ys), max(ys), min(xs), max(xs)],
            "text": text,
            "confidence": confidence,
        })

    return {"status": "ok", "detections": detections}


def main():
    reader = None

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            _respond({"status": "error", "message": f"Invalid JSON: {e}"})
            continue

        cmd = request.get("cmd", "")

        if cmd == "ping":
            _respond({"status": "ok"})

        elif cmd == "quit":
            _respond({"status": "ok"})
            break

        elif cmd == "detect":
            try:
                if reader is None:
                    reader = _init_reader()
                result = _handle_detect(reader, request)
                _respond(result)
            except Exception as e:
                _respond({"status": "error", "message": str(e)})

        else:
            _respond({"status": "error", "message": f"Unknown command: {cmd}"})


def _respond(data):
    """Write a JSON-line response to stdout and flush."""
    sys.stdout.write(json.dumps(data) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
