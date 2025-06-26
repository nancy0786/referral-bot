from diffusers import StableDiffusionInpaintPipeline
import torch
import numpy as np
from PIL import Image

# Load the inpainting pipeline once
pipe = StableDiffusionInpaintPipeline.from_pretrained(
    "runwayml/stable-diffusion-inpainting",
    torch_dtype=torch.float32
).to("cuda" if torch.cuda.is_available() else "cpu")

def generate_inpaint(image_with_mask, prompt, seed=123, steps=30):
    # Separate image and mask from the sketch
    if isinstance(image_with_mask, dict):
        image_np = image_with_mask["image"]
        mask_np = image_with_mask["mask"]
    else:
        return None  # Invalid input

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
