// Cloudflare Pages Function - API 代理
// 将 /api/* 请求转发到后端服务器 http://121.41.215.36:8000

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);

  // 构建后端目标 URL
  const targetUrl = 'http://121.41.215.36:8000' + url.pathname + url.search;

  // 复制原始请求，替换目标 URL
  const modifiedRequest = new Request(targetUrl, {
    method: request.method,
    headers: request.headers,
    body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : undefined,
  });

  try {
    const response = await fetch(modifiedRequest);
    return response;
  } catch (err) {
    return new Response(JSON.stringify({ detail: '后端服务暂时不可用，请稍后重试' }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}