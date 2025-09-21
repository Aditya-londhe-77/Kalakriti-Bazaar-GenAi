from google.cloud import vision
import io, requests, urllib.parse

SERVICE_ACCOUNT_JSON = r"C:\Users\varad\OneDrive\Desktop\New folder\artifacte-scan-2986a052691c.json"
IMAGE_PATH = r"C:\Users\varad\OneDrive\Desktop\New folder\dhumraka.jpg"

GENERIC_STOPWORDS = {
    "soil", "ground", "dirt", "sand", "brush", "hand", "tool", "person", "human", "man", "woman",
    "photograph", "photo", "image", "art", "artwork", "museum", "head", "thorax", "throat",
    "excavation", "archaeology site", "land", "earth", "field", "clay"
}

HINTS = ["artifact", "archaeology", "ancient", "pottery", "vase", "amphora", "ceramic"]



def pick_candidates(web_detection, label_annotations):
    """Collect candidate terms from best-guess labels, web entities, then labels; filter generics."""
    candidates = []

    # Best guess labels are often very good (e.g., "Greek amphora", "ancient vase")
    if web_detection and web_detection.best_guess_labels:
        for b in web_detection.best_guess_labels:
            if b.label:
                candidates.append(b.label)

    # Web entities with scores are also strong signals
    if web_detection and web_detection.web_entities:
        entities = sorted(web_detection.web_entities, key=lambda e: (e.score or 0), reverse=True)
        for e in entities:
            if e.description:
                candidates.append(e.description)

    # Fallback to basic labels
    if label_annotations:
        for l in label_annotations:
            if l.description:
                candidates.append(l.description)

    # Normalize and filter
    seen, filtered = set(), []
    for c in candidates:
        c_norm = c.strip()
        c_low = c_norm.lower()
        if c_low in seen:
            continue
        seen.add(c_low)
        if c_low in GENERIC_STOPWORDS:
            continue
        # Skip very short/too generic single words
        if len(c_low) < 3:
            continue
        filtered.append(c_norm)

    return filtered


def detect_artifact_with_details(image_path: str):
    client = vision.ImageAnnotatorClient.from_service_account_file(SERVICE_ACCOUNT_JSON)

    with io.open(image_path, "rb") as f:
        content = f.read()

    image = vision.Image(content=content)

    # Use Web Detection + Labels
    web_resp = client.web_detection(image=image).web_detection
    label_resp = client.label_detection(image=image).label_annotations

    candidates = pick_candidates(web_resp, label_resp)

    if not candidates:
        print("No useful candidates found.")
        return
    print("Top detected terms:", ", ".join(candidates[:5]))


if __name__ == "__main__":
    detect_artifact_with_details(IMAGE_PATH)
