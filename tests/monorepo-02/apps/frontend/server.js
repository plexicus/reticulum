const express = require('express');
const axios = require('axios');
const _ = require('lodash');

const app = express();
app.use(express.json());

// Vulnerable to prototype pollution via lodash
app.post('/api/merge', (req, res) => {
    const defaults = { role: 'user' };
    const merged = _.merge({}, defaults, req.body);
    res.json(merged);
});

// Call internal auth service
app.post('/api/login', async (req, res) => {
    try {
        const response = await axios.post('http://auth-service:8000/authenticate', req.body);
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: 'Authentication failed' });
    }
});

app.listen(3000, () => {
    console.log('Frontend running on port 3000');
});
