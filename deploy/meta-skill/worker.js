/**
 * Cloudflare Worker — meta-skill.org/studio/ API 代理
 *
 * 作用：
 * 1. 代理 /api/* 到 121.41.215.36 (hui-skill.cn 后端)
 * 2. 注入 X-Domain-Role: demo（只读权限）
 * 3. 透传其余请求到 Cloudflare Pages 静态站点
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    // API 代理：转发到后端服务器
    if (pathname.startsWith('/api/')) {
      const backendUrl = new URL(pathname + url.search, env.BACKEND_URL);

      const proxyRequest = new Request(backendUrl, {
        method: request.method,
        headers: new Headers(request.headers),
        body: request.body,
        redirect: 'follow',
      });

      // 注入只读角色标记
      proxyRequest.headers.set('X-Domain-Role', 'demo');
      proxyRequest.headers.set('X-Forwarded-For', request.headers.get('CF-Connecting-IP') || '');
      proxyRequest.headers.set('X-Forwarded-Proto', 'https');

      try {
        return await fetch(proxyRequest);
      } catch (e) {
        return new Response(JSON.stringify({ error: '服务暂时不可用，请稍后重试' }), {
          status: 502,
          headers: { 'Content-Type': 'application/json' },
        });
      }
    }

    // 静态站点：由 Cloudflare Pages 处理
    return env.ASSETS.fetch(request);
  },
};