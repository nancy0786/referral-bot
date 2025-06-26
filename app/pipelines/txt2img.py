from diffusers import StableDiffusionPipeline
import torch

# Load the model only once and reuse
pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float32
).to("cuda" if torch.cuda.is_available() else "cpu")

def generate_txt2img(prompt, seed=42, steps=30):
    generator = torch.manual_seed(int(seed))
    image = pipe(prompt=prompt, num_inference_steps=int(steps), generator=generator).images[0]
    return image
