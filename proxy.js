const http = require('http');
const httpProxy = require('http-proxy');

const proxy = httpProxy.createProxyServer({});

const server = http.createServer((req, res) => {
  if (req.url.startsWith('/api') || req.url.startsWith('/docs') || req.url.startsWith('/openapi.json')) {
    // Route to Backend
    proxy.web(req, res, { target: 'http://localhost:8000' });
  } else {
    // Route to Frontend
    proxy.web(req, res, { target: 'http://localhost:5173' });
  }
});

proxy.on('error', (err, req, res) => {
  res.writeHead(500, { 'Content-Type': 'text/plain' });
  res.end('Proxy Error: ' + err.message);
});

console.log('Proxy listening on port 9000');
server.listen(9000);
