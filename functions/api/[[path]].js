// Cloudflare Pages Function - API 代理
// 将 /api/* 请求转发到后端服务器 http://121.41.215.36:8000

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);

  // 构建后端目标 URL
  const targetUrl = 'http://121.41.215.36:8000' + url.pathname + url.search;

  // 构建转发请求的 headers
  const headers = new Headers(request.headers);
  headers.set('Host', '121.41.215.36:8000');

  const init = {
    method: request.method,
    headers: headers,
  };

  // POST/PUT/PATCH 需要携带 body
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    init.body = await request.arrayBuffer();
  }

  try {
    const response = await fetch(targetUrl, init);
    return response;
  } catch (err) {
    return new Response(JSON.stringify({ detail: '后端服务暂时不可用，请稍后重试' }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}