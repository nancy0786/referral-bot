from diffusers import StableDiffusionPipeline
import torch
from PIL import Image
from pipelines.utils import fallback_image

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float32
).to("cuda" if torch.cuda.is_available() else "cpu")

def generate_txt2img(prompt, seed=42, steps=30):
    try:
        generator = torch.manual_seed(int(seed))
        image = pipe(prompt=prompt, num_inference_steps=int(steps), generator=generator).images[0]
        return image
    except Exception as e:
        print("txt2img failed:", e)
        return fallback_image("Generation failed")
