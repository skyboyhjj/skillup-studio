import json

path = r"C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine\output\phase3_paper_titles.json"

with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

data["AI 系统与硬件"] = [
    "MiniMax Sparse Attention",
    "Epiphany-Aware KV Cache Eviction Without the Attention Matrix",
    "SAC: Disaggregated KV Cache System for Sparse Attention LLMs with CXL",
    "The Benchmark Illusion: Pruned LLMs Can Pass Multiple Choice but Fail to Answer",
    "Ternary Mamba: Grouped Quantization-Aware Training of W1.58A16 State Space Models",
    "Distill on a Diet: Efficient Knowledge Distillation via Learnable Data Pruning",
    "daVinci-kernel: Co-Evolving Skill Selection, Summarization, and Utilization via RL for GPU Kernel Optimization",
    "TileMaxSim: IO-Aware GPU MaxSim Scoring with Dimension Tiling and Fused Product Quantization",
    "EmuGEMM: Fused Tensor Core Kernels for Precision Emulation in Matrix Multiplication",
    "Piper: A Programmable Distributed Training System",
    "UltraEP: Unleash MoE Training and Inference on Rack-Scale Nodes with Near-Optimal Load Balancing",
    "FoMoE: Breaking the Full-Replica Barrier with a Federation of MoEs",
    "Programmable Probabilistic Computer with 1,000,000 p-bits",
    "Clutch: High Performance Vector-Scalar Comparison using DRAM via Chunked Temporal Coding",
    "Optimizing Energy-based Neural Network Training with Coherent Ising Machine",
    "ScaleDisturb: Exploiting Temporal Asymmetry to Amplify Read Disturbance in Modern DRAM Chips",
    "ColumnKeeper: Efficient Solutions to the ColumnDisturb Vulnerability in DRAM-based Systems",
    "In-DRAM Signature Generation Using Simultaneous Multiple-Row Activation: An Experimental Study of Off-The-Shelf DRAM Chips",
    "Efficient On-Device Diffusion LLM Inference with Mobile NPU",
    "From Compression to Deployment: Real-Time and Energy-Efficient FastGRNN on Ultra-Constrained Microcontrollers",
    "CITRAS-FM: Tiny Time Series Foundation Model for Covariate-Informed Zero-Shot Forecasting",
    "GPUSparse: GPU-Accelerated Learned Sparse Retrieval with Parallel Inverted Indices",
    "Slipstream: Locality-Aware Graph Index Construction for Streaming Approximate Nearest Neighbor Search",
    "RISE: A Rust Library for Inverted Index Search Engines",
    "ARGUS: Production-Scale Tracing and Performance Diagnosis for over 10,000-GPU Clusters",
    "BatchGen: An Architecture for Scalable and Efficient Batch Inference",
    "ASTRA-sim 3.0: Next-Level Distributed Machine Learning Simulations via High-Fidelity GPU and Infrastructure Modeling",
    "Do Transformers Need Three Projections? Systematic Study of QKV Variants",
    "Reversible Foundations: Training a 120B Sparse MoE through State-Preserving Scaling",
    "USAD 2.0: Scaling Representation Distillation for Universal Audio Understanding"
]

