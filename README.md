# 🎨 Private Fooocus AI

Your fully private, high-quality image generation app — inspired by Fooocus but fully self-owned.  
Includes **Text-to-Image**, **Inpainting**, and **Outpainting** features using Stable Diffusion.

---

## 🚀 Features

✅ Text-to-Image (like MidJourney)  
✅ Inpainting (upload image + draw mask + prompt)  
✅ Outpainting (expand image borders intelligently)  
✅ Powered by `diffusers`, `gradio`, `torch`, `PIL`  
✅ Runs on GitHub Actions or Google Colab  
✅ No external repo dependencies — fully private

---

## 🔧 Run via GitHub Actions

1. Click the **"Actions"** tab in your GitHub repo  
2. Choose **"Run Private Fooocus AI"** → click **Run workflow**  
3. Wait ~60 seconds  
4. Look in the logs — you'll see a **Gradio live link** (`https://*.gradio.live`)  
5. Open that link and use the app 🎉

---

## 📓 Run via Google Colab

```python
# Copy this into a Colab notebook cell
!git clone https://github.com/yourusername/private-fooocus-ai.git
%cd private-fooocus-ai
!pip install -r requirements.txt
%cd app
!python main.py --share
