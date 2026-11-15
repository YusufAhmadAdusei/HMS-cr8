
import cv2
import numpy as np
import base64

def preprocess_face(image_path):

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError("Unable to read image.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades +
        "haarcascade_frontalface_default.xml"
    )

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(100, 100)
    )

    if len(faces) == 0:
        raise ValueError(
            "No frontal face detected. "
            "Please upload a clear, front-facing image."
        )

    # Select the largest detected face
    x, y, w, h = max(
        faces,
        key=lambda face: face[2] * face[3]
    )

    # Add padding to preserve surrounding skin
    pad_x = int(w * 0.20)
    pad_y = int(h * 0.20)

    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(image.shape[1], x + w + pad_x)
    y2 = min(image.shape[0], y + h + pad_y)

    face = image[y1:y2, x1:x2]

    # Image quality assessment
    blur_score = cv2.Laplacian(
        cv2.cvtColor(face, cv2.COLOR_BGR2GRAY),
        cv2.CV_64F
    ).var()

    brightness = np.mean(
        cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    )

    quality_warnings = []

    if blur_score < 40:
        quality_warnings.append("Image may be blurry")

    if brightness < 40:
        quality_warnings.append("Image may be too dark")

    if brightness > 220:
        quality_warnings.append("Image may be overexposed")

    # Convert to JPEG without changing skin colours
    success, encoded = cv2.imencode(
        ".jpg",
        face,
        [cv2.IMWRITE_JPEG_QUALITY, 95]
    )

    if not success:
        raise ValueError("Image encoding failed.")

    image_base64 = base64.b64encode(
        encoded.tobytes()
    ).decode("utf-8")

    return {
        "image_base64": image_base64,
        "blur_score": float(blur_score),
        "brightness": float(brightness),
        "quality_warnings": quality_warnings
    }
