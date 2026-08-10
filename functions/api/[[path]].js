// Cloudflare Pages Function - API 代理
// 将 /api/* 请求转发到后端服务器
// 部署前需在 Cloudflare Dashboard > Settings > Environment Variables 中设置:
//   API_TARGET = http://<your-server-ip>:8000

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);

  // 从环境变量读取后端地址，未配置时使用占位符（会返回 502）
  const apiBase = env.API_TARGET || 'http://DEPLOY_SERVER:8000';

  // 构建后端目标 URL
  const targetUrl = apiBase + url.pathname + url.search;

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