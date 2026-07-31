import json

path = r"C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine\output\phase3_paper_titles.json"

with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

data["交叉领域智能应用"] = [
    "FinStressTS: A Parametric Synthetic Benchmark for Time-Series Forecasting in Finance",
    "Hedge-Bench: Benchmarking Agents on Hard, Realistic Tasks Pertaining to Financial Reasoning",
    "Polymarket-v1 Database",
    "Language-Based Digital Twins for Elderly Cognitive Assistance",
    "Routine laboratory trajectories encode the onset of organ-level complications in cancer",
    "ChronoSurv: A Clinical Pathway-Guided Graph Framework for Multimodal Survival Analysis",
    "The Effortless Trap: Productive Struggle, AI, and the Illusion of Learning",
    "Test-Driven, AI-Assisted Learning: Replacing Lectures with Weekly Closed-Book Tests",
    "LLM-as-Judge in Education: A Curriculum-Grounded Marking Pipeline",
    "Scaling Laws for Task-Specific LLM Distillation",
    "Agents' Last Exam",
    "Domain-Adapted Small Language Models with Hybrid Post-Processing: Achieving Cost-Efficient, Low-Latency Multi-Label Structured Prediction via LoRA Fine-Tuning on Scarce Data",
    "TS-ICL: A Flexible Time-Indexed Foundation Model for Time Series via In-Context Learning",
    "Filtered Conformal Ellipsoids for Graph-Native Time Series",
    "Once-for-All: Scalable Simultaneous Forecasting via Equilibrium State Estimation",
    "Forecasting what Matters: Decision-Focused RL for Controlled EV Charging with Unknown Departure Times",
    "Maximising the Set-Piece Return: Optimising Football Corner Tactics with Graph Reinforcement Learning",
    "PandaAI: A Practical Agent CQ2 for Neuro-symbolic Data Analysis And Integrated Decision-Making in Quantitative Finance",
    "The Economics of Proof-of-Useful-Work",
    "Polymarket-v1 Database",
    "Proof of Source of Funds: Efficient On-chain Provenance of Cryptoassets",
    "Reimagining Open Source and Openness in AI: Co-Creating Responsible Technological Futures",
    "War in the Abstract: The Rise and Consequences of Militarized Language in Scientific Communication",
    "AI Exposure Scores: what they measure, what they miss, and what comes next",
    "AI+CAD Data Representation Architecture: From DeepCAD Solid Modeling to WHUCAD Industrial-Level Parametric Feature Modeling",
    "Learning the Geometry of Data: A Mathematical Review of Shape Space Analysis",
    "Generating Special Triangulations with Transformers",
    "Orange Lab: Lowering Barriers to Data Mining through Embedded Interactive Workflows",
    "Econstellar: An Open-Source AI-Augmented Research Engine for Computational Financial Econometrics",
    "Towards Unified and Data-Efficient Prognostics and Health Management with Tabular Foundation Models"
]

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Updated: {len(data)} domains, total: {sum(len(v) for v in data.values())} papers")