export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // ⚠️ 修改这里：填入你 Space 的真实直连地址 (不要带 https://)
    const targetHost = "你的用户名-项目名.hf.space"; 
    
    url.hostname = targetHost;
    url.protocol = "https:";

    // 构造请求
    const newRequest = new Request(url.toString(), {
      method: request.method,
      headers: request.headers,
      body: request.body,
      redirect: "manual" 
    });

    return fetch(newRequest);
  },
};
