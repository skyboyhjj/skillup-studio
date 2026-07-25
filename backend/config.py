"""Meta-Skill.org 后端配置"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 安全
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# 数据库
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://ms_user:dev_password@localhost:5432/meta_skill"
)
DATABASE_URL_SYNC = DATABASE_URL.replace("+asyncpg", "+psycopg2")

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# CORS
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "https://hui-skill.cn,https://meta-skill.org,http://localhost:8088"
).split(",")

# AI (DeepSeek)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# 规则库路径
RULES_BASE_PATH = Path(os.getenv("RULES_BASE_PATH", BASE_DIR.parent / "wuxing_rules" / "rules"))

# 日志
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# 用户角色
class Role:
    GUEST = "guest"
    REGISTERED = "registered"
    STUDIO_MEMBER = "studio_member"
    STUDIO_ADMIN = "studio_admin"
    STUDIO_OWNER = "studio_owner"
    ADMIN = "admin"

# 认知深度
class CognitiveDepth:
    L1 = "L1"  # 白话
    L2 = "L2"  # 精读
    L3 = "L3"  # 应用
    L4 = "L4"  # 学术

VALID_DEPTHS = [CognitiveDepth.L1, CognitiveDepth.L2, CognitiveDepth.L3, CognitiveDepth.L4]

# 领域列表
VALID_DOMAINS = [
    "chinese_medicine",
    "daojism",
    "confucianism",
    "buddhism",
    "science_technology",
    "western_philosophy",
    "mathematics",
]