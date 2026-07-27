/**
 * Cloudflare Pages _worker.js — meta-skill.org 路由总管
 *
 * 作为 Pages Function 部署，env.ASSETS 自动可用。
 * 包含：API 代理 + 静态资源服务 + /studio/ 前缀处理
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    // === API 代理 ===
    if (pathname.startsWith('/api/')) {
      // CORS 预检
      if (request.method === 'OPTIONS') {
        return new Response(null, {
          status: 204,
          headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '86400',
          },
        });
      }

      const backendUrl = env.BACKEND_URL || 'https://hui-skill.cn';
      const targetUrl = backendUrl + pathname + url.search;

      try {
        const response = await fetch(targetUrl, {
          method: request.method,
          headers: {
            'Content-Type': 'application/json',
            'X-Domain-Role': 'demo',
          },
          body: request.body,
          redirect: 'follow',
        });

        const responseBody = await response.text();

        return new Response(responseBody, {
          status: response.status,
          statusText: response.statusText,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
          },
        });
      } catch (err) {
        return new Response(JSON.stringify({
          detail: '后端服务暂时不可用',
          error: err.message,
        }), {
          status: 502,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        });
      }
    }

    // === 根路径重定向到 /studio/ ===
    if (pathname === '/') {
      return Response.redirect('/studio/', 302);
    }

    // === 静态资源：去掉 /studio 前缀后从 ASSETS 获取 ===
    let assetPath = pathname;
    if (assetPath.startsWith('/studio')) {
      assetPath = assetPath.replace(/^\/studio\/?/, '/');
    }

    return env.ASSETS.fetch(new Request(new URL(assetPath + url.search, url.origin), request));
  },
};