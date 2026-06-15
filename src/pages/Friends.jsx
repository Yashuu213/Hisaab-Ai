import React from 'react';
import BroConnect from '../components/BroConnect';

const Friends = () => {
    return (
        <div className="max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="mb-8">
                <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">Friends Network</h1>
                <p className="text-sm text-slate-500 font-medium mt-1">Connect with other users, send nudges, and chat securely.</p>
            </div>
            
            <BroConnect />
        </div>
    );
};

export default Friends;
