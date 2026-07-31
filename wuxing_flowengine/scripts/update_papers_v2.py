import json

path = r"C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\wuxing_flowengine\output\phase3_paper_titles.json"

with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

data["推荐系统与信息检索"] = [
    "Gryphon: A Unified Architecture for Semantic-ID Generation and Item-Level Scoring in Industrial Recommendations",
    "Implicit Reasoning for Large Language Model-based Generative Recommendation",
    "OneRetrieval: Unifying Multi-Branch E-commerce Retrieval with an Editable Generative Model",
    "Multi-Vector Embeddings are Provably More Expressive than Single Vector Embeddings",
    "What Limits Does Quantization Place on Dense Top-k Retrieval? A Theoretical Study",
    "Compact Geometric Representations of Hierarchies",
    "ColBERTSaR: Sparsified ColBERT Index via Product Quantization",
    "GPUSparse: GPU-Accelerated Learned Sparse Retrieval with Parallel Inverted Indices",
    "TileMaxSim: IO-Aware GPU MaxSim Scoring with Dimension Tiling and Fused Product Quantization",
    "ADORE: Iterative Query Expansion with Retrieval-Grounded Relevance Feedback",
    "STORM: Stepwise Token Optimization with Reward-Guided Beam Search",
    "KaLM-Reranker-V1: Fast but Not Late Interaction for Compressed Document Reranking",
    "Stellar: Scalable Multimodal Document Retrieval for Natural Language Queries",
    "MM-Matryoshka: Towards Budget-Elastic Visual Document Retrieval via a 2D Multimodal Matryoshka Training Framework",
    "LightSTAR: Efficient Visual Document Retrieval via Lightweight Selection with Vision-Adaptive Refinement",
    "OneRank: Unified Transformer-Native Ranking Architecture for Multi-Task Recommendation",
    "UniFormer: Efficient and Unified Model-Centric Scaling for Industrial Recommendation",
    "Token Factory: Efficiently Integrating Diverse Signals into Large Recommendation Models",
    "Denoising Implicit Feedback for Cold-start Recommendation",
    "DREAM: Dynamic Refinement of Early Assignment Mappings",
    "Bridging the Semantic-Collaborative Gap: An Asymmetric Graph Architecture for Cold-Start Item Recommendation",
    "ANN Search: Recall What Matters",
    "HAKARI-Bench: A Lightweight Benchmark for Comparing Retrieval Architectures and Efficiency Settings under Unified Conditions",
    "Understanding and Debugging Failures in N-Gram-Based Generative Retrieval",
    "Temporal Preference Optimization for Unsupervised Retrieval",
    "CausalPOI: Spatio-Temporal Graph-Based Causal Modeling for Cold-Start POI Check-in Forecasting",
    "Time-Aware Diffusion based on Preference Disentanglement for Generative Recommendation",
    "RL-Index: Reinforcement Learning for Retrieval Index Reasoning",
    "AgentX: Towards Agent-Driven Self-Iteration of Industrial Recommender Systems",
    "Towards Retrieving Interaction Spaces for Agentic Search"
]

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Updated: {len(data)} domains, total: {sum(len(v) for v in data.values())} papers")