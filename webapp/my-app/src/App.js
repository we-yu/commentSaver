// Reactコンポーネントの例
import React, { useState } from 'react';

function ArticleForm() {
  const [title, setTitle] = useState('');
  const [response, setResponse] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    try {
      // const res = await fetch(`http://api:8000/forward-to-scraper/${title}`);
      const res = await fetch(`http://54.255.145.116:5110/forward-to-scraper/${title}`);
      const data = await res.json();
      setResponse({ status: res.status, body: data });
    } catch (error) {
      setResponse({ status: 'error', body: error.message });
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <button type="submit">Submit</button>
      </form>
      {response && (
        <div>
          <p>Status: {response.status}</p>
          <p>Response: {JSON.stringify(response.body)}</p>
        </div>
      )}
    </div>
  );
}

export default ArticleForm;
