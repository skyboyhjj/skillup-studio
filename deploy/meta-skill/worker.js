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

    // 根路径重定向到 /studio/
    if (pathname === '/') {
      return Response.redirect('https://meta-skill.org/studio/', 302);
    }

    // 去掉 /studio 前缀再转发到 Pages 资产
    // Pages 项目根目录 = frontend/studio，所以 /studio/xxx → /xxx
    let assetPath = pathname;
    if (assetPath.startsWith('/studio')) {
      assetPath = assetPath.replace(/^\/studio\/?/, '/');
    }

    // 优先使用 env.ASSETS（Pages Functions 部署），否则从 Pages 部署 URL 获取
    if (env.ASSETS) {
      const assetUrl = new URL(assetPath + url.search, url.origin);
      return env.ASSETS.fetch(new Request(assetUrl, request));
    }

    const pagesUrl = env.PAGES_URL || 'https://meta-skill-studio.pages.dev';
    const assetUrl = new URL(assetPath + url.search, pagesUrl);
    const assetResp = await fetch(new Request(assetUrl, request));
    // 添加调试头确认 Worker 被调用
    const newHeaders = new Headers(assetResp.headers);
    newHeaders.set('X-Debug-Worker', 'v2-fixed');
    newHeaders.set('X-Asset-Path', assetPath);
    return new Response(assetResp.body, {
      status: assetResp.status,
      headers: newHeaders,
    });
  },
};