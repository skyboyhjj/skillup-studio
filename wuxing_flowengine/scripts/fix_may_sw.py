import json

existing_path = r"C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine\output\phase3_may_paper_titles.json"

with open(existing_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Fix 软件工程与编程 May data with actual paper titles
data["软件工程与编程"] = [
    "One Developer Is All You Need: A Case Study of an AI-Augmented One-Person Squad in a Brownfield Enterprise",
    "SpecBench: Measuring Reward Hacking in Long-Horizon Coding Agents",
    "Agentic Agile-V: From Vibe Coding to Verified Engineering in Software and Hardware Development",
    "Extrapolative Weight Averaging Reveals Correctness-Efficiency Frontiers in Code RL",
    "StepCodeReasoner: Aligning Code Reasoning with Stepwise Execution Traces via Reinforcement Learning",
    "Code Generation by Differential Test Time Scaling",
    "Agentic Vulnerability Reasoning on Windows COM Binaries",
    "NeuroLog: Reasoning You Can Audit -- Neuro-Symbolic Vulnerability Discovery via LLM Facts, Datalog, and SMT",
    "SecureForge: Finding and Preventing Vulnerabilities in LLM-Generated Code via Prompt Optimization",
    "Inductive Deductive Synthesis: Enabling AI to Generate Formally Verified Systems",
    "Verus-SpecGym: An Agentic Environment for Evaluating Specification Autoformalization",
    "Agentic Separation Logic Specification Synthesis",
    "The Impact of AI Coding Assistants on Software Engineering: A Longitudinal Study",
    "From Prompting to Verification: How Experience Shapes Vibe Coding Practices",
    "Can LLMs Produce Better Object-Oriented Designs than Human-Involved Development?",
    "Articulate but Wrong: Self-Review Failures in LLM-Based Code Modernization",
    "Breaking Changes in Software Ecosystems: A Systematic Literature Review",
    "Names Are All You Need: Effective and Safe Regression Test Selection for Python",
    "SWE-Mutation: Can LLMs Generate Reliable Test Suites in Software Engineering?",
    "DiagEval: Trajectory-Conditioned Diagnosis for Reliable Software Evaluation with GUI Agents",
    "A semantic mutation metric for metamorphic relation adequacy in scientific computing programs",
    "AI-Generated Smells: An Analysis of Code and Architecture in LLM and Agent-Driven Development",
    "Bridging Requirements and Architecture: Multi-Agent Orchestration with External Knowledge and Hierarchical Memory",
    "Strategies for Guiding LLMs to Use Software Design Patterns: A Case of Singleton",
    "On the Reliability of Code Comprehension Proxies",
    "XSearch: Explainable Code Search via Concept-to-Code Alignment",
    "The Readability Spectrum: Patterns, Issues, and Prompt Effects in LLM-Generated Code",
    "Debug Like a Human: Scaling LLM-based Fault Localization to Processor Design via Block-Level Instruction-Oriented Slicing",
    "Finding Missing Input Validation in TEEs via LLM-Assisted Symbolic Execution",
    "Customizing an LLM for Enterprise Software Engineering"
]

with open(existing_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Updated 软件工程与编程 May data")
for domain, papers in data.items():
    print(f"  {domain}: {len(papers)} papers")
print(f"  Total: {sum(len(v) for v in data.values())} papers across {len(data)} domains")