// Cloudflare Pages Function - API 代理
// 将 /api/* 请求转发到后端服务器 http://121.41.215.36:8000

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);

  // 构建后端目标 URL
  const targetUrl = 'http://121.41.215.36:8000' + url.pathname + url.search;

  // 克隆请求并修改 Host header
  // 使用 new Request(url, originalRequest) 确保 body 和 headers 正确传递
  const proxyRequest = new Request(targetUrl, new Request(request));
  proxyRequest.headers.set('Host', 'meta-skill.org');

  try {
    const response = await fetch(proxyRequest);
    return response;
  } catch (err) {
    return new Response(JSON.stringify({ detail: '后端服务暂时不可用，请稍后重试' }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}