data["软件工程与编程"] = [
    "Agentic Very Much! Adoption of Coding Agent in New GitHub Projects",
    "Before the Pull Request: Mining Multi-Agent Coordination",
    "A Deterministic Control Plane for LLM Coding Agents",
    "Multi-LCB: Extending LiveCodeBench to Multiple Programming Languages",
    "SWE-Marathon: Can Agents Autonomously Complete Ultra-Long-Horizon Software Work?",
    "Evaluating LLMs on Real-World Software Performance Optimization",
    "OpenAnt: LLM-Powered Vulnerability Discovery Through Code Decomposition, Adversarial Verification, and Dynamic Testing",
    "Context-Based Adversarial Attacks on AI Code Generators: Vulnerability Analysis and Implications",
    "Beyond Takedown: Measuring Malicious Go Module Persistence in the Wild",
    "Code2LoRA: Hypernetwork-Generated Adapters for Code Language Models under Software Evolution",
    "How Much Static Structure Do Code Agents Need? A Study of Deterministic Anchoring",
    "FastContext: Training Efficient Repository Explorer for Coding Agents",
    "All Smoke, No Alarm: Oracle Signals in Agent-Authored Test Code",
    "LLM-Assisted Model-Based GUI Testing for Vue.js Web Applications",
    "LLM vs. Human Unit Tests: Fault Detection on Real Python Bugs",
    "Faster Code, Deeper Debt? A Multivocal Literature Review on Technical Debt and Its Early Signs in LLM-Assisted Software Development",
    "Are LLMs Ready for Anti-Pattern Detection in Microservice Architectures?",
    "Configuration Smells in AGENTS.md Files: Common Mistakes in Configuring Coding Agents",
    "Proof-Refactor: Refactoring Generated Formal Proofs into Modular Artifacts",
    "Formal-Method-Guided Vibe Coding: Closing the Verification Loop on AI-Generated Safety-Critical Software Through Model-Driven Engineering",
    "EconCSLib: AI-Assisted Lean Formalization for Economics & Computation research",
    "Rule Taxonomy and Evolution in AI IDEs: A Mining and Survey Study",
    "Same Scrutiny, More Time: Eye Tracking Insights into Reviewing LLM-Labelled Code",
    "How Software Engineering Students Use LLMs to Write Research Papers: An Experience Report",
    "GameCraft-Bench: Can Agents Build Playable Games End-to-End in a Real Game Engine?",
    "LLM4RTL: Tool-Assisted LLM for RTL Generation",
    "TeleSWEBench: A Commit-Driven Benchmark for Evaluating LLM-Powered Software Engineering in Telecommunications",
    "Natural Language-Focused Software Engineering via Code-Documentation Equivalence",
    "LLM-Based Discovery of Latent Requirements from Stakeholder Conversations: Preliminary Results from Industry",
    "The Spec Growth Engine: Spec-Anchored, Code-Coupled, Drift-Enforced Architecture for AI-Assisted Software Development"
]

data["科学 AI"] = [
    "AlloGen: Conformation-Selective Binder Generation with Differential State Scoring",
    "Few-step Cofolding with All-Atom Flow Maps",
    "AgentPLM: Agentic Protein Language Models with Reasoning-Augmented Decoding for Protein Sequence Design",
    "Topological Neural Operators",
    "Factorized Neural Operators Decompose Dynamic and Persistent Responses",
    "Effective Dimensionality as an Operator Invariant for Physics-Preserving Constraint Adaptation in Physics-Informed Neural Networks",
    "XRDiff: Crystal Structure Prediction from Powder X-Ray Diffraction Data Using Diffusion Models",
    "Fast Organic Crystal Structure Prediction with Unit Cell Flow Matching",
    "Autonomous heterogeneous catalyst discovery with a self-evolving multi-agent digital twin",
    "Scalable On-Hardware Training of Quantum Neural Networks and Application to Clinical Data Imputation",
    "Efficient foundation decoders for fault-tolerant quantum computing",
    "Quantum-classical physics-informed Kolmogorov-Arnold networks for PDEs",
    "Harnessing the Collective Intelligence of AI Agents in the Wild for New Discoveries",
    "EurekAgent: Agent Environment Engineering is All You Need For Autonomous Scientific Discovery",
    "SciAgentArena: Benchmarking AI Agents for Addressing Scientific Challenges Across Scales",
    "ThousandWorlds: A benchmark for climate emulation of potentially habitable exoplanets",
    "Time series Foundation Models based on Physics-Informed Synthetic Histories for Cold-Start Photovoltaic Forecasting",
    "Scalable Uncertainty Quantification for Extreme Weather Forecasting via Empirical Neural Tangent Kernels",
    "What Does a Chemical Language Model Know About Molecules?",
    "Circuit Tracing in Autoregressive Protein Language Models",
    "Viral Proteins Reveal Geometry of Protein Language Models",
    "Speculative Sampling For Faster Molecular Dynamics",
    "Autoregressive Boltzmann Generators",
    "Scene-Level Heterogeneous Physics Simulation with 3D Gaussian Splats",
    "Data-driven discovery of governing differential equations across physical systems",
    "Discovering Multiscale Deep Formulas in Complex Systems via Neural-Guided Lambda Calculus",
    "Agentic Symbolic Search: Characterizing PDEs Beyond Hand-crafted Expressions, Meshes, and Neural Networks",
    "Curvature-Informed Potential Energy Surface for Protein-Ligand Binding Affinity Prediction",
    "Curvature-Guided Geometric Representation for Protein-Ligand Binding Affinity Prediction",
    "Topo-Omni: Discovering Functionally Selective Brain Regions with a Deep Topographic Multimodal Model"
]

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Updated: {len(data)} domains, total: {sum(len(v) for v in data.values())} papers")
for k, v in data.items():
    print(f"  {k}: {len(v)} papers")