from diffusers import StableDiffusionPipeline
import torch
from PIL import Image, ImageDraw

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float32
).to("cuda" if torch.cuda.is_available() else "cpu")

def generate_txt2img(prompt, seed=42, steps=30):
    try:
        generator = torch.manual_seed(int(seed))
        image = pipe(prompt=prompt, num_inference_steps=int(steps), generator=generator).images[0]
        return image
    except Exception:
        return fallback_image()

def fallback_image():
    blank = Image.new("RGB", (512, 512), (255, 255, 255))
    draw = ImageDraw.Draw(blank)
    draw.text((10, 10), "Error: txt2img failed", fill=(0, 0, 0))
    return blank
