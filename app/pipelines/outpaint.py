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
        return fallback_image()

def fallback_image():
    blank = Image.new("RGB", (512, 512), (255, 255, 255))
    draw = ImageDraw.Draw(blank)
    draw.text((10, 10), "Outpaint failed", fill=(0, 0, 0))
    return blank
