from diffusers import StableDiffusionInpaintPipeline
import torch
import numpy as np
from PIL import Image
from app.utils import fallback_image
from app.utils import resize_image, np_to_pil, pil_to_np

pipe = StableDiffusionInpaintPipeline.from_pretrained(
    "runwayml/stable-diffusion-inpainting",
    torch_dtype=torch.float32
).to("cuda" if torch.cuda.is_available() else "cpu")

def generate_inpaint(image_with_mask, prompt, seed=123, steps=30):
    if isinstance(image_with_mask, dict):
        image_np = image_with_mask.get("image")
        mask_np = image_with_mask.get("mask")
        if image_np is None or mask_np is None:
            return fallback_image("Missing image or mask")
    else:
        return fallback_image("Invalid input type")

    try:
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
    except Exception as e:
        print("inpaint failed:", e)
        return fallback_image("Inpaint failed")
