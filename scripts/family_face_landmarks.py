"""The face family render (runner:insightface_buffalo_l): InsightFace buffalo_l, detection (det_10g) and 106-point landmarks (2d106det), on the CPU. python scripts/family_face_landmarks.py in.png out.png report.json"""
import json, os, sys, time, cv2, numpy as np
from insightface.app import FaceAnalysis
src, out, rep = sys.argv[1:4]; t0 = time.time()
app = FaceAnalysis(name="buffalo_l", root=os.path.join(os.environ.get("PSN_MODELS_ROOT", os.path.expanduser("~/ComfyUI/models")), "face", "insightface"), allowed_modules=["detection", "landmark_2d_106"], providers=["CPUExecutionProvider"])
app.prepare(ctx_id=-1, det_size=(640, 640))
img = cv2.imread(src); faces = app.get(img); vis = img.copy()
for f in faces:
    x1, y1, x2, y2 = [int(v) for v in f.bbox]; cv2.rectangle(vis, (x1, y1), (x2, y2), (60, 220, 60), 2)
    for (x, y) in f.landmark_2d_106.astype(int): cv2.circle(vis, (int(x), int(y)), 1, (40, 40, 255), -1)
cv2.imwrite(out, vis)
json.dump({"faces": len(faces), "scores": [round(float(f.det_score), 3) for f in faces], "boxes": [[round(float(v)) for v in f.bbox] for f in faces], "seconds": round(time.time() - t0, 1), "size": list(img.shape[:2])}, open(rep, "w"), indent=1); print(open(rep).read())
