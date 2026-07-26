
# Adaptive AI Coding Assessment Platform

## Team Members

- Person 1 – Sandbox
- Person 2 – LLM Evaluator
- Person 3 – Recommender
- Person 4 – Frontend & Integration

## Setup

1. Clone the repository.
2. Create a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the app:

```bash
streamlit run app.py
```


## Local Model Setup (Ollama)

This project can run using a local AI model instead of a paid cloud API. Here's how to get that working on your machine.

### 1. Install Ollama

Download and install Ollama from [ollama.com](https://ollama.com) — pick the version for your operating system and run the installer. Once installed, it runs quietly in the background (on Windows, look for its icon in the system tray near the clock).

### 2. Download the model

Open a terminal and run: 

ollama pull gemma2

This downloads the model we're using for this project (`gemma2`). It's a few gigabytes, so it may take a while depending on your internet connection. Make sure everyone on the team pulls this exact same model tag — using different versions of the model can cause inconsistent results.

### 3. Verify it works

Once the download finishes, test it with: ollama run gemma2 "Say hello in 5 words"

If you get a text response back, Ollama is working correctly. Type `/bye` to exit.

### 4. Verify the app's connection method

The app talks to Ollama using the OpenAI Python SDK, pointed at Ollama's local address instead of OpenAI's servers. You can confirm this works with a quick test script:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

resp = client.chat.completions.create(
    model="gemma2",
    messages=[{"role": "user", "content": "Say hello in 5 words"}],
    temperature=0.2,
)
print(resp.choices[0].message.content)
```

If this prints a response, your setup is complete and the app will be able to reach the local model.

### Troubleshooting

- **"Connection refused" or similar errors** — Ollama isn't running. Check your system tray, or start it manually by running `ollama serve` in a terminal.
- **Model not found** — you may have skipped step 2, or pulled a different model tag than `gemma2`. Run `ollama list` to see what's installed.



