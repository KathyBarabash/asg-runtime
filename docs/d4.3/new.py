# Re-imports after code execution environment reset
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

# Use non-GUI backend
matplotlib.use("Agg")

# CSV data redefined
csv_data = """Tool / Framework,Maturity,Community & Ecosystem,License,Kubernetes Readiness,Notes
[Ollama](https://ollama.com),Medium (2023+),Growing, GitHub activity,MIT,Medium (via sidecar or job pods),"Easy CLI and Docker support; fast to prototype"
[LM Studio](https://lmstudio.ai),Low,"Small, mainly desktop users",Unknown,Low,"GUI-focused, not suitable for automation"
[vLLM](https://github.com/vllm-project/vllm),High,"Active research/dev community",Apache 2.0,High,"Excellent performance with batching; scalable"
[Text Generation Inference (TGI)](https://github.com/huggingface/text-generation-inference),High,"Strong support from Hugging Face",Apache 2.0,High,"Designed for production inference, full REST API"
[llama.cpp](https://github.com/ggerganov/llama.cpp),High (C++-based),"Very active, many wrappers",MIT,Medium,"Lightweight and efficient; CLI or custom server required"
[GPT4All](https://gpt4all.io),Medium,"Moderate, good docs","Apache/MIT",Low–Medium,"Better for desktop/offline GUI use"
[DeepSpeed-MII](https://github.com/microsoft/DeepSpeed-MII),Medium–High,"Research-focused",MIT,Medium–High,"Needs setup, but great for high-performance inference"
"AutoGPTQ / ExLlama","Medium","Niche but growing","Apache/MIT","Low–Medium","Optimized for quantized model inference, still maturing"
"""

from io import StringIO

# Load into DataFrame
df = pd.read_csv(StringIO(csv_data))

# Create the plot
fig, ax = plt.subplots(figsize=(18, len(df) * 0.8 + 2))
ax.axis("off")
table = ax.table(
    cellText=df.values,
    colLabels=df.columns,
    cellLoc="left",
    loc="center",
    colColours=["#d3d3d3"] * len(df.columns)
)

table.auto_set_font_size(False)
table.set_fontsize(10)

# Wrap text and style headers
for key, cell in table.get_celld().items():
    cell.set_text_props(wrap=True)
    if key[0] == 0:
        cell.set_fontsize(11)
        cell.set_text_props(weight="bold")

# Save as PNG
output_path = "/mnt/data/local_llm_options_wrapped.png"
plt.savefig(output_path, bbox_inches="tight", dpi=200)

output_path
