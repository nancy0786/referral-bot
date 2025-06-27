from diffusers import StableDiffusionInpaintPipeline
import torch
import numpy as np
from PIL import Image, ImageDraw

# Load the inpainting pipeline once
pipe = StableDiffusionInpaintPipeline.from_pretrained(
    "runwayml/stable-diffusion-inpainting",
    torch_dtype=torch.float32
).to("cuda" if torch.cuda.is_available() else "cpu")

def generate_inpaint(image_with_mask, prompt, seed=123, steps=30):
    # Separate image and mask from the sketch
    if isinstance(image_with_mask, dict):
        image_np = image_with_mask.get("image")
        mask_np = image_with_mask.get("mask")
        if image_np is None or mask_np is None:
            return fallback_image()  # missing parts
    else:
        return fallback_image()  # invalid type

    image_pil = Image.fromarray(np.uint8(image_np)).convert("RGB")
    mask_pil = Image.fromarray(np.uint8(mask_np)).convert("L")

    generator = torch.manual_seed(int(seed))
    result = pipe(
        prompt=prompt,
        image=image_pil,
        mask_image=mask_pil,
        num_inference_steps=int(steps),
        generator=generator
    ).images[0]

    return result

def fallback_image():
    # Return a white 512x512 image with error message
    blank = Image.new("RGB", (512, 512), (255, 255, 255))
    draw = ImageDraw.Draw(blank)
    draw.text((10, 10), "Invalid input", fill=(0, 0, 0))
    return blank
