const { createServer } = require('http');
const { parse } = require('url');
const next = require('next');
const fs = require('fs');
const path = require('path');

const dev = process.env.NODE_ENV !== 'production';
const hostname = 'localhost';
const port = parseInt(process.env.PORT || '3000', 10);

// ── Read basePath ──────────────────────────────────────────────────────────────
let envBasePath = process.env.NEXT_PUBLIC_BASE_PATH || '';
try {
  const envFile = fs.readFileSync(path.join(__dirname, '.env.local'), 'utf8');
  const match = envFile.match(/^NEXT_PUBLIC_BASE_PATH=(.*)$/m);
  if (match) envBasePath = match[1].trim();
} catch (e) {
  // .env.local might not exist, that's fine
}
const basePath = envBasePath;

// ── Helper: prepend basePath if proxy stripped it ─────────────────────────────
function fixUrl(url) {
  if (basePath && !url.startsWith(basePath)) {
    return `${basePath}${url}`;
  }
  return url;
}

const app = next({ dev, hostname, port });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  const server = createServer(async (req, res) => {
    try {
      req.url = fixUrl(req.url);
      const parsedUrl = parse(req.url, true);
      await handle(req, res, parsedUrl);
    } catch (err) {
      console.error('Error occurred handling', req.url, err);
      res.statusCode = 500;
      res.end('internal server error');
    }
  });

  // ── Fix WebSocket upgrade for HMR ──────────────────────────────────────────
  // The Jupyter proxy strips the basePath before forwarding WebSocket upgrades,
  // so /_next/webpack-hmr arrives without the prefix. We rewrite it here.
  server.on('upgrade', (req, socket, head) => {
    req.url = fixUrl(req.url);
    // Let Next.js handle the upgraded WebSocket connection
    app.getUpgradeHandler()(req, socket, head);
  });

  server
    .once('error', (err) => {
      console.error(err);
      process.exit(1);
    })
    .listen(port, () => {
      console.log(`> Ready on http://${hostname}:${port}`);
      if (basePath) {
        console.log(`> Using basePath: ${basePath}`);
        console.log(`> Handling stripped proxy requests automatically.`);
        console.log(`> WebSocket HMR upgrade handler active.`);
      }
    });
});