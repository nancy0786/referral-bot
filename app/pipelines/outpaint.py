from diffusers import StableDiffusionInpaintPipeline
import torch
import numpy as np
from PIL import Image
from pipelines.utils import fallback_image

pipe = StableDiffusionInpaintPipeline.from_pretrained(
    "runwayml/stable-diffusion-inpainting",
    torch_dtype=torch.float32
).to("cuda" if torch.cuda.is_available() else "cpu")

def pad_image_and_mask(image, expand_px=64):
    w, h = image.size
    new_w, new_h = w + expand_px * 2, h + expand_px * 2

    padded = Image.new("RGB", (new_w, new_h), (255, 255, 255))
    padded.paste(image, (expand_px, expand_px))

    mask = Image.new("L", (new_w, new_h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle([0, 0, new_w, new_h], fill=255)
    draw.rectangle([expand_px, expand_px, expand_px + w, expand_px + h], fill=0)

    return padded, mask

def generate_outpaint(image_np, prompt, seed=555, steps=30):
    try:
        image = Image.fromarray(np.uint8(image_np)).convert("RGB")
        padded_img, mask = pad_image_and_mask(image)
        generator = torch.manual_seed(int(seed))
        result = pipe(
            prompt=prompt,
            image=padded_img,
            mask_image=mask,
            num_inference_steps=int(steps),
            generator=generator
        ).images[0]
        return result
    except Exception as e:
        print("outpaint failed:", e)
        return fallback_image("Outpaint failed")
