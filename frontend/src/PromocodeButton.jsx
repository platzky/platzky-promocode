import React, { useState } from 'react';

export default function PromocodeButton({ code, text, color }) {
    const [revealed, setRevealed] = useState(false);

    return (
        <button
            type="button"
            onClick={() => !revealed && setRevealed(true)}
            style={{
                backgroundColor: revealed ? '#333' : color,
                border: 'none',
                borderRadius: '4px',
                color: '#fff',
                cursor: revealed ? 'default' : 'pointer',
                fontFamily: revealed ? 'monospace' : 'inherit',
                fontSize: '1rem',
                letterSpacing: revealed ? '0.1em' : 'normal',
                padding: '0.5rem 1.25rem',
                transition: 'opacity 0.2s',
            }}
        >
            {revealed ? atob(code) : text}
        </button>
    );
}
