import gradio as gr
from pipelines.txt2img import generate_txt2img
from pipelines.inpaint import generate_inpaint
from pipelines.outpaint import generate_outpaint

# Text-to-Image tab
def text2img_ui():
    with gr.Row():
        prompt = gr.Textbox(label="Prompt", placeholder="A futuristic cyberpunk city at night")
    with gr.Row():
        seed = gr.Number(label="Seed (optional)", value=42)
        steps = gr.Slider(10, 50, value=30, step=1, label="Steps")
    run_btn = gr.Button("Generate")
    output = gr.Image(label="Generated Image")

    run_btn.click(generate_txt2img, inputs=[prompt, seed, steps], outputs=output)

# Inpainting tab
def inpaint_ui():
    with gr.Row():
        input_img = gr.Image(label="Upload image", type="numpy")  # tool="sketch" allows masking
    with gr.Row():
        prompt = gr.Textbox(label="Prompt", placeholder="Fix the sky to be bright and blue")
        seed = gr.Number(label="Seed (optional)", value=123)
        steps = gr.Slider(10, 50, value=30, step=1, label="Steps")
    run_btn = gr.Button("Inpaint")
    output = gr.Image(label="Inpainted Image")

    run_btn.click(generate_inpaint, inputs=[input_img, prompt, seed, steps], outputs=output)

# Outpainting tab
def outpaint_ui():
    with gr.Row():
        input_img = gr.Image(label="Upload image", type="numpy")
    with gr.Row():
        prompt = gr.Textbox(label="Prompt", placeholder="Expand the scene with mountains")
        seed = gr.Number(label="Seed (optional)", value=555)
        steps = gr.Slider(10, 50, value=30, step=1, label="Steps")
    run_btn = gr.Button("Outpaint")
    output = gr.Image(label="Outpainted Image")

    run_btn.click(generate_outpaint, inputs=[input_img, prompt, seed, steps], outputs=output)

# Launch the app
with gr.Blocks(title="Private Fooocus AI") as demo:
    gr.Markdown("# 🎨 Private Fooocus AI\nCreate, Inpaint, and Outpaint your own images privately.")

    with gr.Tab("Text-to-Image"):
        text2img_ui()

    with gr.Tab("Inpainting"):
        inpaint_ui()

    with gr.Tab("Outpainting"):
        outpaint_ui()

demo.launch(share=True)
