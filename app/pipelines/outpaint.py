from diffusers import StableDiffusionInpaintPipeline
import torch
from PIL import Image, ImageDraw
import numpy as np

pipe = StableDiffusionInpaintPipeline.from_pretrained(
    "runwayml/stable-diffusion-inpainting",
    torch_dtype=torch.float32
).to("cuda" if torch.cuda.is_available() else "cpu")

def pad_image_and_mask(image: Image.Image, padding: int = 128) -> (Image.Image, Image.Image):
    w, h = image.size
    new_w, new_h = w + padding * 2, h + padding * 2

    padded_image = Image.new("RGB", (new_w, new_h), (255, 255, 255))
    padded_image.paste(image, (padding, padding))

    mask = Image.new("L", (new_w, new_h), 0)
    mask.paste(255, (0, 0, new_w, padding))
    mask.paste(255, (0, h + padding, new_w, new_h))
    mask.paste(255, (0, padding, padding, h + padding))
    mask.paste(255, (w + padding, padding, new_w, h + padding))

    return padded_image, mask

def generate_outpaint(image_np, prompt, seed=555, steps=30):
    try:
        image = Image.fromarray(np.uint8(image_np)).convert("RGB")
        padded_img, mask = pad_image_and_mask(image, padding=128)
        generator = torch.manual_seed(int(seed))
        result = pipe(
            prompt=prompt,
            image=padded_img,
            mask_image=mask,
            num_inference_steps=int(steps),
            generator=generator
        ).images[0]
        return result
    except Exception:
        return fallback_image()

def fallback_image():
    blank = Image.new("RGB", (512, 512), (255, 255, 255))
    draw = ImageDraw.Draw(blank)
    draw.text((10, 10), "Error: outpaint failed", fill=(0, 0, 0))
    return blank
