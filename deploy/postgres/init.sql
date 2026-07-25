-- Meta-Skill.org 数据库初始化
-- 由 docker-entrypoint-initdb.d 自动执行

-- 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 索引
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

CREATE INDEX IF NOT EXISTS idx_rule_libraries_owner ON rule_libraries(owner_type, owner_id);
CREATE INDEX IF NOT EXISTS idx_rule_libraries_domain ON rule_libraries(domain);
CREATE INDEX IF NOT EXISTS idx_rule_libraries_updated ON rule_libraries(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_studio_members_user ON studio_members(user_id);
CREATE INDEX IF NOT EXISTS idx_studio_members_studio ON studio_members(studio_id);

CREATE INDEX IF NOT EXISTS idx_community_shares_status ON community_shares(status);
CREATE INDEX IF NOT EXISTS idx_community_shares_author ON community_shares(author_id);
CREATE INDEX IF NOT EXISTS idx_community_shares_created ON community_shares(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_dsl_audit_logs_user ON dsl_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_dsl_audit_logs_library ON dsl_audit_logs(library_id);
CREATE INDEX IF NOT EXISTS idx_dsl_audit_logs_created ON dsl_audit_logs(created_at DESC);