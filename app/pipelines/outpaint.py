from diffusers import StableDiffusionInpaintPipeline
import torch
from PIL import Image
import numpy as np

# Load inpainting model for outpainting too
pipe = StableDiffusionInpaintPipeline.from_pretrained(
    "runwayml/stable-diffusion-inpainting",
    torch_dtype=torch.float32
).to("cuda" if torch.cuda.is_available() else "cpu")

def pad_image_and_mask(image: Image.Image, padding: int = 128) -> (Image.Image, Image.Image):
    w, h = image.size
    new_w, new_h = w + padding * 2, h + padding * 2

    # Create new image and mask with padding
    padded_image = Image.new("RGB", (new_w, new_h), (255, 255, 255))
    padded_image.paste(image, (padding, padding))

    mask = Image.new("L", (new_w, new_h), 0)
    mask.paste(255, (0, 0, new_w, padding))                      # Top
    mask.paste(255, (0, h + padding, new_w, new_h))              # Bottom
    mask.paste(255, (0, padding, padding, h + padding))          # Left
    mask.paste(255, (w + padding, padding, new_w, h + padding))  # Right

    return padded_image, mask

def generate_outpaint(image_np, prompt, seed=555, steps=30):
    # Convert from numpy to PIL
    image = Image.fromarray(np.uint8(image_np)).convert("RGB")

    # Add padding + mask for outpainting
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
