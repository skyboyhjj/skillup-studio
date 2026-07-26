/**
 * Cloudflare Worker — meta-skill.org API 代理
 *
 * 通过 hui-skill.cn（443 端口，Cloudflare 代理）转发到后端。
 * 需要服务器 nginx 配置反向代理：/api/studio/ → localhost:8000
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    // API 代理
    if (pathname.startsWith('/api/')) {
      const backendUrl = new URL(pathname + url.search, env.BACKEND_URL);

      const proxyRequest = new Request(backendUrl, {
        method: request.method,
        headers: new Headers(request.headers),
        body: request.body,
        redirect: 'follow',
      });

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

    return env.ASSETS.fetch(request);
  },
};