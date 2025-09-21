import io
import os
import pandas as pd
from google.cloud import vision
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image, ImageTk

SERVICE_ACCOUNT_JSON = r"C:\Users\varad\OneDrive\Desktop\New folder\artifacte-scan-2986a052691c.json"
EXCEL_PATH = r"C:\Users\varad\OneDrive\Desktop\New folder\Untitled spreadsheet.xlsx"
LOGO_PATH = "image.png"

GENERIC_STOPWORDS = {
    "soil","ground","dirt","sand","brush","hand","tool","person","human","man","woman",
    "photograph","photo","image","art","artwork","museum","head","thorax","throat",
    "excavation","archaeology site","land","earth","field","clay"
}

def load_reference_data(sheet_path):
    if not os.path.exists(sheet_path):
        raise FileNotFoundError(f"Excel file not found at {sheet_path}")
    
    df = pd.read_excel(sheet_path, sheet_name="Sheet1")
    ref_data = {}
    for _, row in df.iterrows():
        if pd.isna(row.get("Keywords")):
            continue
        keywords = {k.strip().lower() for k in row["Keywords"].split(",")}
        ref_data[row["Name"]] = keywords
    return ref_data

def pick_candidates(web_detection, label_annotations, stopwords):
    candidates = []
    if web_detection and web_detection.best_guess_labels:
        candidates.extend([b.label for b in web_detection.best_guess_labels if b.label])
    if web_detection and web_detection.web_entities:
        candidates.extend([e.description for e in web_detection.web_entities if e.description])
    if label_annotations:
        candidates.extend([l.description for l in label_annotations if l.description])

    seen, filtered = set(), []
    for c in candidates:
        c_norm = c.strip()
        c_low = c_norm.lower()
        if c_low in seen: 
            continue
        seen.add(c_low)
        if c_low in stopwords: 
            continue
        if len(c_low) < 3: 
            continue
        filtered.append(c_norm.lower())
    return set(filtered)

def get_keywords(image_path, client, stopwords):
    with io.open(image_path, "rb") as f:
        content = f.read()
    image = vision.Image(content=content)
    web_resp = client.web_detection(image=image).web_detection
    label_resp = client.label_detection(image=image).label_annotations
    return pick_candidates(web_resp, label_resp, stopwords)

def jaccard_similarity(set1, set2):
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)

def match_image(test_image_path, ref_data, client, stopwords):
    test_keywords = get_keywords(test_image_path, client, stopwords)
    best_match, best_score = None, 0.0
    for name, ref_keywords in ref_data.items():
        score = jaccard_similarity(test_keywords, ref_keywords)
        if score > best_score:
            best_match, best_score = name, score

    if best_score < 0.15:
        return "No Match Found", best_score, test_keywords
    
    return best_match, best_score, test_keywords


class ArtifactScannerApp:
    def __init__(self, root, ref_data, client):
        self.root = root
        self.ref_data = ref_data
        self.client = client
        self.image_path = None

        self.colors = {
            "background": "#FFF8E1",
            "text": "#1F2937",
            "primary": "#134E4A",
            "accent": "#EA580C",
            "accent_active": "#C2410C",
            "white": "#FFFFFF",
            "border": "#B45309"
        }

        root.title("Artifact Scanner")
        root.geometry("700x750")
        root.configure(bg=self.colors["background"])

        if os.path.exists(LOGO_PATH):
            logo_img = Image.open(LOGO_PATH)
            logo_img.thumbnail((80, 80))
            self.logo_tk = ImageTk.PhotoImage(logo_img)
            logo_label = tk.Label(root, image=self.logo_tk, bg=self.colors["background"])
            logo_label.pack(pady=(10, 0))

        title_label = tk.Label(root, text="Artifact Scanner", font=("Rozha One", 24, "bold"), fg=self.colors["primary"], bg=self.colors["background"])
        title_label.pack(pady=10)

        self.upload_btn = ttk.Button(root, text="📂 Upload Image", command=self.upload_image, style="Accent.TButton")
        self.upload_btn.pack(pady=10)

        self.img_label = tk.Label(root, bg=self.colors["background"])
        self.img_label.pack(pady=10)

        self.scan_btn = ttk.Button(root, text="🔍 Scan & Match", command=self.scan_image, state="disabled", style="Accent.TButton")
        self.scan_btn.pack(pady=15)

        frame = tk.Frame(root, bg=self.colors["white"], highlightbackground=self.colors["border"], highlightthickness=2)
        frame.pack(pady=15, padx=20, fill="both", expand=True)

        result_label = tk.Label(frame, text="Results:", font=("Lora", 12, "bold"), bg=self.colors["white"], fg=self.colors["primary"], anchor="w")
        result_label.pack(fill="x", padx=10, pady=(5,0))

        self.result_text = tk.Text(frame, height=15, width=70, wrap="word", bg=self.colors["white"], fg=self.colors["text"], font=("Lora", 11), relief="flat")
        self.result_text.pack(padx=10, pady=10, fill="both", expand=True)

    def upload_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.jpeg *.png")])
        if not path:
            return
        self.image_path = path

        img = Image.open(path)
        img.thumbnail((450, 300))
        self.tk_img = ImageTk.PhotoImage(img)
        self.img_label.config(image=self.tk_img)

        self.scan_btn.config(state="normal")

    def scan_image(self):
        if not self.image_path:
            messagebox.showerror("Error", "Please upload an image first.")
            return

        try:
            best, score, test_kw = match_image(self.image_path, self.ref_data, self.client, GENERIC_STOPWORDS)
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"Extracted Keywords:\n{', '.join(sorted(test_kw))}\n\n")
            self.result_text.insert(tk.END, f"Best Match: {best}\n")
            self.result_text.insert(tk.END, f"Similarity Score: {score:.2f}\n")
        except Exception as e:
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    ref_data = load_reference_data(EXCEL_PATH)
    client = vision.ImageAnnotatorClient.from_service_account_file(SERVICE_ACCOUNT_JSON)

    root = tk.Tk()
    
    style = ttk.Style()
    style.theme_use("clam")
    
    colors = {
        "accent": "#EA580C",
        "accent_active": "#C2410C",
        "white": "#FFFFFF"
    }

    style.configure("Accent.TButton", 
        font=("Lora", 11, "bold"), 
        padding=8, 
        background=colors["accent"], 
        foreground=colors["white"],
        relief="flat",
        borderwidth=0
    )
    style.map("Accent.TButton", 
    background=[("active", colors["accent_active"])],
    foreground=[("active", colors["white"])]
)

    app = ArtifactScannerApp(root, ref_data, client)
    root.mainloop()