from PIL import Image
import numpy as np

def resize_image(image: Image.Image, max_size: int = 768) -> Image.Image:
    """
    Resize image to fit within max_size, keeping aspect ratio.
    """
    w, h = image.size
    scale = min(max_size / w, max_size / h)
    if scale < 1:
        return image.resize((int(w * scale), int(h * scale)), Image.ANTIALIAS)
    return image

def np_to_pil(np_img):
    return Image.fromarray(np.uint8(np_img)).convert("RGB")

def pil_to_np(pil_img):
    return np.array(pil_img)
