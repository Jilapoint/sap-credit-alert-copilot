# InsightFlow — Model Routing in Microsoft Foundry

**InsightFlow** is a small French-language Streamlit demo comparing Foundry `model-router` with a fixed model deployment on synthetic sales data.

## Prerequisites
- Python 3.10+
- Azure CLI and an identity allowed to invoke model inference in the Foundry project
- Microsoft Foundry project endpoint
- Foundry deployment named `model-router` (or adjust `.env`)
- Optional named model deployment, such as `gpt-4.1-mini`, for a baseline

## Quickstart

Project folder: `insightflow/`

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
az login
cp .env.example .env  # On Windows: copy .env.example .env
# Edit PROJECT_ENDPOINT and deployment names in .env
python generate_data.py
streamlit run app.py
```

## Demo narrative
1. Review the synthetic dataset and chart (12 months, 3 countries, 3 product categories, 2 customer segments).
2. Run a simple factual question with the router and a fixed deployment.
3. Repeat with comparative and strategic questions.
4. Compare selected model (`response.model`), latency and token usage.
5. Repeat prompts to observe variation; manually evaluate factual accuracy and recommendations.

## Design choices
- Pandas computes numbers. The LLM interprets precomputed aggregates, not raw row-by-row data.
- Each request is independent; this avoids hidden conversational state in the benchmark.
- Changing a Foundry routing profile (Balanced/Cost/Quality) is a deployment configuration, **not** a per-request UI switch in this demo.
- The app does not calculate € cost or claim any savings. To add costs, maintain a dated, verified price table for each selected underlying model and token type (including caching/reasoning details where applicable).
- Never send real sensitive customer data to a demo without organizational approval.

## Troubleshooting
- Failed auth: run `az login`, verify Azure RBAC.
- Resource not found: copy the **project endpoint**, not the standard Azure OpenAI inference endpoint.
- Deployment error: ensure your chosen deployment names exist and quotas/models are available.
- Python SDK issues: install `azure-ai-projects>=2.0.0`.

Official docs: https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/responses-model-routing
