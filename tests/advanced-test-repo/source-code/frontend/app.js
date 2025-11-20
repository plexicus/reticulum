const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Security issue: Hardcoded secret
const API_KEY = 'super-secret-key-12345';
const JWT_SECRET = 'frontend-jwt-secret';

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// Vulnerable endpoint: No input validation
app.get('/api/user/:id', (req, res) => {
  const userId = req.params.id;
  // Potential SQL injection if this was a database query
  res.json({ id: userId, name: 'Test User' });
});

// Security issue: XSS vulnerability
app.get('/api/display', (req, res) => {
  const userInput = req.query.input || 'safe';
  // Security issue: No input sanitization
  res.send(`<div>${userInput}</div>`);
});

// Another security issue: Exposed debug endpoint
app.get('/debug/info', (req, res) => {
  res.json({
    nodeVersion: process.version,
    environment: process.env.NODE_ENV || 'development',
    apiKey: API_KEY, // Exposing secret!
    jwtSecret: JWT_SECRET // Exposing secret!
  });
});

// Security issue: Command injection vulnerability
app.get('/api/execute', (req, res) => {
  const { exec } = require('child_process');
  const command = req.query.cmd || 'ls';

  exec(command, (error, stdout, stderr) => {
    if (error) {
      res.json({ error: error.message });
      return;
    }
    res.json({ result: stdout });
  });
});

app.listen(PORT, () => {
  console.log(`Frontend server running on port ${PORT}`);
});