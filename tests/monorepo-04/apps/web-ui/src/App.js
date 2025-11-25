import React, { useState } from 'react';
import DOMPurify from 'dompurify';

function App() {
    const [userInput, setUserInput] = useState('');

    // MEDIUM SEVERITY: Potential XSS if DOMPurify is bypassed
    const renderHTML = () => {
        // Using older version of DOMPurify with known bypasses
        const sanitized = DOMPurify.sanitize(userInput);
        return { __html: sanitized };
    };

    return (
        <div className="App">
            <h1>User Dashboard</h1>
            <input
                type="text"
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                placeholder="Enter content"
            />
            <div dangerouslySetInnerHTML={renderHTML()} />
        </div>
    );
}

export default App;
